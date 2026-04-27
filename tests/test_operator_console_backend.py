import json
from http.client import HTTPConnection
from threading import Thread

from ui.operator_console_server import create_server


def _start_test_server():
    server = create_server(host="127.0.0.1", port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _request(server, method: str, path: str, payload: dict | None = None):
    host, port = server.server_address
    connection = HTTPConnection(host, port)

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}

    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    response_body = response.read().decode("utf-8")
    connection.close()

    return response.status, json.loads(response_body)


def _raw_request(server, method: str, path: str):
    host, port = server.server_address
    connection = HTTPConnection(host, port)

    connection.request(method, path)
    response = connection.getresponse()
    response_body = response.read().decode("utf-8")
    connection.close()

    return response.status, response_body


def test_operator_console_health_route():
    server, _thread = _start_test_server()

    try:
        status, data = _request(server, "GET", "/health")

        assert status == 200
        assert data["status"] == "ok"
        assert data["service"] == "slate808-operator-console-backend"
    finally:
        server.shutdown()
        server.server_close()


def test_operator_console_root_serves_frontend_html():
    server, _thread = _start_test_server()

    try:
        status, body = _raw_request(server, "GET", "/")

        assert status == 200
        assert "Slate808 Operator Console" in body
        assert "Request Workspace" in body
        assert "Plan Output" in body
        assert "System State" in body
    finally:
        server.shutdown()
        server.server_close()


def test_operator_console_serves_css():
    server, _thread = _start_test_server()

    try:
        status, body = _raw_request(server, "GET", "/static/operator_console.css")

        assert status == 200
        assert ".console" in body
        assert ".panel" in body
    finally:
        server.shutdown()
        server.server_close()


def test_operator_console_run_requires_non_empty_input():
    server, _thread = _start_test_server()

    try:
        status, data = _request(server, "POST", "/run", {"input": ""})

        assert status == 400
        assert data["status"] == "error"
        assert "non-empty string" in data["error"]
        assert data["output"] is None
    finally:
        server.shutdown()
        server.server_close()


def test_operator_console_run_returns_engine_output():
    server, _thread = _start_test_server()

    try:
        _request(server, "POST", "/reset")
        status, data = _request(server, "POST", "/run", {"input": "Plan a trip to Naivasha"})

        assert status == 200
        assert data["status"] == "ok"
        assert "Operator Workflow:" in data["output"]
        assert "What exact dates are you planning?" in data["output"]
    finally:
        server.shutdown()
        server.server_close()


def test_operator_console_reset_route_resets_session():
    server, _thread = _start_test_server()

    try:
        _request(server, "POST", "/run", {"input": "Plan a trip to Naivasha"})

        reset_status, reset_data = _request(server, "POST", "/reset")
        next_status, next_data = _request(server, "POST", "/run", {"input": "4th-8th May"})

        assert reset_status == 200
        assert reset_data["status"] == "ok"
        assert reset_data["output"] == "Session reset."

        assert next_status == 200
        assert "Slate808 currently supports travel planning only" in next_data["output"]
    finally:
        server.shutdown()
        server.server_close()
