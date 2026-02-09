"""
Client Server (Earth Receiver) - Main Application
==================================================
Serves the browser-based UI and provides WebSocket bridge
to receive and display verified video streams.
"""

import asyncio
import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import websockets

app = FastAPI(
    title="Client (Earth Receiver)",
    description="Browser-based UI for receiving and verifying video streams",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the directory where this script is located
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))


@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/styles.css")
async def get_styles():
    """Serve the CSS file."""
    return FileResponse(os.path.join(STATIC_DIR, "styles.css"))


@app.get("/app.js")
async def get_script():
    """Serve the JavaScript file."""
    return FileResponse(os.path.join(STATIC_DIR, "app.js"))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "component": "client",
        "status": "running"
    }


@app.websocket("/stream")
async def stream_to_client(websocket: WebSocket):
    """
    WebSocket endpoint that bridges edge server to browser client.
    Receives processed frames from edge and forwards to browser.
    """
    await websocket.accept()
    print("Browser client connected")
    
    # Connect to edge server
    edge_uri = "ws://localhost:8003/process"
    
    try:
        async with websockets.connect(edge_uri) as edge_ws:
            print("Connected to edge server")
            
            async for message in edge_ws:
                try:
                    # Forward message to browser
                    await websocket.send_text(message)
                except Exception as e:
                    print(f"Error forwarding to browser: {e}")
                    break
                    
    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Connection error: {str(e)}"
        })
    except ConnectionRefusedError:
        print("Could not connect to edge server - is it running?")
        await websocket.send_json({
            "type": "error",
            "message": "Could not connect to edge server. Make sure all components are running."
        })
    except WebSocketDisconnect:
        print("Browser client disconnected")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
