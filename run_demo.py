
import subprocess
import time
import sys
import os
import signal

# Define the components and their ports
components = [
    {"name": "Sender", "path": "sender/main.py", "port": 8001},
    {"name": "Network Simulator", "path": "network_simulator/main.py", "port": 8002},
    {"name": "Edge Server", "path": "edge_server/main.py", "port": 8003},
    {"name": "Client", "path": "client/main.py", "port": 8004},
]

processes = []

def start_component(component):
    """Start a component in a new process."""
    print(f"🚀 Starting {component['name']} on port {component['port']}...")
    try:
        # Use python from the current environment
        python_exe = sys.executable
        
        # Get absolute path to the script
        script_path = os.path.abspath(component['path'])
        
        # Determine working directory (parent of the script)
        cwd = os.path.dirname(script_path)
        
        # Start the process - run main.py directly since we're inside the folder
        # or better: run python sender/main.py from root?
        # Let's run from the component directory to avoid import issues 
        # (imports usually assume they are run as modules or scripts inside the folder)
        # But wait, looking at the code imports: `from sender import ...`? No, they are `main.py`
        # and import regular libs.
        
        # Correct approach: Run from project root, but use module path?
        # Or change CWD to component dir. Let's change CWD.
        
        process = subprocess.Popen(
            [python_exe, "main.py"],
            cwd=cwd,
            # stdout=subprocess.PIPE, 
            # stderr=subprocess.PIPE,
            # Check if we want to see output in main console or silence it?
            # Seeing output is good for debugging, but might be messy.
            # Let's redirect to separate log files or just let it flow if user wants.
            # For simplicity in this demo script: let it inherit stdout/stderr
            # creationflags=subprocess.CREATE_NEW_CONSOLE  # Windows-specific: opens new window
        )
        return process
    except Exception as e:
        print(f"❌ Failed to start {component['name']}: {e}")
        return None

def main():
    print("=" * 50)
    print("🌍 Interplanetary Network Demo Runner")
    print("=" * 50)
    
    # Start all components
    for comp in components:
        proc = start_component(comp)
        if proc:
            processes.append(proc)
        time.sleep(1) # Wait a bit between starts
        
    print("\n✅ All components started!")
    print("👉 Open your browser at: http://localhost:8004")
    print("Press Ctrl+C to stop all components.\n")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
            # Check if processes are alive
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    print(f"⚠️  {components[i]['name']} stopped unexpectedly!")
                    # Optional: restart logic
                    
    except KeyboardInterrupt:
        print("\n🛑 Stopping all components...")
        for proc in processes:
            proc.terminate()
            # Windows might typically need kill, but try terminate first
        print("Goodbye!")

if __name__ == "__main__":
    main()
