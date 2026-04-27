from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from engine.clarification_runner import run, reset_state


HOST = "127.0.0.1"
PORT = 8080
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _json_response(
    handler: BaseHTTPRequestHandler,
    status_code: int,
    payload: dict[str, Any],
) -> None:
    body = json.dumps(payload).encode("utf-8")

    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    if content_length <= 0:
        return {}

    raw_body = handler.rfile.read(content_length)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}

    return payload if isinstance(payload, dict) else {}


class OperatorConsoleHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/health":
            _json_response(
                self,
                200,
                {
                    "status": "ok",
                    "service": "slate808-operator-console-backend",
                },
            )
            return

        if path == "/":
            self._serve_static_file("operator_console.html", "text/html")
            return

        if path == "/static/operator_console.css":
            self._serve_static_file("operator_console.css", "text/css")
            return

        _json_response(
            self,
            404,
            {
                "status": "error",
                "error": "Route not found.",
                "output": None,
            },
        )

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/run":
            self._handle_run()
            return

        if path == "/reset":
            self._handle_reset()
            return

        _json_response(
            self,
            404,
            {
                "status": "error",
                "error": "Route not found.",
                "output": None,
            },
        )

    def _handle_run(self) -> None:
        payload = _read_json_body(self)
        user_input = payload.get("input")

        if not isinstance(user_input, str) or not user_input.strip():
            _json_response(
                self,
                400,
                {
                    "status": "error",
                    "error": "Request field 'input' must be a non-empty string.",
                    "output": None,
                },
            )
            return

        output = run(user_input.strip())

        _json_response(
            self,
            200,
            {
                "status": "ok",
                "output": output,
            },
        )

    def _handle_reset(self) -> None:
        reset_state()

        _json_response(
            self,
            200,
            {
                "status": "ok",
                "output": "Session reset.",
            },
        )

    def _serve_static_file(self, filename: str, content_type: str) -> None:
        file_path = STATIC_DIR / filename

        if not file_path.exists():
            _json_response(
                self,
                404,
                {
                    "status": "error",
                    "error": "Static file not found.",
                    "output": None,
                },
            )
            return

        body = file_path.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the v1 console backend quiet during tests/manual use.
        return


def create_server(host: str = HOST, port: int = PORT) -> HTTPServer:
    return HTTPServer((host, port), OperatorConsoleHandler)


def main() -> None:
    server = create_server()
    print(f"Slate808 operator console backend running at http://{HOST}:{PORT}")
    print("Press CTRL+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Slate808 operator console backend.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
