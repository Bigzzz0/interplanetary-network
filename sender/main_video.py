"""
Sender (Mars Emulator) - Video/Audio Version
=============================================
Captures real video from webcam or loads pre-recorded dataset.
Encodes frames as MJPEG, signs with Ed25519, and streams via WebSocket.
"""

import asyncio
import json
import time
import base64
import os
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import sounddevice as sd
except ImportError:
    print("[WARN] sounddevice not found, audio capture will be disabled")
    sd = None


from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="Sender (Mars Emulator) - Video",
    description="Captures video, encodes as MJPEG, signs frames, and streams via WebSocket",
    version="2.0.0"
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
SOURCE_TYPE = "dataset"  # Can be "video" or "dataset"

# Auto-detect video file in dataset folder
DATASET_DIR = Path(__file__).parent.parent / "dataset"

# Specify video file directly (change this to your video file)
VIDEO_FILE = DATASET_DIR / "demo_video.mp4"

# Auto-detect fallback (if VIDEO_FILE doesn't exist)
if VIDEO_FILE and not VIDEO_FILE.exists():
    VIDEO_FILE = None
    for ext in ["*.mp4", "*.avi", "*.mov", "*.mkv", "*.webm"]:
        videos = list(DATASET_DIR.glob(ext))
        if videos:
            VIDEO_FILE = str(videos[0])
            break

VIDEO_SOURCE = VIDEO_FILE if VIDEO_FILE else 0  # Use file if found, else webcam
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30
QUALITY = 85
KEYFRAME_INTERVAL = 30  # Sign every Nth frame as keyframe

# Global state
camera: Optional[cv2.VideoCapture] = None
frame_count = 0


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


def sign_frame_data(frame_data: bytes, frame_id: int, timestamp: float, is_keyframe: bool) -> dict:
    """Sign frame data and create metadata."""
    if SIGNING_KEY is None:
        init_signing_key()

    message = f"{frame_id}:{timestamp}:{len(frame_data)}:{is_keyframe}".encode()
    signed = SIGNING_KEY.sign(message, encoder=Base64Encoder)

    return {
        "frame_id": frame_id,
        "timestamp": timestamp,
        "signature": signed.signature.decode(),
        "public_key": base64.b64encode(bytes(SIGNING_KEY.verify_key)).decode(),
        "is_keyframe": is_keyframe,
        "frame_size": len(frame_data),
        "source_type": SOURCE_TYPE
    }


def encode_frame_as_mjpeg(frame: np.ndarray, quality: int = 85) -> bytes:
    """Encode a single frame as JPEG (MJPEG stream)."""
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, encoded = cv2.imencode('.jpg', frame, encode_param)
    return encoded.tobytes()


def capture_frame() -> Optional[np.ndarray]:
    """Capture a single frame from camera or dataset."""
    global camera, frame_count
    
    if camera is None:
        # Initialize camera
        if isinstance(VIDEO_SOURCE, int) and VIDEO_SOURCE >= 0:
            camera = cv2.VideoCapture(VIDEO_SOURCE)
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            camera.set(cv2.CAP_PROP_FPS, FPS)
            print(f"Camera initialized: {FRAME_WIDTH}x{FRAME_HEIGHT}@{FPS}fps")
        else:
            # Load from video file
            if os.path.exists(VIDEO_SOURCE):
                camera = cv2.VideoCapture(VIDEO_SOURCE)
                print(f"Loading dataset: {VIDEO_SOURCE}")
                # Get original video dimensions
                orig_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                orig_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"Original video size: {orig_width}x{orig_height}")
            else:
                print(f"Video file not found: {VIDEO_SOURCE}")
                return None
    
    if camera is not None and camera.isOpened():
        ret, frame = camera.read()
        if ret:
            frame_count += 1
            # Resize maintaining aspect ratio with letterboxing
            h, w = frame.shape[:2]
            target_w, target_h = FRAME_WIDTH, FRAME_HEIGHT
            
            # Calculate scale
            scale = min(target_w / w, target_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            
            # Resize
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # Create black canvas and center the video
            canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
            y_offset = (target_h - new_h) // 2
            x_offset = (target_w - new_w) // 2
            canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
            
            return canvas
        else:
            # End of video file, loop back
            if isinstance(VIDEO_SOURCE, str):
                camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = camera.read()
                if ret:
                    frame_count += 1
                    # Same resize logic
                    h, w = frame.shape[:2]
                    target_w, target_h = FRAME_WIDTH, FRAME_HEIGHT
                    scale = min(target_w / w, target_h / h)
                    new_w, new_h = int(w * scale), int(h * scale)
                    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                    y_offset = (target_h - new_h) // 2
                    x_offset = (target_w - new_w) // 2
                    canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
                    return canvas
            return None
    return None


def create_test_pattern(frame_id: int) -> np.ndarray:
    """Create a test pattern frame for demo without camera."""
    frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH, 3), dtype=np.uint8)
    
    # Draw moving circle
    cx = FRAME_WIDTH // 2 + int(np.sin(frame_id * 0.1) * 100)
    cy = FRAME_HEIGHT // 2 + int(np.cos(frame_id * 0.1) * 50)
    cv2.circle(frame, (cx, cy), 50, (0, 255, 255), -1)
    
    # Draw grid
    for x in range(0, FRAME_WIDTH, 40):
        cv2.line(frame, (x, 0), (x, FRAME_HEIGHT), (30, 30, 60), 1)
    for y in range(0, FRAME_HEIGHT, 40):
        cv2.line(frame, (0, y), (FRAME_WIDTH, y), (30, 30, 60), 1)
    
    # Draw text
    cv2.putText(frame, f"Frame: {frame_id}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, "Mars Rover Cam", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    return frame


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    init_signing_key()
    print("=" * 60)
    print("[VIDEO] Mars Emulator (Video) - Sender Started")
    print("=" * 60)
    print(f"Source: {SOURCE_TYPE}")
    if isinstance(VIDEO_SOURCE, str):
        print(f"Video file: {VIDEO_SOURCE}")
    else:
        print(f"Camera ID: {VIDEO_SOURCE}")
    print(f"Resolution: {FRAME_WIDTH}x{FRAME_HEIGHT}@{FPS}fps")
    print(f"Public key: {base64.b64encode(bytes(SIGNING_KEY.verify_key)).decode()[:32]}...")
    print("=" * 60)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "component": "sender",
        "status": "running",
        "source_type": SOURCE_TYPE,
        "resolution": f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
        "fps": FPS,
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


@app.get("/config")
async def get_config():
    """Get current configuration."""
    return {
        "source_type": SOURCE_TYPE,
        "video_source": VIDEO_SOURCE,
        "resolution": f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
        "fps": FPS,
        "keyframe_interval": KEYFRAME_INTERVAL,
        "encoding": "MJPEG"
    }


@app.websocket("/stream")
async def stream_video(websocket: WebSocket):
    """WebSocket endpoint for streaming signed video frames & audio."""
    await websocket.accept()
    print(f"Client connected - Streaming video from: {SOURCE_TYPE}")

    global frame_count
    frame_id = 0
    fps_counter = 0
    fps_display_time = time.time()

    send_queue = asyncio.Queue()
    is_streaming = True
    loop = asyncio.get_running_loop()

    # --- Audio Capture Setup ---
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        try:
            if is_streaming and not loop.is_closed():
                loop.call_soon_threadsafe(send_queue.put_nowait, {
                    "type": "audio",
                    "data": base64.b64encode(indata.tobytes()).decode('utf-8'),
                    "metadata": {
                        "timestamp": time.time(),
                        "samplerate": 16000,
                        "channels": 1,
                        "dtype": "float32"
                    }
                })
        except Exception:
            pass

    audio_stream = None
    if sd is not None:
        try:
            audio_stream = sd.InputStream(samplerate=16000, channels=1, dtype='float32', 
                                          blocksize=1024, callback=audio_callback)
            audio_stream.start()
        except Exception as e:
            print(f"Audio init failed (mic might not be available): {e}")

    async def video_capture_task():
        nonlocal frame_id, fps_counter, fps_display_time
        try:
            while is_streaming:
                frame_start_time = time.time()
                
                # Capture or generate frame
                if SOURCE_TYPE == "dataset" or (isinstance(VIDEO_SOURCE, str) and os.path.exists(VIDEO_SOURCE)):
                    frame = capture_frame()
                    if frame is None:
                        frame = create_test_pattern(frame_id)
                else:
                    frame = capture_frame()
                    if frame is None:
                        # Fallback to test pattern if camera not available
                        frame = create_test_pattern(frame_id)
                
                # Encode frame as JPEG
                encoded_frame = encode_frame_as_mjpeg(frame, quality=QUALITY)
                
                # Determine if keyframe
                is_keyframe = (frame_id % KEYFRAME_INTERVAL == 0)
                timestamp = time.time()
                
                # Sign the frame
                metadata = sign_frame_data(encoded_frame, frame_id, timestamp, is_keyframe)
                metadata["encoding"] = "mjpeg"
                metadata["width"] = FRAME_WIDTH
                metadata["height"] = FRAME_HEIGHT
                
                # Send frame
                await send_queue.put({
                    "type": "frame",
                    "metadata": metadata,
                    "data": base64.b64encode(encoded_frame).decode('utf-8')
                })
                
                frame_id += 1
                fps_counter += 1
                
                # Display FPS every second
                if time.time() - fps_display_time >= 1.0:
                    actual_fps = fps_counter / (time.time() - fps_display_time)
                    print(f"Streaming at {actual_fps:.1f} FPS | Frame {frame_id}")
                    fps_counter = 0
                    fps_display_time = time.time()
                
                # Control frame rate (~30 FPS for smooth playback)
                elapsed = time.time() - frame_start_time
                sleep_time = max(0, (1.0 / FPS) - elapsed)
                await asyncio.sleep(sleep_time)
        except Exception as e:
            if is_streaming:
                print(f"Video task error: {e}")

    async def sender_task():
        nonlocal is_streaming
        try:
            while is_streaming:
                msg = await send_queue.get()
                await websocket.send_json(msg)
        except Exception as e:
            # Client disconnected or socket closed
            pass
        finally:
            is_streaming = False

    async def receiver_task():
        global FRAME_WIDTH, FRAME_HEIGHT, FPS, QUALITY
        try:
            while is_streaming:
                msg = await websocket.receive_json()
                if msg.get("type") == "network_feedback":
                    delay = msg.get("delay", 0)
                    loss = msg.get("loss_rate", 0)
                    
                    old_fps = FPS
                    if delay > 2000 or loss > 0.05:
                        FRAME_WIDTH, FRAME_HEIGHT = 320, 240
                        FPS = 15
                        QUALITY = 50
                    elif delay > 1000 or loss > 0.02:
                        FRAME_WIDTH, FRAME_HEIGHT = 480, 360
                        FPS = 20
                        QUALITY = 65
                    else:
                        FRAME_WIDTH, FRAME_HEIGHT = 640, 480
                        FPS = 30
                        QUALITY = 85
                    
                    if old_fps != FPS and camera is not None and isinstance(VIDEO_SOURCE, int):
                        camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
                        camera.set(cv2.CAP_PROP_FPS, FPS)
                        print(f"ABR: Adjusted to {FRAME_WIDTH}x{FRAME_HEIGHT}@{FPS}fps, Q={QUALITY}")
        except Exception:
            pass

    try:
        # Run tasks concurrently
        await asyncio.gather(
            video_capture_task(),
            sender_task(),
            receiver_task()
        )
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        is_streaming = False
        if audio_stream is not None:
            audio_stream.stop()
            audio_stream.close()
        if camera is not None:
            camera.release()


if __name__ == "__main__":
    # Check for command line args or environment variables
    import sys
    if len(sys.argv) > 1:
        VIDEO_SOURCE = sys.argv[1]
        if VIDEO_SOURCE.isdigit():
            VIDEO_SOURCE = int(VIDEO_SOURCE)
        SOURCE_TYPE = "dataset" if isinstance(VIDEO_SOURCE, str) else "video"
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
