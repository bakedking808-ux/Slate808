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


def test_build_confidence_readout_counts_known_metric_events_only():
    readout = logger.build_confidence_readout(
        [
            {"event": "clarification_routed"},
            {"event": "relative_timing_exact_date_refinement"},
            {"event": "relative_timing_exact_date_refinement"},
            {"event": "execution_blocked"},
            {"event": "execution_rejected"},
            {"event": "execution_weak"},
            {"event": "execution_completed"},
            {"event": "unrelated_event"},
        ]
    )

    assert readout == {
        "clarification_routed_count": 1,
        "relative_timing_exact_date_refinement_count": 2,
        "execution_blocked_count": 1,
        "execution_rejected_count": 1,
        "execution_weak_count": 1,
        "execution_completed_count": 1,
        "runtime_outcome_family_counts": {
            "blocked": 1,
            "rejected": 1,
            "weak": 1,
            "completed": 1,
        },
        "dominant_runtime_outcome_family": "blocked",
        "dominant_failure_outcome_family": "blocked",
        "clarification_routed_by_missing_fields": {},
        "execution_blocked_by_reason": {},
        "execution_rejected_by_reason": {},
        "execution_weak_by_reason": {},
        "execution_completed_by_task_type": {},
        "execution_completed_by_flow_shape": {},
        "execution_completed_repaired_count": 0,
        "execution_outcomes_by_decision_path": {},
        "execution_completed_by_flow_shape": {},
        "execution_completed_repaired_count": 0,
        "runtime_outcome_events_by_trace": {},
    }


def test_read_confidence_readout_uses_logged_event_file(monkeypatch, tmp_path):
    monkeypatch.setattr(logger, "LOGS_ROOT", tmp_path / "logs")
    monkeypatch.setattr(logger, "local_date_str", lambda: "2026-04-19")
    monkeypatch.setattr(logger, "local_timestamp", lambda: "2026-04-19 11:00:00 EAT")

    logger.log_event(
        filename="engine.log",
        source="runner",
        layer="execution",
        event="execution_completed",
        status="success",
    )

    assert logger.read_confidence_readout("engine.log")["execution_completed_count"] == 1


def test_confidence_readout_ignores_trace_fields():
    readout = logger.build_confidence_readout(
        [
            {"trace_id": "trace-1", "event": "execution_completed"},
            {"trace_id": "trace-1", "event": "clarification_routed"},
        ]
    )

    assert readout["execution_completed_count"] == 1
    assert readout["clarification_routed_count"] == 1


def test_confidence_readout_groups_clarification_missing_fields():
    readout = logger.build_confidence_readout(
        [
            {
                "event": "clarification_routed",
                "details": {"missing_fields": ["destination", "timing"]},
            },
            {
                "event": "clarification_routed",
                "details": {"missing_fields": ["destination", "timing"]},
            },
            {
                "event": "clarification_routed",
                "details": {"missing_fields": ["traveller_count"]},
            },
        ]
    )

    assert readout["clarification_routed_by_missing_fields"] == {
        "destination,timing": 2,
        "traveller_count": 1,
    }


def test_confidence_readout_groups_execution_reasons():
    readout = logger.build_confidence_readout(
        [
            {"event": "execution_blocked", "details": {"reason": "Unsafe input"}},
            {"event": "execution_blocked", "details": {"reason": "Unsafe input"}},
            {"event": "execution_rejected", "details": {"reason": "Non-travel request"}},
            {"event": "execution_weak", "details": {"reason": "Input too short"}},
        ]
    )

    assert readout["execution_blocked_by_reason"] == {"Unsafe input": 2}
    assert readout["execution_rejected_by_reason"] == {"Non-travel request": 1}
    assert readout["execution_weak_by_reason"] == {"Input too short": 1}
    assert readout["runtime_outcome_family_counts"] == {
        "blocked": 2,
        "rejected": 1,
        "weak": 1,
        "completed": 0,
    }
    assert readout["dominant_runtime_outcome_family"] == "blocked"
    assert readout["dominant_failure_outcome_family"] == "blocked"


def test_confidence_readout_groups_completed_flow_shapes_and_repairs():
    readout = logger.build_confidence_readout(
        [
            {
                "trace_id": "trace-1",
                "event": "execution_completed",
                "status": "success",
                "details": {
                    "task_type": "trip",
                    "flow_shape": "direct_ready_completion",
                    "decision_path": "input_gate>generate_plan>check_plan>apply_task_layers>check_plan",
                    "used_repair": False,
                },
            },
            {
                "trace_id": "trace-2",
                "event": "execution_completed",
                "status": "success",
                "details": {
                    "task_type": "trip",
                    "flow_shape": "clarification_resume_completion",
                    "decision_path": "input_gate>generate_plan>check_plan>fix_plan>check_plan>apply_task_layers>check_plan",
                    "used_repair": True,
                },
            },
        ]
    )

    assert readout["execution_completed_by_task_type"] == {"trip": 2}
    assert readout["runtime_outcome_family_counts"] == {
        "blocked": 0,
        "rejected": 0,
        "weak": 0,
        "completed": 2,
    }
    assert readout["dominant_runtime_outcome_family"] == "completed"
    assert readout["dominant_failure_outcome_family"] is None
    assert readout["execution_completed_by_flow_shape"] == {
        "direct_ready_completion": 1,
        "clarification_resume_completion": 1,
    }
    assert readout["execution_completed_repaired_count"] == 1
    assert readout["execution_outcomes_by_decision_path"] == {
        "input_gate>generate_plan>check_plan>apply_task_layers>check_plan": 1,
        "input_gate>generate_plan>check_plan>fix_plan>check_plan>apply_task_layers>check_plan": 1,
    }
    assert readout["runtime_outcome_events_by_trace"] == {
        "trace-1": [
            {
                "event": "execution_completed",
                "status": "success",
                "task_type": "trip",
                "flow_shape": "direct_ready_completion",
                "decision_path": "input_gate>generate_plan>check_plan>apply_task_layers>check_plan",
            }
        ],
        "trace-2": [
            {
                "event": "execution_completed",
                "status": "success",
                "task_type": "trip",
                "flow_shape": "clarification_resume_completion",
                "decision_path": "input_gate>generate_plan>check_plan>fix_plan>check_plan>apply_task_layers>check_plan",
                "used_repair": True,
            }
        ],
    }


def test_confidence_readout_groups_completed_task_types_and_trace_outcomes():
    readout = logger.build_confidence_readout(
        [
            {
                "trace_id": "trace-1",
                "event": "execution_blocked",
                "status": "blocked",
                    "details": {
                        "reason": "Unsafe input",
                        "decision_path": "input_gate>blocked_input_hard_stop",
                        "transition": "blocked_input_hard_stop",
                        "pipeline_stop": "blocked_input_hard_stop",
                    },
            },
            {
                "trace_id": "trace-2",
                "event": "execution_completed",
                "status": "success",
                    "details": {
                        "task_type": "trip",
                        "decision_path": "input_gate>generate_plan>check_plan>apply_task_layers>check_plan",
                        "final_status": "pass",
                        "transition": "execution_completed",
                    },
            },
        ]
    )

    assert readout["execution_completed_by_task_type"] == {"trip": 1}
    assert readout["execution_outcomes_by_decision_path"] == {
        "input_gate>blocked_input_hard_stop": 1,
        "input_gate>generate_plan>check_plan>apply_task_layers>check_plan": 1,
    }
    assert readout["runtime_outcome_events_by_trace"] == {
        "trace-1": [
            {
                "event": "execution_blocked",
                "status": "blocked",
                "reason": "Unsafe input",
                "decision_path": "input_gate>blocked_input_hard_stop",
                "transition": "blocked_input_hard_stop",
                "pipeline_stop": "blocked_input_hard_stop",
            }
        ],
        "trace-2": [
            {
                "event": "execution_completed",
                "status": "success",
                "task_type": "trip",
                "decision_path": "input_gate>generate_plan>check_plan>apply_task_layers>check_plan",
                "transition": "execution_completed",
                "final_status": "pass",
            }
        ],
    }
