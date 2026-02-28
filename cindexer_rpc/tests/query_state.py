import sys
import os
import time

# Add the project root to sys.path to allow importing cindexer_rpc
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from cindexer_rpc.client import VSCodeIPCClient
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def main():
    client = VSCodeIPCClient()
    
    print(f"Connecting to CIndexer IPC at: {client.base_dir}")
    
    try:
        # 1. Query current state
        state = client.get_current_state()
        print("\n--- Current VS Code State ---")
        print(f"Session ID: {state.session_id}")
        print(f"Active File: {state.active_file}")
        print(f"Language: {state.language_id}")
        print(f"Workspace: {state.workspace_folder}")
        print(f"Compile DB: {state.compilation_database_path}")
        print(f"Focused: {state.window_focused}")
        
        # 2. Send a get_state request
        print("\nSending 'get_state' request to VS Code...")
        req_id = client.send_request("get_state")
        print(f"Request sent (ID: {req_id})")
        
        # 3. Wait a bit and query again
        time.sleep(1)
        new_state = client.get_current_state()
        print(f"Updated timestamp: {new_state.timestamp}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure VS Code is running with the CIndexer extension activated.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
