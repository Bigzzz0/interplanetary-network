"""
Sender (Mars Emulator) - Main Application
==========================================
Simulates Mars Rover telemetry (2D coordinates).
Signs telemetry data with Ed25519 and streams via WebSocket.
"""

import asyncio
import json
import time
import base64
import os
import math
from pathlib import Path
from typing import Optional

from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="Sender (Mars Emulator)",
    description="Simulates and signs telemetry data for transmission",
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
SIGNING_KEY: Optional[SigningKey] = None
SOURCE_TYPE = "telemetry"

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


def generate_telemetry_payload(frame_id: int) -> dict:
    speed = 2
    period = 250
    cycle = frame_id % (period * 2)
    
    if cycle < period:
        # Moving right
        x = 50 + (cycle * speed)
        direction = "east"
    else:
        # Moving left
        x = 50 + (period * speed) - ((cycle - period) * speed)
        direction = "west"
        
    y = 240 + (frame_id % 10) - 5 # slight bumpiness
    
    return {
        "rover_x": x,
        "rover_y": y,
        "state": f"moving_{direction}",
        "battery": max(0, 100 - (frame_id % 1000) / 10),
        "temperature": -60 + (frame_id % 20) / 2
    }


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    init_signing_key()
    print("=" * 50)
    print("Mars Emulator (Telemetry) - Sender Started")
    print("=" * 50)
    print(f"Public key: {base64.b64encode(bytes(SIGNING_KEY.verify_key)).decode()[:32]}...")
    print("=" * 50)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "component": "sender",
        "status": "running",
        "source_type": SOURCE_TYPE,
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


@app.websocket("/stream")
async def stream_video(websocket: WebSocket):
    """WebSocket endpoint for streaming signed telemetry frames."""
    await websocket.accept()
    print(f"Client connected - Streaming from: {SOURCE_TYPE}")
    
    frame_id = 0
    keyframe_interval = 30
    
    try:
        while True:
            # Generate telemetry
            payload = generate_telemetry_payload(frame_id)
            payload_json = json.dumps(payload)
            payload_bytes = payload_json.encode('utf-8')
            
            # Create metadata and sign
            timestamp = time.time()
            is_keyframe = (frame_id % keyframe_interval == 0)
            
            metadata = sign_frame_data(payload_bytes, frame_id, timestamp)
            metadata["is_keyframe"] = is_keyframe
            metadata["frame_size"] = len(payload_bytes)
            metadata["source_type"] = SOURCE_TYPE
            
            # Send frame
            await websocket.send_json({
                "type": "frame",
                "metadata": metadata,
                # Encode telemetry data as base64 to match the existing expected structure, 
                # or just send it as a string. Base64 is safer for existing proxies.
                "data": base64.b64encode(payload_bytes).decode('utf-8')
            })
            
            frame_id += 1
            
            # Control frame rate (~30 FPS for smooth playback)
            await asyncio.sleep(1/30)
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Stream error: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
