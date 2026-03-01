import json
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from .ipc_utils import get_base_communication_dir, get_active_session_dir


@dataclass
class VSCodeState:
    schema_version: int
    session_id: str
    timestamp: int
    active_file: Optional[str]
    language_id: Optional[str]
    workspace_folder: Optional[str]
    window_focused: bool
    compilation_database_path: Optional[str]


class VSCodeIPCClient:
    def __init__(self, app_name: str = "cindexer"):
        self.app_name = app_name
        self.base_dir = get_base_communication_dir(app_name)
        self._cached_session_dir: Optional[Path] = None

    def get_current_state(self) -> VSCodeState:
        """
        Reads and returns the current VS Code state.
        On-demand querying: re-reads the JSON file from the active session.
        """
        try:
            session_dir = get_active_session_dir(self.base_dir)
            self._cached_session_dir = session_dir
        except FileNotFoundError:
            # If we had a cached session dir, try to reuse it as fallback?
            # No, if active_session is missing, we should probably fail or wait.
            raise

        state_file = session_dir / "vscode_state.json"
        if not state_file.exists():
            raise FileNotFoundError(f"State file missing: {state_file}")

        data = json.loads(state_file.read_text())

        return VSCodeState(
            schema_version=data.get("schema_version"),
            session_id=data.get("session_id"),
            timestamp=data.get("timestamp"),
            active_file=data.get("active_file"),
            language_id=data.get("language_id"),
            workspace_folder=data.get("workspace_folder"),
            window_focused=(
                data.get("window_focused")
                if data.get("window_focused") is not None
                else False
            ),
            compilation_database_path=data.get("compilation_database_path"),
        )

    def is_alive(self) -> bool:
        """Checks if the VS Code session is still considered active based on state file presence."""
        try:
            session_dir = get_active_session_dir(self.base_dir)
            return (session_dir / "vscode_state.json").exists()
        except FileNotFoundError:
            return False

    def send_request(self, request_type: str, data: Optional[dict] = None) -> str:
        """
        Writes a request to request.json in the active session directory.
        Returns a unique request ID (UUID).
        """
        import uuid

        request_id = str(uuid.uuid4())
        session_dir = get_active_session_dir(self.base_dir)
        request_path = session_dir / "request.json"

        request = {
            "request_id": request_id,
            "type": request_type,
            "data": data or {},
            "timestamp": int(__import__("time").time() * 1000),
        }

        # Atomic write
        tmp_path = f"{request_path}.tmp"
        with open(tmp_path, "w") as f:
            json.dump(request, f, separators=(",", ":"))
            f.write("\n")

        import os

        os.replace(tmp_path, str(request_path))

        return request_id
