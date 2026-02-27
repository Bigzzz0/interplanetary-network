# Interplanetary Network Simulator (2D Telemetry Edition)

A working undergraduate-level prototype demonstrating a simplified *latency-masking* inter-node communication system. This project simulates the transmission of planetary rovers exchanging delayed telemetry data, utilizing Edge predictive extrapolation to ensure a smooth, real-time UI experience despite heavy network lag.

## 🚀 Project Overview

This project simulates interplanetary communication with predictive processing at an edge node to improve perceived latency for telemetry streams, supported by clear instrumentation of link performance and cryptographic provenance verification.

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
| **Sender** | 8001 | Simulates a Mars rover, generating 2D telemetry (X, Y, Battery, Temp), signs with Ed25519, streams via WebSocket |
| **Network Simulator** | 8002 | Injects configurable delay (default 3000ms), jitter, and packet loss |
| **Edge Server** | 8003 | Runs continuous linear extrapolation with damping, generates smooth 30FPS synthesized frames, signs attestations |
| **Client** | 8004 | Premium browser-based UI rendering dual HTML5 Canvas streams (Delayed vs Predicted) with real-time analytics graphs |

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
# Clone and enter project directory
cd interplanetary-network

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

Open your browser and navigate to: **http://localhost:8004** (or `http://localhost:8000` depending on the hosting method).
Click "Start Comparison Demo" to begin receiving telemetry.

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

- ✅ **Ed25519 Cryptographic Signing** - Origin frames signed for provenance
- ✅ **Edge Attestation** - Synthesized frames carry edge server signatures
- ✅ **Continuous Extrapolation** - Smooth prediction logic completely masks 3-second network delays without "rubber-banding"
- ✅ **Real-time Dual Tracking** - Side-by-side comparison of Raw Network Delay vs Edge-Predictive Stream
- ✅ **Live Metrics Graph** - Dynamically drawn charts displaying network performance

## 📁 Project Structure

```
interplanetary-network/
├── docker-compose.yml       # Docker orchestration (all 4 services)
├── .dockerignore            # Docker build exclusions
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── sender/                  # Mars Emulator
│   ├── Dockerfile
│   └── main.py              # Telemetry generator and signing
├── network_simulator/       # Delay/Loss Proxy
│   ├── Dockerfile
│   └── main.py              # Configurable network simulation
├── edge_server/             # Lagrange Edge Predictor
│   ├── Dockerfile
│   └── main.py              # Continuous 30FPS extrapolation
└── client/                  # Earth Receiver
    ├── Dockerfile
    ├── main.py              # WebSocket bridge server
    ├── index.html           # Main UI page
    ├── styles.css           # Premium dark theme
    └── app.js               # Dual-canvas rendering & analytics
```

## 👥 Team Roles

| Name | Responsibility |
|------|----------------|
| **Tankun** | Sender & Data Preparation |
| **Sikarin** | AI Algorithm & Edge Node Logic |
| **Sorawit** | Client UI & Signature Verification |
| **Sapphanyu** | Network Simulation & Control System |
| **Teeramet** | Evaluation & Reporting |

## 📄 License

Computer Networks Course Project - Educational Use Only
