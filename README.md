# 🌌 Interplanetary Network: Advanced Latency-Masking Video System

[![Computer Networks](https://img.shields.io/badge/Course-Computer%20Networks-blue.svg)](https://)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://)
[![ML-Powered](https://img.shields.io/badge/ML-PyTorch%20%7C%20RAFT%20%7C%20DAIN-orange.svg)](https://)

An undergraduate-level high-performance prototype demonstrating how extreme interplanetary latencies (Mars-to-Earth) can be mitigated using **Edge-Compute Prediction** and **ML-based Frame Interpolation**. This project bridges the gap between traditional networking and modern AI to deliver seamless 60FPS-equivalent video even over unstable 5,000ms+ delay links.

---

## 📖 Table of Contents
1. [Core Philosophy](#🚀-core-philosophy)
2. [Architectural Deep-Dive](#🛰️-architectural-deep-dive)
3. [The ML Engine (RAFT & DAIN)](#🧠-the-ml-engine-raft--dain)
4. [Advanced Network Simulation](#🪐-advanced-network-simulation)
5. [Security & Cryptography](#🔒-security--cryptography)
6. [Component Reference](#📦-component-reference)
7. [Installation & Setup](#🛠️-installation--setup)
8. [Evaluation & Metrics](#📊-evaluation--metrics)
9. [Project Structure](#📁-project-structure)

---

## 🚀 Core Philosophy

Interplanetary communication is governed by the speed of light. A round-trip to Mars takes between **3 and 22 minutes**. Traditional TCP/UDP streaming fails because:
*   **ACK-Wait:** Handshaking takes minutes.
*   **Jitter:** Orbital relative velocities and atmosphere cause massive fluctuations in packet arrival.
*   **Buffer Bloat:** Traditional buffering adds even more latency.

**Our Solution:** Instead of waiting for the real frame to arrive to play it, we use an **Edge Node (Lagrange Punkt)** to predict and synthesize the missing motion, results in a perfectly fluid experience for the end-user on Earth while the slow data trickle continues in the background.

---

## 🛰️ Architectural Deep-Dive

The system operates as a 4-node sequential relay:

### 1. Mars Node (Sender) - `Port 8001`
*   **Capture:** Real-time OpenCV video capture (webcam or MP4 dataset).
*   **Encoding:** High-frequency MJPEG encoding (optimized for per-frame processing).
*   **Signing:** Generates 512-bit Ed25519 signatures for every frame.
*   **Protocol:** Pushes JSON packets containing Base64 data and metadata.

### 2. Space Relay (Network Simulator) - `Port 8002`
*   **Chronological Queue:** Implements a priority-based async delivery mechanism. It ensures that while jitter can bounce frames around, they are delivered in strict timestamp order to the next node.
*   **Rubber-Banding:** Injects randomized 1.0s–3.0s "Rubber-band" spikes to simulate severe signal fading.

### 3. Lagrange Node (Edge Server) - `Port 8003`
*   **Burst Ingestion:** An `asyncio.Queue` swallows bursts of packets from the simulator.
*   **Paced Synthesis:** A fixed-rate predictor task interpolates between the last two known real frames at exactly 33ms/16ms intervals.
*   **Dual-Path Forwarding:** Immediately forwards raw data to the client (to prevent blanking) while slipping ML-generated frames into the stream asynchronously.

### 4. Earth Node (Client) - `Port 8004`
*   **Dual-Canvas Rendering:** Side-by-side comparison.
*   **Telemetry Hub:** Real-time PSNR/SSIM calculation and packet tracking.
*   **Adaptive UI:** Dynamically reacts to model changes (RAFT vs DAIN).

---

## 🧠 The ML Engine (RAFT & DAIN)

The Lagrange node features two interchangeable interpolation architectures:

### RAFT (Recurrent All-Pairs Field Transforms)
Implemented in `edge_server/raft.py`:
*   **Mechanism:** Uses a correlation volume and a GRU-based recurrent update block to estimate highly accurate optical flow between two frames ($I_1, I_2$).
*   **Interpolation:** Frames are warped forward using the estimated flow vectors to create a synthetic intermediate state.

### DAIN (Depth-Aware Video Frame Interpolation)
Implemented in `edge_server/dain.py`:
*   **Depth Estimation:** Small sub-network estimates foreground/background depth layers ($D$).
*   **Adaptive Warping:** Uses depth values to weigh pixels during warping, preventing "ghosting" artifacts where foreground objects pass over background details.
*   **Refinement:** A post-warping CNN cleans up interpolation artifacts for 1080p-ready aesthetics.

---

## 🪐 Advanced Network Simulation

The project includes a theoretical model for **Rubber-Banding**.

When a lag spike occurs, subsequent packets "pile up" behind it. Our `network_simulator/main.py` handles this with:
1.  **Monotonic Clocks:** Every packet is assigned a `send_time = arrival_time + delay`.
2.  **Sequential Flush:** When a delay resolves, the queue flushes the accumulated packets in order. 
    *   *Baseline Effect:* Video freezes, then plays in "Fast Forward" (Choppy).
    *   *ML Effect:* The Edge Server absorbs the burst and plays them out at a **smooth, continuous pace**, effectively time-shifting the stream to hide the network physical anomaly.

---

## 🔒 Security & Cryptography

Every frame's provenance is verified using the **Ed25519** elliptic curve algorithm:
1.  **Mars Signature:** `Sign(PrivateKey_Mars, Frame_Hash)`
2.  **Lagrange Attestation:** `Sign(PrivateKey_Lagrange, SynthFrame_Hash + Parent_Hashes)`
3.  **Client-Side Check:** The UI marks frames with a Green/Red checkmark. If a hacker intercepts the proxy and modifies a frame (e.g., bit-flipping), the signature failure is instantly logged.

---

## 📦 Component Reference

### REST API Endpoints
| Component | Endpoint | Method | Description |
|-----------|----------|--------|-------------|
| **Proxy** | `/config` | POST | Adjust `base_delay_ms`, `jitter_ms`, `packet_loss_rate`. |
| **Proxy** | `/metrics` | GET | Retrieve throughput and uptime. |
| **Edge** | `/config` | POST | Set `interpolation_frames` or toggle `model_type` (RAFT/DAIN). |
| **Client** | `/health` | GET | Check system readiness. |

### WebSocket Hubs
*   `ws://localhost:8001/stream`: Raw Mars Output.
*   `ws://localhost:8002/proxy`: The Delayed Space Link.
*   `ws://localhost:8003/process`: The ML Enrichment Channel.
*   `ws://localhost:8004/stream`: The final UI consumer.

---

## 🛠️ Installation & Setup

### Prerequisites
*   Python 3.10+
*   NVIDIA GPU (CUDA 11.8+) - *Recommended for DAIN*
*   OpenCV + FFmpeg

### Windows Installation
```powershell
# Setup environment
python -m venv venv
.\venv\Scripts\activate

# Install core and ML libraries
pip install -r requirements.txt
```

### 🚀 Launching the Demo
We provide a unified orchestrator that starts all 4 nodes with appropriate environment variables:
```powershell
python run_demo.py
```

---

## 📊 Evaluation & Metrics

The system measures its own performance using:
*   **PSNR (Peak Signal-to-Noise Ratio):** Measures byte-level reconstruction quality (Goal: >35dB).
*   **SSIM (Structural Similarity Index):** Measures perceptual quality and motion consistency (Goal: >0.90).
*   **Throughput:** Real-time bandwidth tracking on Earth receiver.

---

## 📁 Project Structure

```text
interplanetary-network/
├── client/              # Earth Node
│   ├── main.py          # FastAPI bridge
│   └── app_video.js     # Dual-canvas JS renderer
├── edge_server/         # Lagrange Node (Prediction Hub)
│   ├── main_ml.py       # ML Orchestration & Orchestration
│   ├── raft.py          # Optical Flow Algorithm
│   └── dain.py          # Depth-Aware Warp Algorithm
├── network_simulator/   # Space Link Emulator
│   └── main.py          # Queue-based Delay Proxy
├── sender/              # Mars Node (Source)
│   └── main_video.py    # Signed MJPEG Streaming
├── run_demo.py          # One-click Launcher
└── requirements.txt     # Global dependencies
```

---

## 👥 Authors
*   **Tankun** - Sender & Data Preparation
*   **Sikarin** - AI Algorithm & Edge Node Logic
*   **Sorawit** - Client UI & Signature Verification
*   **Sapphanyu** - Network Simulation & Control
*   **Teeramet** - Evaluation & Reporting

---

## 📄 License
Computer Networks Course Project - Educational Use Only.
© 2026 Interplanetary Network Team.
