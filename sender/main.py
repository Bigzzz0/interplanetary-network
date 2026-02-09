"""
Sender (Mars Emulator) - Main Application
==========================================
Captures video from webcam, loads from video file, or uses test pattern.
Signs frames with Ed25519 and streams via WebSocket.
"""

import asyncio
import json
import time
import base64
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="Sender (Mars Emulator)",
    description="Captures and signs video frames for transmission",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DATASET_DIR = Path(__file__).parent.parent / "dataset"
SIGNING_KEY: Optional[SigningKey] = None

# Video source settings
VIDEO_SOURCE = None  # Will be set on startup
SOURCE_TYPE = "test"  # "webcam", "video", or "test"


def find_video_file() -> Optional[Path]:
    """Find a video file in the dataset directory."""
    if not DATASET_DIR.exists():
        DATASET_DIR.mkdir(parents=True, exist_ok=True)
        return None
    
    # Supported video formats
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    
    for ext in video_extensions:
        files = list(DATASET_DIR.glob(f'*{ext}'))
        if files:
            return files[0]
    
    return None


def init_signing_key() -> SigningKey:
    """Initialize or load the Ed25519 signing key."""
    global SIGNING_KEY
    key_path = Path(__file__).parent / "sender_private_key.bin"
    pub_key_path = Path(__file__).parent / "sender_public_key.bin"
    
    try:
        with open(key_path, "rb") as f:
            SIGNING_KEY = SigningKey(f.read())
    except FileNotFoundError:
        SIGNING_KEY = SigningKey.generate()
        with open(key_path, "wb") as f:
            f.write(bytes(SIGNING_KEY))
        with open(pub_key_path, "wb") as f:
            f.write(bytes(SIGNING_KEY.verify_key))
    return SIGNING_KEY


def sign_frame_data(frame_data: bytes, frame_id: int, timestamp: float) -> dict:
    """Sign frame data and create metadata."""
    if SIGNING_KEY is None:
        init_signing_key()
    
    message = f"{frame_id}:{timestamp}:{len(frame_data)}".encode()
    signed = SIGNING_KEY.sign(message, encoder=Base64Encoder)
    
    return {
        "frame_id": frame_id,
        "timestamp": timestamp,
        "signature": signed.signature.decode(),
        "public_key": base64.b64encode(bytes(SIGNING_KEY.verify_key)).decode(),
        "is_keyframe": True
    }


def encode_frame_to_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
    """Encode frame to JPEG format."""
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    _, buffer = cv2.imencode('.jpg', frame, encode_params)
    return buffer.tobytes()


def generate_test_pattern(frame_id: int) -> np.ndarray:
    """
    Generate a professional test pattern for demo presentation.
    Shows: Mars surface simulation, rover, data transmission animation.
    """
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # === BACKGROUND: Space gradient with stars ===
    for y in range(480):
        # Dark blue to black gradient (space)
        blue_val = max(0, 40 - int(y * 0.08))
        frame[y, :] = [blue_val, 5, 10]
    
    # Add twinkling stars
    np.random.seed(42)  # Fixed seed for consistent star positions
    for _ in range(100):
        sx, sy = np.random.randint(0, 640), np.random.randint(0, 200)
        brightness = 150 + (frame_id * 7 + sx) % 105  # Twinkle effect
        frame[sy, sx] = [brightness, brightness, brightness]
    
    # === MARS SURFACE (bottom third) ===
    for y in range(320, 480):
        # Mars terrain gradient (orange-red)
        terrain_noise = int(np.sin((y + frame_id) * 0.1) * 15)
        r = min(255, 180 + terrain_noise)
        g = min(255, 80 + terrain_noise // 2)
        b = 40
        frame[y, :] = [b, g, r]
    
    # Add terrain texture (rocks/craters)
    for i in range(20):
        cx = (i * 37 + frame_id // 10) % 640
        cy = 350 + (i * 13) % 100
        radius = 5 + i % 10
        cv2.circle(frame, (cx, cy), radius, (30, 60, 140), -1)
        cv2.circle(frame, (cx, cy), radius, (25, 50, 120), 2)
    
    # === MARS ROVER (animated position) ===
    rover_x = 100 + (frame_id * 2) % 400  # Moving rover
    rover_y = 340
    
    # Rover body
    cv2.rectangle(frame, (rover_x, rover_y - 20), (rover_x + 60, rover_y), (80, 80, 80), -1)
    cv2.rectangle(frame, (rover_x + 10, rover_y - 35), (rover_x + 50, rover_y - 20), (100, 100, 100), -1)
    
    # Rover wheels
    wheel_offset = (frame_id * 10) % 360
    cv2.circle(frame, (rover_x + 10, rover_y + 5), 10, (50, 50, 50), -1)
    cv2.circle(frame, (rover_x + 50, rover_y + 5), 10, (50, 50, 50), -1)
    cv2.line(frame, (rover_x + 10, rover_y + 5), 
             (rover_x + 10 + int(8 * np.cos(np.radians(wheel_offset))),
              rover_y + 5 + int(8 * np.sin(np.radians(wheel_offset)))),
             (150, 150, 150), 2)
    
    # Antenna with blinking signal
    cv2.line(frame, (rover_x + 30, rover_y - 35), (rover_x + 30, rover_y - 55), (200, 200, 200), 2)
    if frame_id % 10 < 5:  # Blinking
        cv2.circle(frame, (rover_x + 30, rover_y - 58), 5, (0, 255, 255), -1)  # Cyan signal
    
    # === DATA TRANSMISSION ANIMATION ===
    # Animated packets traveling from rover to "satellite"
    packet_positions = [(frame_id * 8 + i * 80) % 300 for i in range(4)]
    for i, pos in enumerate(packet_positions):
        px = rover_x + 30 + int(pos * 0.5)
        py = rover_y - 55 - int(pos * 0.3)
        if py > 50:
            color = (0, 255, 255) if i % 2 == 0 else (255, 200, 0)  # Cyan or Yellow
            cv2.circle(frame, (px, py), 4, color, -1)
    
    # === EARTH (top right) ===
    earth_x, earth_y = 550, 80
    earth_radius = 35
    cv2.circle(frame, (earth_x, earth_y), earth_radius, (255, 200, 100), -1)  # Base (land)
    cv2.circle(frame, (earth_x - 10, earth_y - 5), 20, (255, 150, 50), -1)  # Ocean
    cv2.circle(frame, (earth_x + 8, earth_y + 10), 12, (255, 150, 50), -1)  # Ocean
    cv2.circle(frame, (earth_x, earth_y), earth_radius, (255, 255, 255), 2)  # Border
    cv2.putText(frame, "Earth", (earth_x - 22, earth_y + 55), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # === LAGRANGE POINT / EDGE SERVER (middle) ===
    edge_x, edge_y = 400, 120
    # Satellite shape
    cv2.rectangle(frame, (edge_x - 8, edge_y - 5), (edge_x + 8, edge_y + 5), (200, 200, 200), -1)
    cv2.rectangle(frame, (edge_x - 25, edge_y - 3), (edge_x - 8, edge_y + 3), (100, 150, 255), -1)  # Solar panel
    cv2.rectangle(frame, (edge_x + 8, edge_y - 3), (edge_x + 25, edge_y + 3), (100, 150, 255), -1)  # Solar panel
    cv2.putText(frame, "Edge AI", (edge_x - 25, edge_y + 25), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)
    
    # Connection lines (dashed effect)
    for i in range(0, 100, 15):
        offset = (frame_id * 3 + i) % 100
        # Rover to Edge
        lx1 = rover_x + 30 + int(offset * 1.5)
        ly1 = int(rover_y - 55 - offset * 1.2)
        cv2.circle(frame, (lx1, ly1), 2, (100, 255, 100), -1)
        
        # Edge to Earth
        lx2 = edge_x + 25 + int(offset * 1.2)
        ly2 = edge_y - int(offset * 0.3) + 20
        cv2.circle(frame, (lx2, ly2), 2, (100, 200, 255), -1)
    
    # === TITLE AND INFO ===
    # Main title
    cv2.putText(frame, "Interplanetary Network Simulation", (120, 35), 
                cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, "Latency-Masking Demo", (200, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 200, 255), 1)
    
    # Frame counter (important for demo)
    cv2.rectangle(frame, (10, 440), (200, 475), (40, 40, 40), -1)
    cv2.putText(frame, f"Frame: {frame_id:05d}", (20, 465), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    
    # Timestamp
    cv2.putText(frame, f"Time: {time.strftime('%H:%M:%S')}", (450, 465), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    # Status indicator
    status_color = (0, 255, 0) if frame_id % 30 < 25 else (0, 255, 255)
    cv2.circle(frame, (620, 460), 8, status_color, -1)
    cv2.putText(frame, "LIVE", (580, 465), cv2.FONT_HERSHEY_SIMPLEX, 0.4, status_color, 1)
    
    # === LEGEND BOX ===
    cv2.rectangle(frame, (10, 80), (150, 180), (30, 30, 30), -1)
    cv2.rectangle(frame, (10, 80), (150, 180), (100, 100, 100), 1)
    cv2.putText(frame, "Demo Legend:", (15, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.circle(frame, (25, 120), 5, (0, 255, 255), -1)
    cv2.putText(frame, "Data Packet", (35, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
    cv2.circle(frame, (25, 145), 5, (100, 255, 100), -1)
    cv2.putText(frame, "AI Prediction", (35, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
    cv2.circle(frame, (25, 170), 5, (100, 200, 255), -1)
    cv2.putText(frame, "To Earth", (35, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
    
    return frame


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    global VIDEO_SOURCE, SOURCE_TYPE
    
    init_signing_key()
    print("=" * 50)
    print("Mars Emulator - Sender Started")
    print("=" * 50)
    print(f"Public key: {base64.b64encode(bytes(SIGNING_KEY.verify_key)).decode()[:32]}...")
    
    # Check for video file first
    video_file = find_video_file()
    if video_file:
        print(f"📹 Found video file: {video_file.name}")
        SOURCE_TYPE = "video"
        VIDEO_SOURCE = str(video_file)
    else:
        # Try webcam
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            print("📷 Using webcam")
            SOURCE_TYPE = "webcam"
            cap.release()
        else:
            print("⚠️  No video source found, using test pattern")
            print(f"   Add a video file to: {DATASET_DIR}")
            SOURCE_TYPE = "test"
    
    print("=" * 50)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "component": "sender",
        "status": "running",
        "source_type": SOURCE_TYPE,
        "video_source": VIDEO_SOURCE if SOURCE_TYPE == "video" else None,
        "public_key": base64.b64encode(bytes(SIGNING_KEY.verify_key)).decode() if SIGNING_KEY else None
    }


@app.get("/public-key")
async def get_public_key():
    """Get the sender's public key for verification."""
    if SIGNING_KEY is None:
        init_signing_key()
    return {
        "public_key": base64.b64encode(bytes(SIGNING_KEY.verify_key)).decode()
    }


@app.get("/sources")
async def list_sources():
    """List available video sources."""
    sources = {
        "webcam_available": False,
        "video_files": [],
        "current_source": SOURCE_TYPE
    }
    
    # Check webcam
    cap = cv2.VideoCapture(0)
    sources["webcam_available"] = cap.isOpened()
    cap.release()
    
    # List video files
    if DATASET_DIR.exists():
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        for ext in video_extensions:
            for f in DATASET_DIR.glob(f'*{ext}'):
                sources["video_files"].append(f.name)
    
    return sources


@app.websocket("/stream")
async def stream_video(websocket: WebSocket):
    """WebSocket endpoint for streaming signed video frames."""
    await websocket.accept()
    print(f"Client connected - Streaming from: {SOURCE_TYPE}")
    
    cap = None
    frame_id = 0
    keyframe_interval = 30
    
    try:
        # Initialize video capture based on source type
        if SOURCE_TYPE == "webcam":
            cap = cv2.VideoCapture(0)
        elif SOURCE_TYPE == "video":
            cap = cv2.VideoCapture(VIDEO_SOURCE)
            if cap.isOpened():
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS) or 30
                print(f"Video: {total_frames} frames at {fps:.1f} FPS")
        
        while True:
            frame = None
            
            if cap and cap.isOpened():
                ret, frame = cap.read()
                
                # Loop video file
                if not ret and SOURCE_TYPE == "video":
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                
                if not ret:
                    frame = generate_test_pattern(frame_id)
            else:
                frame = generate_test_pattern(frame_id)
            
            # Resize frame
            frame = cv2.resize(frame, (640, 480))
            
            # Encode frame
            frame_bytes = encode_frame_to_jpeg(frame)
            
            # Create metadata and sign
            timestamp = time.time()
            is_keyframe = (frame_id % keyframe_interval == 0)
            
            metadata = sign_frame_data(frame_bytes, frame_id, timestamp)
            metadata["is_keyframe"] = is_keyframe
            metadata["frame_size"] = len(frame_bytes)
            metadata["source_type"] = SOURCE_TYPE
            
            # Send frame
            await websocket.send_json({
                "type": "frame",
                "metadata": metadata,
                "data": base64.b64encode(frame_bytes).decode()
            })
            
            frame_id += 1
            
            # Control frame rate (~30 FPS for smooth playback)
            await asyncio.sleep(1/30)
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        if cap:
            cap.release()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
