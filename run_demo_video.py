#!/usr/bin/env python3
"""
Demo Runner for Interplanetary Network - Video/ML Version
==========================================================
Starts all components for video demo with ML frame interpolation.
"""

import subprocess
import time
import sys
import os
import signal
import threading
from pathlib import Path

# Define the components and their configurations
components = [
    {
        "name": "Sender (Video)",
        "path": "sender/main_video.py",
        "port": 8001,
        "args": []  # No args = use webcam or test pattern
    },
    {
        "name": "Network Simulator",
        "path": "network_simulator/main.py",
        "port": 8002,
        "args": []
    },
    {
        "name": "Edge Server (ML)",
        "path": "edge_server/main_ml.py",
        "port": 8003,
        "args": []
    },
    {
        "name": "Client",
        "path": "client/main.py",
        "port": 8004,
        "args": []
    },
]

processes = []
running = True


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    print("\n\n🛑 Stopping all components...")
    running = False
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
    print("👋 Goodbye!")
    sys.exit(0)


def start_component(component, log_file=None):
    """Start a component in a new process."""
    print(f"🚀 Starting {component['name']} on port {component['port']}...")
    
    try:
        python_exe = sys.executable
        script_path = Path(component['path']).resolve()
        cwd = script_path.parent
        
        cmd = [python_exe, script_path.name] + component.get('args', [])
        
        if log_file:
            with open(log_file, 'w') as lf:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(cwd),
                    stdout=lf,
                    stderr=lf
                )
        else:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd)
            )
        
        return proc
    except Exception as e:
        print(f"❌ Failed to start {component['name']}: {e}")
        return None


def check_component_ready(name: str, port: int, timeout: float = 10.0) -> bool:
    """Check if a component is ready by testing its HTTP endpoint."""
    import urllib.request
    import urllib.error
    
    start_time = time.time()
    url = f"http://localhost:{port}/"
    
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionRefusedError):
            pass
        time.sleep(0.5)
    
    return False


def main():
    global running
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("Interplanetary Network - Video/ML Demo Runner")
    print("=" * 60)
    print()
    print("Components to start:")
    for comp in components:
        print(f"   - {comp['name']} (Port {comp['port']})")
    print()
    print("Press Ctrl+C to stop all components")
    print("=" * 60)
    print()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Start all components in order
    for i, comp in enumerate(components):
        log_file = logs_dir / f"{comp['name'].replace(' ', '_').lower()}.log"
        proc = start_component(comp, log_file=log_file)
        
        if proc:
            processes.append(proc)
            
            # Wait for component to be ready
            print(f"Waiting for {comp['name']} to be ready...", end=" ")
            if check_component_ready(comp['name'], comp['port']):
                print("OK")
            else:
                print("Started (check logs)")
            
            time.sleep(1)  # Stagger starts
        else:
            print(f"Failed to start {comp['name']}")
            print("\nAborting startup...")
            for proc in processes:
                proc.terminate()
            sys.exit(1)
    
    print()
    print("=" * 60)
    print("All components started successfully!")
    print()
    print("Open your browser at: http://localhost:8004")
    print()
    print("Component Status:")
    for comp in components:
        print(f"   - {comp['name']}: Running")
    print()
    print("Logs are being saved to: logs/")
    print()
    print("Next steps:")
    print("   1. Open http://localhost:8004 in your browser")
    print("   2. Click 'Start Comparison Demo'")
    print("   3. Select network delay from dropdown")
    print("   4. Observe video quality metrics")
    print("=" * 60)
    print()
    
    # Keep running until interrupted
    try:
        while running:
            time.sleep(1)
            
            # Check if any process died unexpectedly
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    comp_name = components[i]['name']
                    print(f"\n[WARN] {comp_name} stopped unexpectedly!")
                    print(f"   Check logs/{comp_name.replace(' ', '_').lower()}.log for details")
                    
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
