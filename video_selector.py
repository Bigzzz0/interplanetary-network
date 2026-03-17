#!/usr/bin/env python3
"""
Video Selector Web UI
=====================
A simple web interface to select videos from the dataset folder.
"""

import os
import re
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Video Selector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to dataset folder
DATASET_DIR = Path(__file__).parent / "dataset"
SENDER_CONFIG = Path(__file__).parent / "sender" / "main_video.py"

# Path to logs directory
LOGS_DIR = Path(__file__).parent / "logs"


def get_available_videos():
    """Get list of available video files."""
    video_extensions = ["*.mp4", "*.avi", "*.mov", "*.mkv", "*.webm", "*.flv", "*.wmv"]
    videos = []
    
    for ext in video_extensions:
        videos.extend(DATASET_DIR.glob(ext))
        videos.extend(DATASET_DIR.glob(ext.upper()))
    
    # Remove duplicates and sort
    videos = sorted(set(videos), key=lambda x: x.name.lower())
    
    result = []
    for video in videos:
        size_mb = video.stat().st_size / (1024 * 1024)
        result.append({
            "name": video.name,
            "path": str(video),
            "size_mb": round(size_mb, 1)
        })
    
    return result


def get_current_video():
    """Get currently selected video from sender config."""
    if not SENDER_CONFIG.exists():
        return None
    
    try:
        with open(SENDER_CONFIG, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Pattern: VIDEO_FILE = DATASET_DIR / "filename.mp4"
        match = re.search(r'VIDEO_FILE = DATASET_DIR / "([^"]*)"', content)
        if match:
            return match.group(1)
    except Exception:
        pass
    
    return None


def set_current_video(video_name):
    """Update sender config to use selected video."""
    if not SENDER_CONFIG.exists():
        return {"success": False, "error": "Sender config not found"}
    
    try:
        with open(SENDER_CONFIG, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Pattern: VIDEO_FILE = DATASET_DIR / "..."
        pattern = r'VIDEO_FILE = DATASET_DIR / "[^"]*"'
        replacement = f'VIDEO_FILE = DATASET_DIR / "{video_name}"'
        
        new_content = re.sub(pattern, replacement, content)
        
        with open(SENDER_CONFIG, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return {"success": True, "video": video_name}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_system_status():
    """Check if system components are running."""
    import urllib.request
    import urllib.error
    
    components = {
        "sender": {"port": 8001, "running": False},
        "network_simulator": {"port": 8002, "running": False},
        "edge_server": {"port": 8003, "running": False},
        "client": {"port": 8004, "running": False}
    }
    
    for name, info in components.items():
        try:
            with urllib.request.urlopen(f"http://localhost:{info['port']}/", timeout=1) as resp:
                if resp.status == 200:
                    components[name]["running"] = True
        except Exception:
            pass
    
    return components


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main video selector page."""
    videos = get_available_videos()
    current_video = get_current_video()
    
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎬 Video Selector - Interplanetary Network</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid #e94560;
            margin-bottom: 30px;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }
        
        .subtitle {
            color: #a0a0a0;
            font-size: 1.1em;
        }
        
        .status-panel {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }
        
        .status-panel h2 {
            margin-bottom: 15px;
            font-size: 1.3em;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }
        
        .status-item {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        
        .status-item .name {
            font-size: 0.9em;
            color: #a0a0a0;
            margin-bottom: 8px;
        }
        
        .status-item .indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-item .indicator.running {
            background: #00ff88;
            box-shadow: 0 0 10px #00ff88;
        }
        
        .status-item .indicator.stopped {
            background: #ff4757;
            box-shadow: 0 0 10px #ff4757;
        }
        
        .video-panel {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        
        .video-panel h2 {
            margin-bottom: 20px;
            font-size: 1.3em;
        }
        
        .video-list {
            display: grid;
            gap: 15px;
        }
        
        .video-item {
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }
        
        .video-item:hover {
            background: rgba(0,0,0,0.4);
            transform: translateX(5px);
        }
        
        .video-item.active {
            border-color: #00ff88;
            background: rgba(0, 255, 136, 0.1);
        }
        
        .video-info {
            flex: 1;
        }
        
        .video-name {
            font-size: 1.1em;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .video-size {
            color: #a0a0a0;
            font-size: 0.9em;
        }
        
        .video-actions {
            display: flex;
            gap: 10px;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.95em;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .btn-select {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-select:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-active {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #1a1a2e;
            cursor: default;
        }
        
        .btn-refresh {
            background: rgba(255,255,255,0.2);
            color: white;
            margin-left: 10px;
        }
        
        .btn-refresh:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .actions-panel {
            margin-top: 30px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .btn-large {
            padding: 15px 30px;
            font-size: 1.1em;
        }
        
        .btn-start {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #1a1a2e;
        }
        
        .btn-start:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 20px rgba(0, 255, 136, 0.4);
        }
        
        .btn-stop {
            background: linear-gradient(135deg, #ff4757 0%, #ff3838 100%);
            color: white;
        }
        
        .btn-stop:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 20px rgba(255, 71, 87, 0.4);
        }
        
        .message {
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: none;
        }
        
        .message.success {
            background: rgba(0, 255, 136, 0.2);
            border: 2px solid #00ff88;
            display: block;
        }
        
        .message.error {
            background: rgba(255, 71, 87, 0.2);
            border: 2px solid #ff4757;
            display: block;
        }
        
        .refresh-hint {
            text-align: center;
            color: #a0a0a0;
            margin-top: 20px;
            font-size: 0.9em;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading {
            animation: pulse 1s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎬 Video Selector</h1>
            <p class="subtitle">Interplanetary Network - Mars Rover Video Stream</p>
        </header>
        
        <div id="message" class="message"></div>
        
        <div class="status-panel">
            <h2>📊 System Status</h2>
            <div class="status-grid" id="statusGrid">
                <div class="status-item">
                    <div class="name">📡 Sender (Mars)</div>
                    <div><span class="indicator stopped" id="sender-status"></span><span id="sender-text">Checking...</span></div>
                </div>
                <div class="status-item">
                    <div class="name">🌌 Network Simulator</div>
                    <div><span class="indicator stopped" id="network-status"></span><span id="network-text">Checking...</span></div>
                </div>
                <div class="status-item">
                    <div class="name">🛰️ Edge Server (Lagrange)</div>
                    <div><span class="indicator stopped" id="edge-status"></span><span id="edge-text">Checking...</span></div>
                </div>
                <div class="status-item">
                    <div class="name">🌍 Client (Earth)</div>
                    <div><span class="indicator stopped" id="client-status"></span><span id="client-text">Checking...</span></div>
                </div>
            </div>
        </div>
        
        <div class="video-panel">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h2>📹 Available Videos</h2>
                <button class="btn btn-refresh" onclick="loadVideos()">🔄 Refresh</button>
            </div>
            <div class="video-list" id="videoList">
                <!-- Videos will be loaded here -->
            </div>
        </div>
        
        <div class="actions-panel">
            <button class="btn btn-large btn-start" onclick="startSystem()">🚀 Start System</button>
            <button class="btn btn-large btn-stop" onclick="stopSystem()">⏹️ Stop System</button>
        </div>
        
        <p class="refresh-hint">💡 Tip: Add new videos to the <code>dataset/</code> folder and click Refresh</p>
    </div>
    
    <script>
        let currentVideo = """ + json.dumps(current_video) + """;
        
        async function loadVideos() {
            const response = await fetch('/api/videos');
            const videos = await response.json();
            
            const videoList = document.getElementById('videoList');
            videoList.innerHTML = '';
            
            if (videos.length === 0) {
                videoList.innerHTML = '<p style="text-align: center; color: #a0a0a0; padding: 40px;">No videos found. Add .mp4, .avi, .mov files to the dataset/ folder.</p>';
                return;
            }
            
            videos.forEach(video => {
                const isActive = video.name === currentVideo;
                const item = document.createElement('div');
                item.className = 'video-item' + (isActive ? ' active' : '');
                item.innerHTML = `
                    <div class="video-info">
                        <div class="video-name">🎬 ${video.name}</div>
                        <div class="video-size">${video.size_mb} MB</div>
                    </div>
                    <div class="video-actions">
                        ${isActive 
                            ? '<button class="btn btn-active">✓ Selected</button>'
                            : `<button class="btn btn-select" onclick="selectVideo('${video.name}')">Select</button>`
                        }
                    </div>
                `;
                videoList.appendChild(item);
            });
        }
        
        async function selectVideo(videoName) {
            const messageEl = document.getElementById('message');
            messageEl.className = 'message';
            messageEl.textContent = '';
            
            const response = await fetch('/api/video/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video: videoName })
            });
            
            const result = await response.json();
            
            if (result.success) {
                currentVideo = videoName;
                messageEl.className = 'message success';
                messageEl.textContent = `✓ Selected: ${videoName}. Restart the system to apply changes.`;
                loadVideos();
            } else {
                messageEl.className = 'message error';
                messageEl.textContent = `✗ Error: ${result.error}`;
            }
        }
        
        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const status = await response.json();
                
                updateStatusIndicator('sender', status.sender?.running);
                updateStatusIndicator('network', status.network_simulator?.running);
                updateStatusIndicator('edge', status.edge_server?.running);
                updateStatusIndicator('client', status.client?.running);
            } catch (error) {
                console.error('Status check failed:', error);
            }
        }
        
        function updateStatusIndicator(component, isRunning) {
            const indicator = document.getElementById(`${component}-status`);
            const text = document.getElementById(`${component}-text`);
            
            indicator.className = 'indicator ' + (isRunning ? 'running' : 'stopped');
            text.textContent = isRunning ? 'Running' : 'Stopped';
        }
        
        async function startSystem() {
            const messageEl = document.getElementById('message');
            messageEl.className = 'message success';
            messageEl.textContent = 'Starting system... Check terminal for progress.';
            
            // Try to start via API if available, otherwise show instructions
            try {
                const response = await fetch('/api/start', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    messageEl.textContent = '✓ System starting! Open http://localhost:8004 in your browser.';
                } else {
                    messageEl.textContent = '⚠️ Run "python run_demo.py" in terminal to start the system.';
                }
            } catch {
                messageEl.textContent = '⚠️ Run "python run_demo.py" in terminal to start the system.';
            }
            
            setTimeout(checkStatus, 3000);
        }
        
        async function stopSystem() {
            const messageEl = document.getElementById('message');
            
            try {
                const response = await fetch('/api/stop', { method: 'POST' });
                const result = await response.json();
                if (result.success) {
                    messageEl.className = 'message success';
                    messageEl.textContent = '✓ System stopped.';
                }
            } catch {
                messageEl.className = 'message';
                messageEl.textContent = '⚠️ Press Ctrl+C in terminal to stop the system.';
            }
            
            setTimeout(checkStatus, 2000);
        }
        
        // Load videos and status on page load
        loadVideos();
        checkStatus();
        
        // Auto-refresh status every 3 seconds
        setInterval(checkStatus, 3000);
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/api/videos")
async def api_get_videos():
    """Get list of available videos."""
    return JSONResponse(get_available_videos())


@app.get("/api/video/current")
async def api_get_current_video():
    """Get currently selected video."""
    current = get_current_video()
    return JSONResponse({"current_video": current})


@app.post("/api/video/select")
async def api_select_video(request: Request):
    """Select a video to use."""
    data = await request.json()
    video_name = data.get("video")
    
    if not video_name:
        return JSONResponse({"success": False, "error": "No video specified"})
    
    # Verify video exists
    video_path = DATASET_DIR / video_name
    if not video_path.exists():
        return JSONResponse({"success": False, "error": "Video not found"})
    
    result = set_current_video(video_name)
    return JSONResponse(result)


@app.get("/api/status")
async def api_get_status():
    """Get system status."""
    return JSONResponse(get_system_status())


@app.post("/api/start")
async def api_start_system():
    """Start the demo system."""
    try:
        # Start run_demo.py in background
        script_path = Path(__file__).parent / "run_demo.py"
        subprocess.Popen([sys.executable, str(script_path)], 
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


@app.post("/api/stop")
async def api_stop_system():
    """Stop all running components."""
    try:
        import urllib.request
        # Send stop signal to each component
        for port in [8001, 8002, 8003, 8004]:
            try:
                urllib.request.urlopen(f"http://localhost:{port}/shutdown", timeout=1)
            except Exception:
                pass
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


if __name__ == "__main__":
    import sys
    import subprocess
    
    print("=" * 60)
    print("🎬 Video Selector Web UI")
    print("=" * 60)
    print()
    print("Open in browser: http://localhost:8080")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")
