# 🔧 Troubleshooting Video Display Issues

## Problem: Only seeing gear icon / no video

### Solution 1: Use the Quick Start Guide

1. Run `python run_demo.py`
2. A web page will open at `http://localhost:8080` (or similar)
3. **Select a video** from the list
4. **Click "Start System"** button
5. Wait for all 4 components to start (green indicators)
6. **Click "Open Client UI"** button
7. On the client page, **click "Start Comparison Demo"** button
8. Video should now appear!

### Solution 2: Check Component Status

Open the run_demo web UI and check the status panel:
- All 4 nodes should show **green** (Running)
- If any show **red** (Stopped), click "Stop System" and try again

### Solution 3: Manual Component Launch

If auto-start isn't working, launch components manually:

```bash
# Terminal 1 - Sender
cd src/sender
python main_video.py

# Terminal 2 - Network Simulator
cd src/network_simulator
python main.py

# Terminal 3 - Edge Server
cd src/edge_server
python main_ml.py

# Terminal 4 - Client
cd src/client
python main.py
```

Then open **http://localhost:8004** in your browser.

### Solution 4: Check for Port Conflicts

```bash
# Windows: Check if ports are in use
netstat -ano | findstr :8001
netstat -ano | findstr :8002
netstat -ano | findstr :8003
netstat -ano | findstr :8004

# Kill processes if needed
taskkill /PID <PID> /F
```

### Solution 5: Check Logs

Look in the `logs/` directory:
```bash
cd logs
# Check the most recent log files
type sender_video.log
type edge_server_ml.log
```

### Solution 6: Verify Video File

Make sure you have a video file in the `dataset/` folder:

```bash
# Check dataset folder
dir dataset\*.mp4
dir dataset\*.avi
```

If no videos exist, add one or the system will use a test pattern.

### Solution 7: Check Python Dependencies

```bash
# Verify all dependencies are installed
pip install -r requirements.txt

# Specifically check OpenCV and PyTorch
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "import torch; print('PyTorch:', torch.__version__)"
```

### Common Error Messages

#### "Camera initialization failed"
- **Cause:** No webcam connected
- **Solution:** System will auto-fallback to test pattern or dataset video

#### "Could not connect to edge server"
- **Cause:** Edge server not running
- **Solution:** Make sure all 4 components are started

#### "WebSocket connection failed"
- **Cause:** Port conflict or firewall
- **Solution:** Check firewall settings, allow Python through

### Still Not Working?

1. **Restart everything:**
   ```bash
   # Stop all components
   # Close all terminals
   python run_demo.py
   ```

2. **Check system requirements:**
   - Python 3.10+
   - 8GB+ RAM
   - Windows 10/11 or Linux

3. **Run tests:**
   ```bash
   cd tests
   python test_ml.py
   python test_integration.py
   ```

4. **Check the logs for errors:**
   - `logs/sender_(video).log`
   - `logs/edge_server_(ml).log`
   - `logs/network_simulator.log`
   - `logs/client.log`

## Expected Behavior

When everything is working:
1. ✅ All 4 status indicators turn green
2. ✅ Client UI shows "Connected"
3. ✅ After clicking "Start Comparison Demo":
   - Left canvas: Baseline video (delayed)
   - Right canvas: ML-predicted video (smooth)
   - Metrics updating in real-time
   - FPS counter showing 30-60 FPS

## Quick Video Test

To quickly test if video is flowing:

```bash
# Run this after starting all components
python -c "
import asyncio
import websockets

async def test():
    try:
        async with websockets.connect('ws://localhost:8004/stream') as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print('✅ Video received!', len(msg), 'bytes')
    except Exception as e:
        print('❌ Error:', e)

asyncio.run(test())
```

If you see "✅ Video received!", the pipeline is working!
