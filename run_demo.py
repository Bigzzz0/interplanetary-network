# -*- coding: utf-8 -*-
"""
Demo Runner for Interplanetary Network - Video/ML Version
==========================================================
Starts all components with Web UI for video selection.
"""

import subprocess
import time
import sys
import os
import signal
import re
import json
import threading
import socket
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

# Define the components and their ports
components = [
    {"name": "Sender", "path": "sender/main_video.py", "port": 8001},
    {"name": "Network Simulator", "path": "network_simulator/main.py", "port": 8002},
    {"name": "Edge Server", "path": "edge_server/main_ml.py", "port": 8003},
    {"name": "Client", "path": "client/main.py", "port": 8004},
]

processes = []
running = True
selected_video = None
system_started = False


# ============================================================================
# Web UI Server
# ============================================================================

class DemoHandler(BaseHTTPRequestHandler):
    """HTTP Handler for the demo web UI."""
    
    def log_message(self, format, *args):
        pass  # Suppress logging
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/":
            self.send_video_selector_page()
        elif parsed.path == "/api/videos":
            self.send_videos_json()
        elif parsed.path == "/api/status":
            self.send_status_json()
        elif parsed.path == "/api/started":
            self.send_json({"started": system_started, "video": selected_video})
        else:
            self.send_error(404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        if parsed.path == "/api/select":
            self.handle_select_video(body)
        elif parsed.path == "/api/start":
            self.handle_start_system()
        elif parsed.path == "/api/stop":
            self.handle_stop_system()
        else:
            self.send_error(404)
    
    def send_video_selector_page(self):
        """Send the main video selector HTML page."""
        global selected_video
        
        videos = get_available_videos()
        current = get_current_video()
        
        # Escape for JSON
        current_json = json.dumps(current if current else "")
        
        html = self.get_html_template(videos, current_json)
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def get_html_template(self, videos, current_json):
        """Generate HTML template."""
        current_video = get_current_video()
        video_items_html = ""
        
        for v in videos:
            active_class = "active" if v["name"] == current_video else ""
            
            if v["name"] == current_video:
                btn_html = '<button class="btn btn-active">✓ Selected</button>'
            else:
                # Escape single quotes for JavaScript
                safe_name = v["name"].replace("'", "\\'")
                btn_html = f'<button class="btn btn-select" onclick="selectVideo(\'{safe_name}\')">Select</button>'
            
            video_items_html += f"""
            <div class="video-item {active_class}">
                <div class="video-info">
                    <div class="video-name">🎬 {v['name']}</div>
                    <div class="video-size">{v['size_mb']} MB</div>
                </div>
                <div class="video-actions">
                    {btn_html}
                </div>
            </div>"""
        
        if not videos:
            video_items_html = '<p style="text-align:center;color:#a0a0a0;padding:40px;">No videos found. Add .mp4, .avi, .mov files to dataset/</p>'
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Interplanetary Network Demo</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 40px 0 30px;
            border-bottom: 2px solid #e94560;
            margin-bottom: 30px;
        }}
        h1 {{ font-size: 2.8em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }}
        .subtitle {{ color: #a0a0a0; font-size: 1.2em; }}
        .panel {{
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        .panel h2 {{ margin-bottom: 20px; font-size: 1.4em; }}
        .status-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .status-item {{
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .status-item .name {{ font-size: 0.95em; color: #a0a0a0; margin-bottom: 10px; }}
        .status-item .indicator {{
            display: inline-block;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .status-item .indicator.running {{
            background: #00ff88;
            box-shadow: 0 0 12px #00ff88;
        }}
        .status-item .indicator.stopped {{
            background: #ff4757;
            box-shadow: 0 0 12px #ff4757;
        }}
        .video-list {{ display: grid; gap: 12px; max-height: 400px; overflow-y: auto; }}
        .video-item {{
            background: rgba(0,0,0,0.3);
            padding: 18px 20px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 2px solid transparent;
        }}
        .video-item:hover {{ background: rgba(0,0,0,0.4); transform: translateX(5px); }}
        .video-item.active {{ border-color: #00ff88; background: rgba(0, 255, 136, 0.1); }}
        .video-info {{ flex: 1; }}
        .video-name {{ font-size: 1.1em; font-weight: 600; margin-bottom: 5px; }}
        .video-size {{ color: #a0a0a0; font-size: 0.9em; }}
        .btn {{
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
        }}
        .btn-select {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
        .btn-select:hover {{ transform: scale(1.05); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }}
        .btn-active {{ background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%); color: #1a1a2e; cursor: default; }}
        .btn-refresh {{ background: rgba(255,255,255,0.2); color: white; font-size: 0.9em; padding: 8px 16px; }}
        .actions {{ display: flex; gap: 15px; flex-wrap: wrap; margin-top: 25px; }}
        .btn-large {{ padding: 18px 36px; font-size: 1.15em; flex: 1; min-width: 200px; }}
        .btn-start {{ background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%); color: #1a1a2e; }}
        .btn-start:hover:not(:disabled) {{ transform: scale(1.05); box-shadow: 0 5px 25px rgba(0, 255, 136, 0.5); }}
        .btn-stop {{ background: linear-gradient(135deg, #ff4757 0%, #ff3838 100%); color: white; }}
        .btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .message {{ padding: 18px 24px; border-radius: 12px; margin-bottom: 20px; display: none; }}
        .message.success {{ background: rgba(0, 255, 136, 0.2); border: 2px solid #00ff88; display: block; }}
        .message.error {{ background: rgba(255, 71, 87, 0.2); border: 2px solid #ff4757; display: block; }}
        .message.info {{ background: rgba(102, 126, 234, 0.2); border: 2px solid #667eea; display: block; }}
        .running-panel {{ display: none; background: rgba(0, 255, 136, 0.1); border: 2px solid #00ff88; }}
        .running-panel.show {{ display: block; }}
        .link {{ color: #00ff88; text-decoration: none; font-weight: 600; }}
        .link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 Interplanetary Network</h1>
            <p class="subtitle">Mars-to-Earth Video Streaming with ML Frame Interpolation</p>
        </header>
        
        <div id="message" class="message"></div>
        
        <div class="panel" id="runningPanel" style="display: none;">
            <h2>✅ System Running!</h2>
            <p style="margin-bottom: 15px;">
                🌍 <strong>Client UI:</strong> 
                <a href="http://localhost:8004" class="link" target="_blank">http://localhost:8004</a>
            </p>
            <p style="margin-bottom: 15px;">
                📹 <strong>Current Video:</strong> <span id="runningVideo">-</span>
            </p>
            <button class="btn btn-stop" onclick="stopSystem()">⏹️ Stop System</button>
        </div>
        
        <div class="panel" id="selectionPanel">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2>📹 Select Video</h2>
                <button class="btn btn-refresh" onclick="location.reload()">🔄 Refresh</button>
            </div>
            <div class="video-list" id="videoList">
                {video_items_html}
            </div>
            
            <div class="actions">
                <button class="btn btn-large btn-start" id="btnStart" onclick="startSystem()" {'disabled' if not get_current_video() else ''}>
                    🚀 Start System
                </button>
            </div>
            <p style="text-align: center; color: #a0a0a0; margin-top: 15px; font-size: 0.9em;">
                💡 Tip: Add videos to <code>dataset/</code> folder, then click Refresh
            </p>
        </div>
        
        <div class="panel" id="statusPanel">
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
    </div>
    
    <script>
        let currentVideo = {current_json};
        let systemStarted = false;
        
        async function selectVideo(name) {{
            const msg = document.getElementById('message');
            
            try {{
                const resp = await fetch('/api/select', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ video: name }})
                }});
                const result = await resp.json();
                
                if (result.success) {{
                    currentVideo = name;
                    msg.className = 'message success';
                    msg.textContent = '✓ Selected: ' + name + '. Click "Start System" to begin.';
                    document.getElementById('btnStart').disabled = false;
                    setTimeout(() => location.reload(), 500);
                }} else {{
                    msg.className = 'message error';
                    msg.textContent = '✗ Error: ' + result.error;
                }}
            }} catch (e) {{
                msg.className = 'message error';
                msg.textContent = '✗ Error: ' + e.message;
            }}
        }}
        
        async function startSystem() {{
            const msg = document.getElementById('message');
            msg.className = 'message info';
            msg.textContent = 'Starting system...';
            
            try {{
                const resp = await fetch('/api/start', {{ method: 'POST' }});
                const result = await resp.json();
                
                if (result.success) {{
                    systemStarted = true;
                    document.getElementById('selectionPanel').style.display = 'none';
                    document.getElementById('runningPanel').classList.add('show');
                    document.getElementById('runningVideo').textContent = currentVideo || 'Test Pattern';
                    msg.className = 'message success';
                    msg.textContent = '✓ System started! Opening Client UI...';
                    
                    setTimeout(() => {{
                        window.open('http://localhost:8004', '_blank');
                    }}, 2000);
                }} else {{
                    msg.className = 'message error';
                    msg.textContent = '✗ Error: ' + result.error;
                }}
            }} catch (e) {{
                msg.className = 'message error';
                msg.textContent = '✗ Error: ' + e.message;
            }}
        }}
        
        async function stopSystem() {{
            try {{
                await fetch('/api/stop', {{ method: 'POST' }});
                location.reload();
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}
        
        async function checkStatus() {{
            try {{
                const resp = await fetch('/api/status');
                const status = await resp.json();
                
                updateIndicator('sender', status.sender?.running);
                updateIndicator('network', status.network_simulator?.running);
                updateIndicator('edge', status.edge_server?.running);
                updateIndicator('client', status.client?.running);
            }} catch (e) {{ }}
        }}
        
        function updateIndicator(id, running) {{
            const ind = document.getElementById(id + '-status');
            const txt = document.getElementById(id + '-text');
            ind.className = 'indicator ' + (running ? 'running' : 'stopped');
            txt.textContent = running ? 'Running' : 'Stopped';
        }}
        
        checkStatus();
        setInterval(checkStatus, 3000);
    </script>
</body>
</html>"""
    
    def send_videos_json(self):
        """Send list of available videos."""
        videos = get_available_videos()
        self.send_json(videos)
    
    def send_status_json(self):
        """Send system status."""
        status = get_system_status()
        self.send_json(status)
    
    def handle_select_video(self, body):
        """Handle video selection."""
        try:
            data = json.loads(body)
            video_name = data.get("video")
            
            if not video_name:
                self.send_json({"success": False, "error": "No video specified"})
                return
            
            result = set_current_video(video_name)
            self.send_json(result)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})
    
    def handle_start_system(self):
        """Handle system start request."""
        global system_started, selected_video
        
        if system_started:
            self.send_json({"success": False, "error": "System already running"})
            return
        
        # Start all components in background
        threading.Thread(target=start_all_components, daemon=True).start()
        
        time.sleep(0.5)
        system_started = True
        self.send_json({"success": True})
    
    def handle_stop_system(self):
        """Handle system stop request."""
        global system_started
        stop_all_components()
        system_started = False
        self.send_json({"success": True})
    
    def send_json(self, data):
        """Send JSON response."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))


# ============================================================================
# Helper Functions
# ============================================================================

def get_available_videos():
    """Get list of available video files."""
    dataset_dir = Path(__file__).parent / "dataset"
    video_extensions = ["*.mp4", "*.avi", "*.mov", "*.mkv", "*.webm", "*.flv", "*.wmv"]
    
    videos = []
    for ext in video_extensions:
        videos.extend(dataset_dir.glob(ext))
        videos.extend(dataset_dir.glob(ext.upper()))
    
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
    sender_config = Path(__file__).parent / "sender" / "main_video.py"
    
    if not sender_config.exists():
        return None
    
    try:
        with open(sender_config, "r", encoding="utf-8") as f:
            content = f.read()
        
        match = re.search(r'VIDEO_FILE = DATASET_DIR / "([^"]*)"', content)
        if match:
            video_name = match.group(1)
            # Verify file exists
            if (Path(__file__).parent / "dataset" / video_name).exists():
                return video_name
    except Exception:
        pass
    
    return None


def set_current_video(video_name):
    """Update sender config to use selected video."""
    sender_config = Path(__file__).parent / "sender" / "main_video.py"
    
    if not sender_config.exists():
        return {"success": False, "error": "Sender config not found"}
    
    # Verify video exists
    video_path = Path(__file__).parent / "dataset" / video_name
    if not video_path.exists():
        return {"success": False, "error": f"Video not found: {video_name}"}
    
    try:
        with open(sender_config, "r", encoding="utf-8") as f:
            content = f.read()
        
        pattern = r'VIDEO_FILE = DATASET_DIR / "[^"]*"'
        replacement = f'VIDEO_FILE = DATASET_DIR / "{video_name}"'
        
        new_content = re.sub(pattern, replacement, content)
        
        with open(sender_config, "w", encoding="utf-8") as f:
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


def kill_port(port):
    """Kill any process currently listening on the given port (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-aon"],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                parts = line.split()
                pid = parts[-1]
                subprocess.run(["taskkill", "/PID", pid, "/F"],
                               capture_output=True)
                print(f"   [+] Freed port {port} (killed PID {pid})")
                time.sleep(0.5)
    except Exception:
        pass


def start_component(component):
    """Start a component in a new process."""
    print(f"[*] Starting {component['name']} on port {component['port']}...")
    try:
        python_exe = sys.executable
        script_path = os.path.abspath(component['path'])
        cwd = os.path.dirname(script_path)
        script_name = os.path.basename(script_path)

        process = subprocess.Popen(
            [python_exe, script_name],
            cwd=cwd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        return process
    except Exception as e:
        print(f"[!] Failed to start {component['name']}: {e}")
        return None


def start_all_components():
    """Start all system components."""
    global processes
    
    # Free ports
    for comp in components:
        kill_port(comp["port"])
    
    # Start components
    for comp in components:
        proc = start_component(comp)
        if proc:
            processes.append(proc)
        time.sleep(0.5)
    
    print("\n[+] All components started!")


def stop_all_components():
    """Stop all running components."""
    global processes
    
    print("\n[-] Stopping all components...")
    for proc in processes:
        try:
            proc.terminate()
        except Exception:
            pass
    
    processes = []
    print("Goodbye!")


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    print("\n\n🛑 Stopping...")
    running = False
    stop_all_components()
    sys.exit(0)


def is_port_available(port):
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except Exception:
            return False


def find_available_port(start_port=8080):
    """Find an available port starting from start_port."""
    port = start_port
    while port < start_port + 100:
        if is_port_available(port):
            return port
        port += 1
    return start_port


# ============================================================================
# Main
# ============================================================================

def main():
    global running
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Find available port for web UI
    web_port = find_available_port(8080)
    
    print("=" * 70)
    print("🚀 Interplanetary Network - Demo Runner with Web UI")
    print("=" * 70)
    print()
    print(f"🌐 Web UI: http://localhost:{web_port}")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    # Start web server
    server = HTTPServer(('localhost', web_port), DemoHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    # Open browser after short delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{web_port}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Keep running
    try:
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)
    
    server.shutdown()


if __name__ == "__main__":
    main()
