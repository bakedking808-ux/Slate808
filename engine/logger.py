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


def local_date_str() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")


def local_timestamp() -> str:
    return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S EAT")


def get_log_dir_for_today() -> Path:
    log_dir = LOGS_ROOT / local_date_str()
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _next_session_number(day_dir: Path) -> int:
    existing_numbers = []

    for path in day_dir.iterdir() if day_dir.exists() else []:
        if not path.is_dir():
            continue
        name = path.name
        if not name.startswith("session-"):
            continue
        suffix = name.removeprefix("session-")
        if suffix.isdigit():
            existing_numbers.append(int(suffix))

    if not existing_numbers:
        return 1

    return max(existing_numbers) + 1


def create_session_log_dir() -> Path:
    day_dir = get_log_dir_for_today()
    session_number = _next_session_number(day_dir)
    session_dir = day_dir / f"session-{session_number:03d}"
    session_dir.mkdir(parents=True, exist_ok=False)
    return session_dir


def get_latest_session_log_dir() -> Path:
    day_dir = get_log_dir_for_today()
    sessions = []

    for path in day_dir.iterdir():
        if not path.is_dir():
            continue
        name = path.name
        if not name.startswith("session-"):
            continue
        suffix = name.removeprefix("session-")
        if suffix.isdigit():
            sessions.append((int(suffix), path))

    if not sessions:
        return create_session_log_dir()

    return max(sessions, key=lambda item: item[0])[1]


def get_log_file_path(filename: str, session_dir: Path | None = None) -> Path:
    target_dir = session_dir or get_latest_session_log_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / filename


def append_log(filename: str, line: str, session_dir: Path | None = None) -> None:
    with get_log_file_path(filename, session_dir=session_dir).open("a", encoding="utf-8") as f:
        f.write(f"{line}\n")


def log_run(entry: dict, session_dir: Path | None = None):
    entry["timestamp"] = local_timestamp()

    with get_log_file_path(ENGINE_LOG_FILENAME, session_dir=session_dir).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def create_log_entry(
    trace_id,
    input_text,
    task_type,
    generated_steps,
    checker_result,
    fixer_actions,
    final_output,
):
    return {
        "trace_id": trace_id,
        "input": input_text,
        "task_type": task_type,
        "generated_steps": generated_steps,
        "checker_result": checker_result,
        "fixer_actions": fixer_actions,
        "final_output": final_output,
    }


def log_event(
    filename: str,
    source: str,
    layer: str,
    event: str,
    status: str,
    trace_id=None,
    details=None,
    session_dir: Path | None = None,
):
    entry = {
        "timestamp": local_timestamp(),
        "trace_id": trace_id,
        "source": source,
        "layer": layer,
        "event": event,
        "status": status,
        "details": details or {},
    }

    with get_log_file_path(filename, session_dir=session_dir).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _increment_group(group: dict, key) -> None:
    if key:
        group[str(key)] = group.get(str(key), 0) + 1


def _dominant_group(group: dict, keys: tuple[str, ...]) -> str | None:
    counts = {key: group.get(key, 0) for key in keys}
    if not any(counts.values()):
        return None
    return max(keys, key=lambda key: counts[key])


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
    readout["execution_completed_by_task_type"] = {}
    readout["execution_completed_by_flow_shape"] = {}
    readout["execution_completed_repaired_count"] = 0
    readout["execution_outcomes_by_decision_path"] = {}
    readout["runtime_outcome_events_by_trace"] = {}

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

        if event in RUNTIME_OUTCOME_EVENTS:
            _increment_group(readout["execution_outcomes_by_decision_path"], details.get("decision_path"))

        if event == "execution_completed":
            _increment_group(readout["execution_completed_by_task_type"], details.get("task_type"))
            _increment_group(readout["execution_completed_by_flow_shape"], details.get("flow_shape"))
            if details.get("used_repair"):
                readout["execution_completed_repaired_count"] += 1

        if trace_id and event in RUNTIME_OUTCOME_EVENTS:
            event_readout = {"event": event, "status": entry.get("status")}
            for key in (
                "reason",
                "task_type",
                "flow_shape",
                "decision_path",
                "transition",
                "pipeline_stop",
                "final_status",
            ):
                if details.get(key) is not None:
                    event_readout[key] = details.get(key)
            if details.get("used_repair"):
                event_readout["used_repair"] = True
            readout["runtime_outcome_events_by_trace"].setdefault(trace_id, []).append(event_readout)

    readout["dominant_runtime_outcome_family"] = _dominant_group(
        readout["runtime_outcome_family_counts"],
        ("blocked", "rejected", "weak", "completed"),
    )
    readout["dominant_failure_outcome_family"] = _dominant_group(
        readout["runtime_outcome_family_counts"],
        ("blocked", "rejected", "weak"),
    )

    return readout


def read_confidence_readout(
    filename: str = ENGINE_LOG_FILENAME,
    session_dir: Path | None = None,
) -> dict:
    log_path = get_log_file_path(filename, session_dir=session_dir)

    if not log_path.exists():
        return build_confidence_readout([])

    events = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    return build_confidence_readout(events)
