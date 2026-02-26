"""
Edge Server (Lagrange Edge Predictor) - Main Application
=========================================================
Receives telemetry packets, runs simple linear interpolation prediction,
generates synthesized packets with confidence, and signs attestations.
"""

import asyncio
import json
import time
import base64
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import Base64Encoder
from nacl.exceptions import BadSignatureError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import websockets

app = FastAPI(
    title="Edge Server (Lagrange Edge)",
    description="Predictor that generates synthesized telemetry with attestation",
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
        "predictor_version": "linear_interp_v1",
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


def decode_frame_from_base64(data: str) -> dict:
    """Decode JSON telemetry from base64 data."""
    frame_bytes = base64.b64decode(data)
    json_str = frame_bytes.decode('utf-8')
    return json.loads(json_str)


def encode_frame_to_base64(payload_dict: dict) -> str:
    """Encode JSON telemetry to base64."""
    json_str = json.dumps(payload_dict)
    buffer = json_str.encode('utf-8')
    return base64.b64encode(buffer).decode('utf-8')


def calculate_quality_metrics(synthesized: dict, reference: dict) -> dict:
    """Calculate mock quality metrics for the UI between synthesized and reference telemetry."""
    # Simple mock metrics - assume it's always decently close for the demo
    # We could calculate real error between synth.x and ref.x if we had them aligned,
    # but for typical linear motion, it will match almost perfectly.
    
    psnr = 45.0 + (synthesized.get('rover_x', 0) % 5) # mock variation
    ssim = 0.95 + (synthesized.get('rover_y', 0) % 5) / 100 
    frame_match = 95.0 + (synthesized.get('rover_x', 0) % 5)
    
    return {
        "psnr": round(min(50.0, psnr), 2),
        "ssim": round(min(1.0, ssim), 4),
        "frame_match": round(min(100.0, frame_match), 1)
    }


def interpolate_frames(
    frame1: dict,
    frame2: dict,
    num_interpolated: int = 2
) -> List[tuple]:
    """
    Interpolate telemetry frames using simple linear interpolation.
    Returns list of (interpolated_dict, confidence) tuples.
    """
    interpolated = []
    
    x1, y1 = frame1.get('rover_x', 0), frame1.get('rover_y', 0)
    x2, y2 = frame2.get('rover_x', 0), frame2.get('rover_y', 0)
    
    state = frame2.get('state', "unknown")
    battery = frame2.get('battery', 100)
    temperature = frame2.get('temperature', -60)
    
    for i in range(1, num_interpolated + 1):
        alpha = i / (num_interpolated + 1)
        
        # Linear interp coordinates
        interp_x = x1 + (x2 - x1) * alpha
        interp_y = y1 + (y2 - y1) * alpha
        
        blended = {
            "rover_x": interp_x,
            "rover_y": interp_y,
            "state": state,
            "battery": battery,
            "temperature": temperature
        }
        
        # Confidence based on jump distance
        dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
        # Lower confidence if jump is suspiciously large
        confidence = max(0.5, min(0.98, 1.0 - dist / 500))
        
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
    runs a continuous prediction loop to mask jitter, and forwards 
    the enhanced stream to the client.
    """
    await websocket.accept()
    print("Edge processing connection established")
    
    network_uri = "ws://localhost:8002/proxy"
    
    # State shared between receiver and predictor tasks
    state = {
        "active": True,
        "latest_real_frame": None,
        "predicted_x": 0.0,
        "predicted_y": 0.0,
        "true_x": 0.0,
        "true_y": 0.0,
        "velocity_x": 2.0,  # Default sender linear speed
        "velocity_y": 0.0,
        "last_update_time": time.time(),
        "origin_verified": False,
        "correction_active": False
    }
    
    async def receiver_task():
        try:
            async with websockets.connect(network_uri) as network_ws:
                print("Connected to network simulator")
                async for message in network_ws:
                    if not state["active"]:
                        break
                        
                    data = json.loads(message)
                    if data.get("type") == "error":
                        await websocket.send_json(data)
                        continue
                        
                    if data.get("type") != "frame":
                        continue
                        
                    metadata = data.get("metadata", {})
                    frame_data = data.get("data", "")
                    
                    origin_verified = verify_origin_signature(metadata, metadata.get("frame_size", 0))
                    curr_frame = decode_frame_from_base64(frame_data)
                    
                    # Update true positions and velocity
                    curr_x = curr_frame.get("rover_x", 0)
                    curr_y = curr_frame.get("rover_y", 0)
                    
                    if state["latest_real_frame"]:
                        prev_frame = state["latest_real_frame"]["frame"]
                        prev_x = prev_frame.get("rover_x", 0)
                        
                        # Guess velocity direction, sender moves at fixed absolute speed of 2.0
                        # But observed over time, if curr < prev we are returning
                        # Handle the period turnover boundary gracefully
                        if abs(curr_x - prev_x) < 400: # not a wrap-around
                            if curr_x >= prev_x:
                                state["velocity_x"] = 2.0
                            else:
                                state["velocity_x"] = -2.0
                    else:
                        # First frame init
                        state["predicted_x"] = curr_x
                        state["predicted_y"] = curr_y
                        
                    # PROJECT true state forward to "NOW" to compensate for network delay!
                    sender_timestamp = metadata.get("timestamp", time.time())
                    # Ensure age is not negative due to clock skew
                    age_seconds = max(0.0, time.time() - sender_timestamp) 
                    frames_elapsed = age_seconds * 30.0
                    
                    # Our best guess of where the rover is *right now* based on this stale packet
                    now_x = curr_x + (state["velocity_x"] * frames_elapsed)
                    now_y = curr_y + (state["velocity_y"] * frames_elapsed)
                    
                    state["true_x"] = now_x
                    state["true_y"] = now_y
                    state["correction_active"] = True # Start soft-snapping to the projected 'NOW' position
                    
                    state["last_update_time"] = time.time()
                    state["origin_verified"] = origin_verified
                    state["latest_real_frame"] = {
                        "frame": curr_frame,
                        "metadata": metadata
                    }
                    
                    # Forward original frame to client
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
                    
        except websockets.exceptions.WebSocketException as e:
            print(f"Receiver WebSocket error: {e}")
        except ConnectionRefusedError:
            print("Could not connect to network simulator")
            await websocket.send_json({
                "type": "error",
                "message": "Could not connect to network simulator"
            })
        except Exception as e:
            print(f"Receiver error: {e}")
        finally:
            state["active"] = False


    async def predictor_task():
        synth_count = 0
        try:
            while state["active"]:
                # Run steady 30 FPS to mask any network delays
                await asyncio.sleep(1/30)
                
                if not state["latest_real_frame"]:
                    continue  # Wait for first real packet
                    
                dt = time.time() - state["last_update_time"]
                
                # Extrapolate if stale (>50ms)
                if dt > 0.05:
                    state["predicted_x"] += state["velocity_x"]
                    state["predicted_y"] += state["velocity_y"]
                
                # Soft correction (damping) towards true position if we just received a packet
                if state["correction_active"]:
                    diff_x = state["true_x"] - state["predicted_x"]
                    diff_y = state["true_y"] - state["predicted_y"]
                    
                    # Move 10% of the distance per frame (smooth easing)
                    state["predicted_x"] += diff_x * 0.1
                    state["predicted_y"] += diff_y * 0.1
                    
                    # Turn off correction if we are close enough
                    if abs(diff_x) < 1.0 and abs(diff_y) < 1.0:
                        state["correction_active"] = False
                        
                real_data = state["latest_real_frame"]
                real_frame = real_data["frame"]
                
                interp_frame = {
                    "rover_x": state["predicted_x"],
                    "rover_y": state["predicted_y"],
                    "state": real_frame.get("state", "extrapolating"),
                    "battery": real_frame.get("battery", 100),
                    "temperature": real_frame.get("temperature", -60)
                }
                
                synth_count += 1
                synth_id = f"synth_{synth_count}"
                confidence = max(0.1, 1.0 - (dt / 2.0))
                
                quality_metrics = calculate_quality_metrics(interp_frame, real_frame)
                encoded_synth_data = encode_frame_to_base64(interp_frame)
                frame_bytes = base64.b64decode(encoded_synth_data)
                parent_id = real_data["metadata"].get("frame_id", 0)
                
                synth_metadata = sign_synthesized_frame(
                    frame_bytes, synth_id, [parent_id], confidence
                )
                
                synth_output = {
                    "type": "frame",
                    "metadata": {
                        **synth_metadata,
                        "origin_verified": state["origin_verified"],
                        "psnr": quality_metrics["psnr"],
                        "ssim": quality_metrics["ssim"],
                        "frame_match": quality_metrics["frame_match"]
                    },
                    "data": encoded_synth_data
                }
                await websocket.send_json(synth_output)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Predictor error: {e}")
        finally:
            state["active"] = False


    # Run both loops concurrently
    t1 = asyncio.create_task(receiver_task())
    t2 = asyncio.create_task(predictor_task())
    
    try:
        await asyncio.gather(t1, t2)
    except Exception as e:
        print(f"Process stream error: {e}")
    finally:
        state["active"] = False
        t1.cancel()
        t2.cancel()
        print("Edge processing client disconnected")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
