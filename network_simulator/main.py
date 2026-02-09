"""
Network Simulator - Main Application
=====================================
Proxy server that simulates network latency, jitter, and packet loss
to emulate Earth-Mars communication characteristics.
"""

import asyncio
import json
import random
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import websockets

app = FastAPI(
    title="Network Simulator",
    description="Simulates latency and packet loss for interplanetary communication",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class NetworkConfig:
    """Configuration for network simulation parameters."""
    base_delay_ms: int = 3000  # Base delay in milliseconds (3 seconds default)
    jitter_ms: int = 500  # Random jitter range
    packet_loss_rate: float = 0.02  # 2% packet loss
    bandwidth_limit_kbps: Optional[int] = None  # Optional bandwidth limit


# Default configuration
config = NetworkConfig()

# Metrics tracking
metrics: Dict[str, Any] = {
    "packets_forwarded": 0,
    "packets_dropped": 0,
    "total_bytes": 0,
    "avg_delay_ms": 0,
    "start_time": time.time()
}


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "component": "network_simulator",
        "status": "running",
        "config": asdict(config)
    }


@app.get("/config")
async def get_config():
    """Get current network simulation configuration."""
    return asdict(config)


@app.post("/config")
async def update_config(
    base_delay_ms: Optional[int] = None,
    jitter_ms: Optional[int] = None,
    packet_loss_rate: Optional[float] = None,
    bandwidth_limit_kbps: Optional[int] = None
):
    """Update network simulation configuration."""
    global config
    if base_delay_ms is not None:
        config.base_delay_ms = base_delay_ms
    if jitter_ms is not None:
        config.jitter_ms = jitter_ms
    if packet_loss_rate is not None:
        config.packet_loss_rate = max(0, min(1, packet_loss_rate))
    if bandwidth_limit_kbps is not None:
        config.bandwidth_limit_kbps = bandwidth_limit_kbps
    
    return {"status": "updated", "config": asdict(config)}


@app.get("/metrics")
async def get_metrics():
    """Get network simulation metrics."""
    uptime = time.time() - metrics["start_time"]
    return {
        **metrics,
        "uptime_seconds": uptime,
        "loss_rate": metrics["packets_dropped"] / max(1, metrics["packets_forwarded"] + metrics["packets_dropped"])
    }


@app.post("/reset-metrics")
async def reset_metrics():
    """Reset network simulation metrics."""
    global metrics
    metrics = {
        "packets_forwarded": 0,
        "packets_dropped": 0,
        "total_bytes": 0,
        "avg_delay_ms": 0,
        "start_time": time.time()
    }
    return {"status": "metrics_reset"}


def calculate_delay() -> float:
    """Calculate delay with jitter."""
    jitter = random.uniform(-config.jitter_ms, config.jitter_ms)
    return max(0, config.base_delay_ms + jitter) / 1000.0


def should_drop_packet() -> bool:
    """Determine if packet should be dropped based on loss rate."""
    return random.random() < config.packet_loss_rate


@app.websocket("/proxy")
async def proxy_connection(websocket: WebSocket):
    """
    WebSocket proxy that forwards data with simulated network conditions.
    Connects to sender and forwards to edge server with delay.
    """
    await websocket.accept()
    print("Proxy connection established")
    
    # Connect to sender
    sender_uri = "ws://localhost:8001/stream"
    
    try:
        async with websockets.connect(sender_uri) as sender_ws:
            print("Connected to sender")
            
            async def forward_with_delay():
                """Forward messages from sender to client with delay."""
                async for message in sender_ws:
                    # Check for packet loss
                    if should_drop_packet():
                        metrics["packets_dropped"] += 1
                        print(f"Packet dropped (simulated loss)")
                        continue
                    
                    # Calculate and apply delay
                    delay = calculate_delay()
                    await asyncio.sleep(delay)
                    
                    # Parse message to add network metadata
                    try:
                        data = json.loads(message)
                        data["network_metadata"] = {
                            "simulated_delay_ms": delay * 1000,
                            "proxy_timestamp": time.time(),
                            "config": asdict(config)
                        }
                        message = json.dumps(data)
                    except json.JSONDecodeError:
                        pass
                    
                    # Forward message
                    await websocket.send_text(message)
                    
                    # Update metrics
                    metrics["packets_forwarded"] += 1
                    metrics["total_bytes"] += len(message)
                    
                    # Update average delay (exponential moving average)
                    alpha = 0.1
                    metrics["avg_delay_ms"] = (
                        alpha * (delay * 1000) +
                        (1 - alpha) * metrics["avg_delay_ms"]
                    )
            
            await forward_with_delay()
            
    except websockets.exceptions.WebSocketException as e:
        print(f"WebSocket error: {e}")
    except ConnectionRefusedError:
        print("Could not connect to sender - is it running?")
        await websocket.send_json({
            "type": "error",
            "message": "Could not connect to sender"
        })
    except WebSocketDisconnect:
        print("Proxy client disconnected")


@app.websocket("/forward")
async def forward_to_edge(websocket: WebSocket):
    """
    WebSocket endpoint for forwarding data to edge server.
    Acts as intermediary between sender and edge.
    """
    await websocket.accept()
    print("Forward connection established")
    
    pending_messages = asyncio.Queue()
    
    async def receive_messages():
        """Receive messages from client and queue for forwarding."""
        try:
            while True:
                data = await websocket.receive_text()
                await pending_messages.put(data)
        except WebSocketDisconnect:
            await pending_messages.put(None)
    
    async def forward_messages():
        """Forward queued messages with delay."""
        while True:
            message = await pending_messages.get()
            if message is None:
                break
            
            # Check for packet loss
            if should_drop_packet():
                metrics["packets_dropped"] += 1
                continue
            
            # Apply delay
            delay = calculate_delay()
            await asyncio.sleep(delay)
            
            # Forward message
            await websocket.send_text(message)
            metrics["packets_forwarded"] += 1
    
    try:
        await asyncio.gather(receive_messages(), forward_messages())
    except Exception as e:
        print(f"Forward error: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
