# Interplanetary Network Simulator (Video + ML Edition)

A working undergraduate-level prototype demonstrating a *latency-masking* inter-node communication system with **real video streaming** and **ML-based frame interpolation**. This project simulates interplanetary communication with predictive processing at an edge node to ensure smooth 30FPS video playback despite heavy network lag.

## 🚀 Project Overview

This project simulates interplanetary communication with:
- **Real video capture** from webcam or pre-recorded datasets
- **ML-based frame interpolation** using RAFT optical flow
- **Quality metrics** (PSNR, SSIM) for prediction accuracy
- **Ed25519 cryptographic signing** for provenance verification

### Architecture

```
┌─────────────┐     ┌───────────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Sender    │────▶│ Network Simulator │────▶│   Edge Server   │────▶│    Client    │
│ (Mars Node) │     │  (Delay/Jitter)   │     │ (RAFT/ML Predictor)│  │(Earth Viewer)│
│  :8001      │     │      :8002        │     │     :8003       │     │    :8004     │
└─────────────┘     └───────────────────┘     └─────────────────┘     └──────────────┘
   Webcam/MJPEG         3000ms delay          Optical Flow             Dual Canvas
   H.264/MJPEG          Packet Loss           Frame Warping            Video Display
```

## 📦 Components

| Component | Port | Description |
|-----------|------|-------------|
| **Sender** | 8001 | Captures video (webcam/file), encodes as MJPEG, signs with Ed25519 |
| **Network Simulator** | 8002 | Injects configurable delay (default 3000ms), jitter, packet loss |
| **Edge Server** | 8003 | RAFT optical flow + frame interpolation, 30FPS synthesis, signs attestations |
| **Client** | 8004 | Browser UI with dual video streams (Delayed vs ML-Predicted) + quality metrics |

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- pip
- Webcam (optional, can use test pattern)
- NVIDIA GPU (optional, for ML acceleration)

### Setup

```bash
# Clone and enter project directory
cd interplanetary-network

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies (includes PyTorch, OpenCV, etc.)
pip install -r requirements.txt
```

## 🚀 Running the System

### Quick Start (Video Mode)

Start each component in a separate terminal window, **in order**:

### Terminal 1 - Sender (Port 8001)
```bash
cd sender
# Option A: Use webcam (or test pattern if no camera)
python main_video.py

# Option B: Use specific camera device
python main_video.py 1

# Option C: Use pre-recorded video file
python main_video.py ../dataset/video.mp4
```

### Terminal 2 - Network Simulator (Port 8002)
```bash
cd network_simulator
python main.py
```

### Terminal 3 - Edge Server (Port 8003)
```bash
cd edge_server
# ML version with RAFT optical flow
python main_ml.py
```

### Terminal 4 - Client (Port 8004)
```bash
cd client
python main.py
```

### Access the UI

Open your browser and navigate to: **http://localhost:8004**

Click "Start Comparison Demo" to begin receiving video streams.

### Using the Legacy Telemetry Mode

If you prefer the original 2D telemetry simulation:

```bash
# Terminal 1 - Sender (Telemetry)
cd sender
python main.py

# Terminal 3 - Edge Server (Linear Extrapolation)
cd edge_server
python main.py
```

## � Running with Docker

> **Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) must be installed and running.

### Start all services with one command

```bash
docker compose up --build
```

All 4 services will start in the correct order automatically. Then open **http://localhost:8004** in your browser.

### Stop all services

```bash
docker compose down
```

### View logs for a specific service

```bash
docker compose logs -f sender
docker compose logs -f network_simulator
docker compose logs -f edge_server
docker compose logs -f client
```

> **Note:** Signing keys (`sender_private_key.bin`, `edge_private_key.bin`) are generated fresh inside each container on first run. If you want persistent keys across restarts, mount them as Docker volumes.

## �🔧 Configuration


### Network Simulator Settings

Adjust delay and packet loss via REST API or via the Web UI controls:

```bash
# Get current config
curl http://localhost:8002/config

# Update delay to 5 seconds with 5% packet loss
curl -X POST "http://localhost:8002/config?base_delay_ms=5000&packet_loss_rate=0.05"
```

## 📊 Features

### Video & ML Features (New!)
- ✅ **Real Video Streaming** - MJPEG encoding from webcam or video files
- ✅ **ML-Based Frame Interpolation** - RAFT optical flow + frame warping
- ✅ **Quality Metrics** - PSNR, SSIM, Frame Match scores in real-time
- ✅ **Fallback to OpenCV** - Automatic fallback when PyTorch/RAFT unavailable

### Original Features
- ✅ **Ed25519 Cryptographic Signing** - Origin frames signed for provenance
- ✅ **Edge Attestation** - Synthesized frames carry edge server signatures
- ✅ **Continuous Extrapolation** - Smooth prediction logic masks network delays
- ✅ **Real-time Dual Tracking** - Side-by-side comparison of Delayed vs ML-Predicted streams
- ✅ **Live Metrics Graph** - Dynamic charts displaying network performance

## 📁 Project Structure

```
interplanetary-network/
├── docker-compose.yml          # Docker orchestration
├── .dockerignore               # Docker build exclusions
├── requirements.txt            # Python dependencies (PyTorch, OpenCV, etc.)
├── README.md                   # This file
├── VIDEO_IMPLEMENTATION.md     # Video/ML implementation guide
├── architecture_spec_and_implementation_plan.md
├── run_demo.py                 # Demo runner script
├── sender/                     # Mars Emulator
│   ├── Dockerfile
│   ├── main.py                 # Legacy: 2D telemetry generator
│   └── main_video.py           # NEW: Video capture & MJPEG streaming
├── network_simulator/          # Delay/Loss Proxy
│   ├── Dockerfile
│   └── main.py                 # Configurable network simulation
├── edge_server/                # Lagrange Edge Predictor
│   ├── Dockerfile
│   ├── main.py                 # Legacy: Linear extrapolation
│   └── main_ml.py              # NEW: RAFT optical flow + ML interpolation
└── client/                     # Earth Receiver
    ├── Dockerfile
    ├── main.py                 # WebSocket bridge server
    ├── index.html              # Main UI page
    ├── styles.css              # Premium dark theme
    ├── app.js                  # Legacy: Telemetry rendering
    └── app_video.js            # NEW: Video rendering & ML metrics
```

## 👥 Team Roles

| Name | Responsibility |
|------|----------------|
| **Tankun** | Sender & Data Preparation |
| **Sikarin** | AI Algorithm & Edge Node Logic (RAFT/ML) |
| **Sorawit** | Client UI & Signature Verification |
| **Sapphanyu** | Network Simulation & Control System |
| **Teeramet** | Evaluation & Reporting |

## 📚 Documentation

- **[VIDEO_IMPLEMENTATION.md](VIDEO_IMPLEMENTATION.md)** - Detailed guide for video/ML features
- **[architecture_spec_and_implementation_plan.md](architecture_spec_and_implementation_plan.md)** - Original project specification

## 📄 License

Computer Networks Course Project - Educational Use Only
