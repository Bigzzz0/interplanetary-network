"""
Edge Server (Lagrange Edge Predictor) - Main Application
=========================================================
Receives keyframes, runs predictive algorithms (optical flow interpolation),
generates synthesized frames with confidence, and signs attestations.
"""

import asyncio
import json
import time
import base64
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import cv2
import numpy as np
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import Base64Encoder
from nacl.exceptions import BadSignatureError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import websockets

app = FastAPI(
    title="Edge Server (Lagrange Edge)",
    description="Predictor that generates synthesized frames with attestation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Edge signing key
EDGE_SIGNING_KEY: Optional[SigningKey] = None

# Frame buffer for prediction
frame_buffer: List[Dict[str, Any]] = []
MAX_BUFFER_SIZE = 10


@dataclass
class PredictorConfig:
    """Configuration for the frame predictor."""
    interpolation_frames: int = 2  # Number of frames to interpolate
    optical_flow_method: str = "farneback"  # 'farneback' or 'lucas_kanade'
    confidence_threshold: float = 0.7


config = PredictorConfig()


def init_edge_signing_key() -> SigningKey:
    """Initialize or load the edge server's Ed25519 signing key."""
    global EDGE_SIGNING_KEY
    try:
        with open("edge_private_key.bin", "rb") as f:
            EDGE_SIGNING_KEY = SigningKey(f.read())
    except FileNotFoundError:
        EDGE_SIGNING_KEY = SigningKey.generate()
        with open("edge_private_key.bin", "wb") as f:
            f.write(bytes(EDGE_SIGNING_KEY))
        with open("edge_public_key.bin", "wb") as f:
            f.write(bytes(EDGE_SIGNING_KEY.verify_key))
    return EDGE_SIGNING_KEY


def sign_synthesized_frame(
    frame_data: bytes,
    frame_id: int,
    parent_frame_ids: List[int],
    confidence: float
) -> dict:
    """Sign synthesized frame and create attestation metadata."""
    if EDGE_SIGNING_KEY is None:
        init_edge_signing_key()
    
    timestamp = time.time()
    message = f"synth:{frame_id}:{timestamp}:{confidence:.4f}:{parent_frame_ids}".encode()
    signed = EDGE_SIGNING_KEY.sign(message, encoder=Base64Encoder)
    
    return {
        "frame_id": frame_id,
        "timestamp": timestamp,
        "is_synthesized": True,
        "parent_frame_ids": parent_frame_ids,
        "confidence": confidence,
        "predictor_version": "optical_flow_v1",
        "edge_signature": signed.signature.decode(),
        "edge_public_key": base64.b64encode(bytes(EDGE_SIGNING_KEY.verify_key)).decode()
    }


def verify_origin_signature(metadata: dict, frame_size: int) -> bool:
    """Verify the origin sender's signature."""
    try:
        public_key_bytes = base64.b64decode(metadata["public_key"])
        verify_key = VerifyKey(public_key_bytes)
        
        message = f"{metadata['frame_id']}:{metadata['timestamp']}:{frame_size}".encode()
        signature = base64.b64decode(metadata["signature"])
        
        verify_key.verify(message, signature)
        return True
    except (BadSignatureError, KeyError, Exception) as e:
        print(f"Signature verification failed: {e}")
        return False


def decode_frame_from_base64(data: str) -> np.ndarray:
    """Decode frame from base64 JPEG data."""
    frame_bytes = base64.b64decode(data)
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return frame


def encode_frame_to_base64(frame: np.ndarray, quality: int = 80) -> str:
    """Encode frame to base64 JPEG."""
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode('.jpg', frame, encode_params)
    return base64.b64encode(buffer.tobytes()).decode()


def calculate_psnr(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calculate Peak Signal-to-Noise Ratio between two images."""
    # Ensure same size
    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
    
    mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)
    if mse == 0:
        return 100.0  # Perfect match
    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return min(50.0, max(0.0, psnr))


def calculate_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calculate Structural Similarity Index between two images."""
    # Ensure same size
    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
    
    # Convert to grayscale for SSIM
    if len(img1.shape) == 3:
        img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        img2_gray = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    else:
        img1_gray = img1
        img2_gray = img2
    
    # Constants for SSIM
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2
    
    img1_float = img1_gray.astype(np.float64)
    img2_float = img2_gray.astype(np.float64)
    
    # Mean
    mu1 = cv2.GaussianBlur(img1_float, (11, 11), 1.5)
    mu2 = cv2.GaussianBlur(img2_float, (11, 11), 1.5)
    
    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2
    
    # Variance and covariance
    sigma1_sq = cv2.GaussianBlur(img1_float ** 2, (11, 11), 1.5) - mu1_sq
    sigma2_sq = cv2.GaussianBlur(img2_float ** 2, (11, 11), 1.5) - mu2_sq
    sigma12 = cv2.GaussianBlur(img1_float * img2_float, (11, 11), 1.5) - mu1_mu2
    
    # SSIM formula
    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    return float(np.mean(ssim_map))


def calculate_quality_metrics(synthesized: np.ndarray, reference: np.ndarray) -> dict:
    """Calculate PSNR, SSIM and frame match score between synthesized and reference frames."""
    psnr = calculate_psnr(synthesized, reference)
    ssim = calculate_ssim(synthesized, reference)
    
    # Frame match score based on histogram correlation
    hist1 = cv2.calcHist([synthesized], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    hist2 = cv2.calcHist([reference], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    frame_match = cv2.compareHist(cv2.normalize(hist1, hist1), cv2.normalize(hist2, hist2), cv2.HISTCMP_CORREL)
    frame_match = max(0.0, min(1.0, frame_match)) * 100  # Convert to percentage
    
    return {
        "psnr": round(psnr, 2),
        "ssim": round(ssim, 4),
        "frame_match": round(frame_match, 1)
    }


def interpolate_frames(
    frame1: np.ndarray,
    frame2: np.ndarray,
    num_interpolated: int = 2
) -> List[tuple]:
    """
    Interpolate frames using optical flow.
    Returns list of (interpolated_frame, confidence) tuples.
    """
    # Convert to grayscale for optical flow
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # Calculate optical flow using Farneback method
    flow = cv2.calcOpticalFlowFarneback(
        gray1, gray2,
        None,
        pyr_scale=0.5,
        levels=3,
        winsize=15,
        iterations=3,
        poly_n=5,
        poly_sigma=1.2,
        flags=0
    )
    
    interpolated = []
    
    for i in range(1, num_interpolated + 1):
        alpha = i / (num_interpolated + 1)
        
        # Create interpolated flow
        h, w = gray1.shape
        flow_map = np.zeros((h, w, 2), dtype=np.float32)
        flow_map[:, :, 0] = np.arange(w)
        flow_map[:, :, 1] = np.arange(h)[:, np.newaxis]
        
        # Apply partial flow
        flow_map[:, :, 0] += flow[:, :, 0] * alpha
        flow_map[:, :, 1] += flow[:, :, 1] * alpha
        
        # Remap frame
        interpolated_frame = cv2.remap(
            frame1,
            flow_map,
            None,
            cv2.INTER_LINEAR
        )
        
        # Blend with simple linear interpolation
        blended = cv2.addWeighted(
            interpolated_frame, 1 - alpha * 0.3,
            frame2, alpha * 0.3,
            0
        )
        
        # Calculate confidence based on flow magnitude
        flow_magnitude = np.sqrt(flow[:, :, 0]**2 + flow[:, :, 1]**2)
        avg_magnitude = np.mean(flow_magnitude)
        
        # Lower confidence for high motion
        confidence = max(0.5, min(0.95, 1.0 - avg_magnitude / 50))
        
        interpolated.append((blended, confidence))
    
    return interpolated


@app.on_event("startup")
async def startup():
    """Initialize edge signing key on startup."""
    init_edge_signing_key()
    print("Edge server initialized with signing key")
    print(f"Edge public key: {base64.b64encode(bytes(EDGE_SIGNING_KEY.verify_key)).decode()}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "component": "edge_server",
        "status": "running",
        "buffer_size": len(frame_buffer),
        "edge_public_key": base64.b64encode(bytes(EDGE_SIGNING_KEY.verify_key)).decode() if EDGE_SIGNING_KEY else None
    }


@app.get("/public-key")
async def get_public_key():
    """Get the edge server's public key for verification."""
    if EDGE_SIGNING_KEY is None:
        init_edge_signing_key()
    return {
        "edge_public_key": base64.b64encode(bytes(EDGE_SIGNING_KEY.verify_key)).decode()
    }


@app.websocket("/process")
async def process_stream(websocket: WebSocket):
    """
    WebSocket endpoint that receives frames from network simulator,
    runs prediction, and forwards enhanced stream to client.
    """
    await websocket.accept()
    print("Edge processing connection established")
    
    # Connect to network simulator
    network_uri = "ws://localhost:8002/proxy"
    synthesized_frame_counter = 0
    
    try:
        async with websockets.connect(network_uri) as network_ws:
            print("Connected to network simulator")
            
            async for message in network_ws:
                try:
                    data = json.loads(message)
                    
                    if data.get("type") == "error":
                        await websocket.send_json(data)
                        continue
                    
                    if data.get("type") != "frame":
                        continue
                    
                    metadata = data.get("metadata", {})
                    frame_data = data.get("data", "")
                    
                    # Verify origin signature
                    origin_verified = verify_origin_signature(
                        metadata,
                        metadata.get("frame_size", 0)
                    )
                    
                    # Decode frame
                    frame = decode_frame_from_base64(frame_data)
                    
                    # Add to buffer
                    frame_buffer.append({
                        "frame": frame,
                        "metadata": metadata,
                        "origin_verified": origin_verified
                    })
                    
                    # Keep buffer size limited
                    while len(frame_buffer) > MAX_BUFFER_SIZE:
                        frame_buffer.pop(0)
                    
                    # Forward original frame with verification status
                    original_output = {
                        "type": "frame",
                        "metadata": {
                            **metadata,
                            "origin_verified": origin_verified,
                            "is_synthesized": False
                        },
                        "data": frame_data,
                        "network_metadata": data.get("network_metadata", {})
                    }
                    await websocket.send_json(original_output)
                    
                    # Generate interpolated frames if we have enough buffer
                    if len(frame_buffer) >= 2:
                        prev_frame = frame_buffer[-2]["frame"]
                        curr_frame = frame_buffer[-1]["frame"]
                        prev_id = frame_buffer[-2]["metadata"]["frame_id"]
                        curr_id = frame_buffer[-1]["metadata"]["frame_id"]
                        
                        # Interpolate frames
                        interpolated = interpolate_frames(
                            prev_frame,
                            curr_frame,
                            config.interpolation_frames
                        )
                        
                        # Send interpolated frames
                        for interp_frame, confidence in interpolated:
                            synthesized_frame_counter += 1
                            synth_id = f"synth_{synthesized_frame_counter}"
                            
                            # Calculate real quality metrics comparing synthesized to reference
                            quality_metrics = calculate_quality_metrics(interp_frame, curr_frame)
                            
                            # Sign synthesized frame
                            frame_bytes = base64.b64decode(encode_frame_to_base64(interp_frame))
                            synth_metadata = sign_synthesized_frame(
                                frame_bytes,
                                synth_id,
                                [prev_id, curr_id],
                                confidence
                            )
                            
                            synth_output = {
                                "type": "frame",
                                "metadata": {
                                    **synth_metadata,
                                    "origin_verified": origin_verified,
                                    # Add real quality metrics
                                    "psnr": quality_metrics["psnr"],
                                    "ssim": quality_metrics["ssim"],
                                    "frame_match": quality_metrics["frame_match"]
                                },
                                "data": encode_frame_to_base64(interp_frame)
                            }
                            await websocket.send_json(synth_output)
                    
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                except Exception as e:
                    print(f"Processing error: {e}")
                    
    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket error: {e}")
    except ConnectionRefusedError:
        print("Could not connect to network simulator - is it running?")
        await websocket.send_json({
            "type": "error",
            "message": "Could not connect to network simulator"
        })
    except WebSocketDisconnect:
        print("Edge processing client disconnected")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
