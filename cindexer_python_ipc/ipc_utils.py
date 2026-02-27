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
    in the base directory.
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            pointer_file = base_dir / "active_session"
            if not pointer_file.exists():
                raise FileNotFoundError(f"No active session found at {pointer_file}")
            
            session_id = pointer_file.read_text().strip()
            session_dir = base_dir / "sessions" / session_id
            
            if not session_dir.exists():
                raise FileNotFoundError(f"Session directory {session_dir} does not exist")
            
            return session_dir
        except FileNotFoundError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    if last_error:
        raise last_error
    raise FileNotFoundError(f"Failed to resolve active session after {max_retries} attempts")
