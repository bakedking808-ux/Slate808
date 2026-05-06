import pytest

import engine.generator as generator
from engine.planning_policy import (
    build_planning_constraints,
    derive_planning_constraints,
    validate_planning_constraints,
)
from engine.travel_brief import build_timing


def _brief(**overrides):
    brief = {
        "destination": "nairobi",
        "traveller_count": 5,
        "timing": build_timing(
            raw_text="next weekend",
            date_flexibility="fixed",
            state="relative_timing",
            confidence="medium",
        ),
        "budget_amount": None,
        "budget_level": "medium",
        "trip_mood": "romantic",
    }
    brief.update(overrides)
    return brief


def test_build_planning_constraints_is_stable_public_entrypoint(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    built = build_planning_constraints(_brief())
    derived = derive_planning_constraints(_brief())

    assert built == derived
    assert validate_planning_constraints(built).model_dump() == built


def test_build_planning_constraints_logs_compact_policy_summary(monkeypatch):
    logged = []
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: logged.append((filename, line)))

    constraints = build_planning_constraints(
        _brief(destination="mt kenya", trip_mood="relaxed"),
        trace_id="trace-policy-1",
    )

    assert logged
    assert logged[0][0] == "decisions.log"
    assert "'trace_id': 'trace-policy-1'" in logged[0][1]
    assert "'trace_origin': 'manual_run'" in logged[0][1]
    assert "constraint_policy" in logged[0][1]
    assert "conflict_flags" in logged[0][1]
    assert "refinement_flags" in logged[0][1]
    assert constraints["constraint_policy"]["low_mobility"] is True


def test_build_planning_constraints_logs_direct_policy_origin_without_trace_id(monkeypatch):
    logged = []
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: logged.append((filename, line)))

    build_planning_constraints(_brief())

    assert "'trace_id': None" in logged[0][1]
    assert "'trace_origin': 'direct_policy_call'" in logged[0][1]


def test_build_planning_constraints_accepts_explicit_test_origin(monkeypatch):
    logged = []
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: logged.append((filename, line)))

    build_planning_constraints(_brief(), trace_origin="test_run")

    assert "'trace_origin': 'test_run'" in logged[0][1]


def test_build_planning_constraints_marks_invalid_origin_unknown(monkeypatch):
    logged = []
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: logged.append((filename, line)))

    build_planning_constraints(_brief(), trace_origin="weird_source")

    assert "'trace_origin': 'unknown'" in logged[0][1]


def test_derive_planning_constraints_forwards_trace_origin(monkeypatch):
    logged = []
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: logged.append((filename, line)))

    derive_planning_constraints(_brief(), trace_origin="test_run")

    assert "'trace_origin': 'test_run'" in logged[0][1]


def test_generator_rejects_invalid_planning_constraints_shape():
    with pytest.raises(Exception):
        generator.build_steps(
            "trip",
            {
                "brief": _brief(),
                "planning_constraints": {
                    "budget_policy": {},
                    "constraint_policy": {},
                },
            },
        )
