import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path.home() / ".hermes/profiles/lin/scripts/submit_lin_event.py"


class SubmitLinEventTests(unittest.TestCase):
    def test_posts_only_allowlisted_event_to_callback(self):
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received["path"] = self.path
                received["auth"] = self.headers.get("Authorization")
                received["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                response = b'{"status":"accepted"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def log_message(self, format, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        event = {
            "task_id": "task-1",
            "context_id": "context-1",
            "type": "memory.proposed",
            "payload": {"summary": "Anna told me something important."},
            "source_versions": {"persona_version": "p1", "memory_revision": "m1", "life_state_version": 1},
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as file:
            json.dump(event, file)
            event_path = file.name
        try:
            env = os.environ | {
                "LIN_RENDER_BASE_URL": f"http://127.0.0.1:{server.server_port}",
                "HERMES_CALLBACK_API_TOKEN": "callback-token",
            }
            result = subprocess.run([sys.executable, str(SCRIPT), event_path], env=env, text=True, capture_output=True)
        finally:
            server.shutdown()
            server.server_close()
            os.unlink(event_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(received["path"], "/internal/lin-events/v1")
        self.assertEqual(received["auth"], "Bearer callback-token")
        self.assertEqual(received["body"]["type"], "memory.proposed")
        self.assertEqual(received["body"]["source"], "hermes")
        self.assertEqual(received["body"]["schema_version"], "lin-event/v1")


if __name__ == "__main__":
    unittest.main()
