import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LOGS_ROOT = Path("logs")
ENGINE_LOG_FILENAME = "engine.log"
LOCAL_TZ = ZoneInfo("Africa/Nairobi")
CONFIDENCE_READOUT_EVENTS = (
    "clarification_routed",
    "relative_timing_exact_date_refinement",
    "execution_blocked",
    "execution_rejected",
    "execution_weak",
    "execution_completed",
)
RUNTIME_OUTCOME_EVENTS = (
    "execution_blocked",
    "execution_rejected",
    "execution_weak",
    "execution_completed",
)


def _increment_group(group: dict, key) -> None:
    if key:
        group[str(key)] = group.get(str(key), 0) + 1


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


def build_confidence_readout(events: list[dict]) -> dict:
    readout = {f"{event}_count": 0 for event in CONFIDENCE_READOUT_EVENTS}
    readout["runtime_outcome_family_counts"] = {
        "blocked": 0,
        "rejected": 0,
        "weak": 0,
        "completed": 0,
    }
    readout["dominant_runtime_outcome_family"] = None
    readout["dominant_failure_outcome_family"] = None
    readout["clarification_routed_by_missing_fields"] = {}
    readout["execution_blocked_by_reason"] = {}
    readout["execution_rejected_by_reason"] = {}
    readout["execution_weak_by_reason"] = {}
    for entry in events:
        event = entry.get("event")
        if event in CONFIDENCE_READOUT_EVENTS:
            readout[f"{event}_count"] += 1
        if event == "execution_blocked":
            readout["runtime_outcome_family_counts"]["blocked"] += 1
        if event == "execution_rejected":
            readout["runtime_outcome_family_counts"]["rejected"] += 1
        if event == "execution_weak":
            readout["runtime_outcome_family_counts"]["weak"] += 1
        if event == "execution_completed":
            readout["runtime_outcome_family_counts"]["completed"] += 1
        details = entry.get("details") or {}
        trace_id = entry.get("trace_id")
        if event == "clarification_routed":
            missing_fields = details.get("missing_fields") or []
            _increment_group(
                readout["clarification_routed_by_missing_fields"],
                ",".join(str(field) for field in missing_fields),
            )
        if event == "execution_blocked":
            _increment_group(readout["execution_blocked_by_reason"], details.get("reason"))
        if event == "execution_rejected":
            _increment_group(readout["execution_rejected_by_reason"], details.get("reason"))
        if event == "execution_weak":
            _increment_group(readout["execution_weak_by_reason"], details.get("reason"))
    return readout


def read_confidence_readout(filename: str = ENGINE_LOG_FILENAME) -> dict:
    log_path = get_log_file_path(filename)
    if not log_path.exists():
        return build_confidence_readout([])

    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return build_confidence_readout(events)
