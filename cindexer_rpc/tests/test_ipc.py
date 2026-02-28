import unittest
import json
import shutil
import tempfile
import os
from pathlib import Path
from ..client import VSCodeIPCClient, VSCodeState
from ..ipc_utils import get_base_communication_dir


class TestIPC(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.app_name = "test_cindexer"
        # Monkeypatch get_base_communication_dir or just pass it to client
        self.client = VSCodeIPCClient(app_name=self.app_name)
        # We need to ensure the client uses our test_dir
        # Let's override the base_dir property
        self.client.base_dir = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_state_query(self):
        # 1. Setup mock session
        session_id = "test-session-123"
        session_dir = Path(self.test_dir) / "sessions" / session_id
        session_dir.mkdir(parents=True)

        state_file = session_dir / "vscode_state.json"
        state_data = {
            "schema_version": 1,
            "session_id": session_id,
            "timestamp": 123456789,
            "active_file": "/path/to/test.cpp",
            "language_id": "cpp",
            "workspace_folder": "/path/to/project",
            "window_focused": True,
            "compilation_database_path": "/path/to/project/compile_commands.json",
        }
        state_file.write_text(json.dumps(state_data))

        # 2. Setup active session pointer
        pointer_file = Path(self.test_dir) / "active_session"
        pointer_file.write_text(session_id)

        # 3. Query state via client
        state = self.client.get_current_state()

        self.assertEqual(state.session_id, session_id)
        self.assertEqual(state.active_file, "/path/to/test.cpp")
        self.assertEqual(state.language_id, "cpp")
        self.assertTrue(state.window_focused)

    def test_missing_session(self):
        with self.assertRaises(FileNotFoundError):
            self.client.get_current_state()

    def test_send_request(self):
        # 1. Setup mock session
        session_id = "test-session-rpc"
        session_dir = Path(self.test_dir) / "sessions" / session_id
        session_dir.mkdir(parents=True)
        pointer_file = Path(self.test_dir) / "active_session"
        pointer_file.write_text(session_id)

        # 2. Send request
        req_id = self.client.send_request("get_state", {"foo": "bar"})

        # 3. Verify file exists and has correct content
        request_file = session_dir / "python_request.json"
        self.assertTrue(request_file.exists())

        req_data = json.loads(request_file.read_text())
        self.assertEqual(req_data["request_id"], req_id)
        self.assertEqual(req_data["type"], "get_state")
        self.assertEqual(req_data["data"]["foo"], "bar")


if __name__ == "__main__":
    unittest.main()
