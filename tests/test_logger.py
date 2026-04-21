import json

import engine.logger as logger


def test_get_log_dir_for_today_creates_dated_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(logger, "LOGS_ROOT", tmp_path / "logs")
    monkeypatch.setattr(logger, "local_date_str", lambda: "2026-04-19")

    log_dir = logger.get_log_dir_for_today()

    assert log_dir == tmp_path / "logs" / "2026-04-19"
    assert log_dir.is_dir()


def test_get_log_file_path_returns_dated_log_path(monkeypatch, tmp_path):
    monkeypatch.setattr(logger, "LOGS_ROOT", tmp_path / "logs")
    monkeypatch.setattr(logger, "local_date_str", lambda: "2026-04-19")

    path = logger.get_log_file_path("pytest.log")

    assert path == tmp_path / "logs" / "2026-04-19" / "pytest.log"
    assert path.parent.is_dir()


def test_log_run_writes_engine_log_inside_dated_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(logger, "LOGS_ROOT", tmp_path / "logs")
    monkeypatch.setattr(logger, "local_date_str", lambda: "2026-04-19")
    monkeypatch.setattr(logger, "local_timestamp", lambda: "2026-04-19 10:00:00 EAT")

    entry = logger.create_log_entry(
        trace_id="abc123",
        input_text="Plan a trip to diani",
        task_type="trip",
        generated_steps=["step 1"],
        checker_result={"status": "pass", "errors": []},
        fixer_actions=[],
        final_output={"status": "pass"},
    )

    logger.log_run(entry)

    log_path = tmp_path / "logs" / "2026-04-19" / "engine.log"
    assert log_path.is_file()

    saved = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert saved["trace_id"] == "abc123"
    assert saved["timestamp"] == "2026-04-19 10:00:00 EAT"


def test_log_event_writes_named_log_inside_dated_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(logger, "LOGS_ROOT", tmp_path / "logs")
    monkeypatch.setattr(logger, "local_date_str", lambda: "2026-04-19")
    monkeypatch.setattr(logger, "local_timestamp", lambda: "2026-04-19 11:00:00 EAT")

    logger.log_event(
        filename="manual-tests.log",
        source="manual",
        layer="smoke",
        event="run",
        status="pass",
        trace_id="trace-1",
        details={"case": "trip"},
    )

    log_path = tmp_path / "logs" / "2026-04-19" / "manual-tests.log"
    assert log_path.is_file()

    saved = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert saved["source"] == "manual"
    assert saved["trace_id"] == "trace-1"
    assert saved["details"] == {"case": "trip"}
    assert saved["timestamp"] == "2026-04-19 11:00:00 EAT"


def test_append_log_writes_plain_line_inside_dated_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(logger, "LOGS_ROOT", tmp_path / "logs")
    monkeypatch.setattr(logger, "local_date_str", lambda: "2026-04-19")

    logger.append_log("decisions.log", "{'budget_posture': 'balanced'}")

    log_path = tmp_path / "logs" / "2026-04-19" / "decisions.log"
    assert log_path.is_file()
    assert log_path.read_text(encoding="utf-8") == "{'budget_posture': 'balanced'}\n"
