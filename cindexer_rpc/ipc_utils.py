import os
import time
from pathlib import Path
from tempfile import gettempdir

def get_base_communication_dir(name: str) -> Path:
    """
    Returns the base directory used for communication, scoped by user ID on POSIX.
    Matches the logic in the VS Code extension for alignment.
    """
    suffix = ""
    # On POSIX, we suffix with the UID to avoid cross-user collisions in /tmp
    if hasattr(os, "getuid"):
        suffix = f"-{os.getuid()}"
    
    return Path(gettempdir()) / f"{name}{suffix}"

def get_active_session_dir(base_dir: Path, max_retries: int = 3, retry_delay: float = 0.1) -> Path:
    """
    Resolves the active session directory by reading the 'active_session' pointer
    in the base directory. Falls back to the most recently modified session if the 
    pointer is missing or invalid.
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            pointer_file = base_dir / "active_session"
            if pointer_file.exists():
                session_id = pointer_file.read_text().strip()
                if session_id:
                    session_dir = base_dir / "sessions" / session_id
                    if session_dir.exists():
                        return session_dir
            
            # Fallback: find any valid session
            sessions_root = base_dir / "sessions"
            if sessions_root.exists():
                valid_sessions = []
                for d in sessions_root.iterdir():
                    if d.is_dir() and (d / "vscode_state.json").exists():
                        mtime = (d / "vscode_state.json").stat().st_mtime
                        valid_sessions.append((mtime, d))
                
                if valid_sessions:
                    valid_sessions.sort(key=lambda x: x[0], reverse=True)
                    return valid_sessions[0][1]

            raise FileNotFoundError(f"No active or valid session found at {base_dir}")

        except FileNotFoundError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    if last_error:
        raise last_error
    raise FileNotFoundError(f"Failed to resolve session after {max_retries} attempts")
