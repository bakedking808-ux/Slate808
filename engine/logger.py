import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LOGS_ROOT = Path("logs")
ENGINE_LOG_FILENAME = "engine.log"
LOCAL_TZ = ZoneInfo("Africa/Nairobi")


def local_date_str() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")


def local_timestamp() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S EAT")


def get_log_dir_for_today() -> Path:
    log_dir = LOGS_ROOT / local_date_str()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file_path(filename: str) -> Path:
    return get_log_dir_for_today() / filename


def append_log(filename: str, line: str) -> None:
    with get_log_file_path(filename).open("a", encoding="utf-8") as f:
        f.write(f"{line}\n")


def log_run(entry: dict):
    """Append a single engine run entry as one JSON line."""
    entry["timestamp"] = local_timestamp()

    with get_log_file_path(ENGINE_LOG_FILENAME).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def create_log_entry(
    trace_id,
    input_text,
    task_type,
    generated_steps,
    checker_result,
    fixer_actions,
    final_output
):
    """Build the full engine run log entry structure."""
    return {
        "trace_id": trace_id,
        "input": input_text,
        "task_type": task_type,
        "generated_steps": generated_steps,
        "checker_result": checker_result,
        "fixer_actions": fixer_actions,
        "final_output": final_output
    }


def log_event(
    filename: str,
    source: str,
    layer: str,
    event: str,
    status: str,
    trace_id=None,
    details=None
):
    """Structured event logger (JSON lines)."""
    entry = {
        "timestamp": local_timestamp(),
        "trace_id": trace_id,
        "source": source,
        "layer": layer,
        "event": event,
        "status": status,
        "details": details or {}
    }

    with get_log_file_path(filename).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
