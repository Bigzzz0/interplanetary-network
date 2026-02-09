# Interplanetary-Style Low-Latency Multi-Sensory Network

A working undergraduate-level prototype demonstrating a simplified *latency-masking* inter-node communication system using high-throughput links, edge prediction, and provenance metadata.

## 🚀 Project Overview

This project simulates interplanetary communication with predictive processing at an edge node to improve perceived latency for video streams, with clear instrumentation of link performance and cryptographic provenance verification.

### Architecture

```
┌─────────────┐     ┌───────────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Sender    │────▶│ Network Simulator │────▶│   Edge Server   │────▶│    Client    │
│ (Mars Node) │     │  (Delay/Jitter)   │     │ (Predictor/Edge)│     │(Earth Viewer)│
│  :8001      │     │      :8002        │     │     :8003       │     │    :8004     │
└─────────────┘     └───────────────────┘     └─────────────────┘     └──────────────┘
```

## 📦 Components

| Component | Port | Description |
|-----------|------|-------------|
| **Sender** | 8001 | Captures video frames, signs with Ed25519, streams via WebSocket |
| **Network Simulator** | 8002 | Injects configurable delay, jitter, and packet loss |
| **Edge Server** | 8003 | Runs optical flow prediction, generates synthesized frames, signs attestations |
| **Client** | 8004 | Browser-based UI for receiving and verifying video streams |

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
# Clone and enter project directory
cd network

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## 🚀 Running the System

Start each component in a separate terminal window, **in order**:

### Terminal 1 - Sender (Port 8001)
```bash
cd sender
python main.py
```

### Terminal 2 - Network Simulator (Port 8002)
```bash
cd network_simulator
python main.py
```

### Terminal 3 - Edge Server (Port 8003)
```bash
cd edge_server
python main.py
```

### Terminal 4 - Client (Port 8004)
```bash
cd client
python main.py
```

### Access the UI

Open your browser and navigate to: **http://localhost:8004**

Click "Connect to Stream" to start receiving video.

## 🔧 Configuration

### Network Simulator Settings

Adjust delay and packet loss via REST API:

```bash
# Get current config
curl http://localhost:8002/config

# Update delay to 5 seconds with 5% packet loss
curl -X POST "http://localhost:8002/config?base_delay_ms=5000&packet_loss_rate=0.05"
```

## 📊 Features

- ✅ **Ed25519 Cryptographic Signing** - Origin frames signed for provenance
- ✅ **Edge Attestation** - Synthesized frames carry edge server signatures
- ✅ **Optical Flow Prediction** - Frame interpolation reduces perceived latency
- ✅ **Real-time Metrics** - FPS, latency, frame counts in the UI
- ✅ **Confidence Display** - Visual indicator of prediction confidence
- ✅ **Provenance Badges** - Clear UI indication of verified vs synthesized frames

## 📁 Project Structure

```
network/
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── sender/                  # Mars Emulator
│   ├── __init__.py
│   └── main.py              # Video capture and signing
├── network_simulator/       # Delay/Loss Proxy
│   ├── __init__.py
│   └── main.py              # Configurable network simulation
├── edge_server/             # Lagrange Edge Predictor
│   ├── __init__.py
│   └── main.py              # Optical flow interpolation
└── client/                  # Earth Receiver
    ├── __init__.py
    ├── main.py              # WebSocket bridge server
    ├── index.html           # Main UI page
    ├── styles.css           # Premium dark theme
    └── app.js               # Client-side JavaScript
```

## 👥 Team Roles

- **Member 1**: Sender & Dataset
- **Member 2**: Edge Predictor
- **Member 3**: Client & UI
- **Member 4**: Network & Orchestration
- **Member 5**: Testing & Reports

## 📄 License

Computer Networks Course Project - Educational Use Only
