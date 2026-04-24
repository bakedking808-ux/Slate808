from copy import deepcopy

from engine.formatter import format_output
from engine.generator import build_steps
from engine.plan_refiner import refine_plan
from engine.planning_policy import build_planning_constraints
from engine.runner import run_engine
from engine.travel_brief import build_timing


def _brief(**overrides):
    brief = {
        "destination": "diani",
        "traveller_count": 4,
        "timing": build_timing(
            raw_text="next weekend",
            date_flexibility="fixed",
            state="relative_timing",
            confidence="medium",
        ),
        "budget_amount": None,
        "budget_level": "low",
        "trip_mood": "family",
    }
    brief.update(overrides)
    return brief


def _plan(brief=None):
    brief = brief or _brief()
    planning_constraints = build_planning_constraints(brief)
    return {
        "trace_id": "trace-refine-1",
        "task_type": "trip",
        "goal": "Plan a trip to diani",
        "mode": "normal",
        "clarification_needed": None,
        "clarification_response": None,
        "missing_fields": [],
        "steps": build_steps(
            "trip",
            {"brief": brief, "planning_constraints": planning_constraints},
        ),
        "checks": [
            "The journey should include a clear destination and smooth arrival",
            "Budget and travel arrangements should remain realistic and low-friction",
            "The trip should feel well-paced, with space for both experience and rest",
            "The ending should feel calm, complete, and memorable",
        ],
        "risks": [
            "Missing key planning detail",
            "Poor sequencing of steps",
        ],
        "brief": brief,
        "planning_constraints": planning_constraints,
    }


def test_refinement_preserves_plan_schema_step_count_and_semantics(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan()
    original = deepcopy(plan)

    refined = refine_plan(plan)

    assert set(refined.keys()) == set(original.keys())
    assert len(refined["steps"]) == len(original["steps"])
    assert refined["task_type"] == original["task_type"]
    assert refined["goal"] == original["goal"]
    assert refined["brief"]["destination"] == original["brief"]["destination"]
    assert refined["brief"]["traveller_count"] == original["brief"]["traveller_count"]
    assert refined["brief"]["timing"] == original["brief"]["timing"]


def test_refinement_only_changes_checks_and_risks_when_rules_apply(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan()
    original = deepcopy(plan)

    refined = refine_plan(plan)

    assert refined["steps"] == original["steps"]
    assert refined["checks"] != original["checks"]
    assert refined["risks"] != original["risks"]
    assert "stated budget" in refined["checks"][1]
    assert "family-safe pacing" in refined["risks"][1]


def test_refinement_is_noop_without_valid_constraints():
    plan = _plan()
    plan["planning_constraints"] = None

    refined = refine_plan(plan)

    assert refined == plan
    assert refined is not plan


def test_refined_plan_still_renders_with_same_structural_sections(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan()
    refined = refine_plan(plan)

    output = format_output({"status": "pass", "errors": [], **refined})

    assert "Travel Brief:" in output
    assert "Steps:" in output
    assert "Checks:" in output
    assert "Risks:" in output
    assert "Traveller Count: 4" in output


def test_runner_routes_successful_plan_through_refinement_layer():
    output = run_engine("Plan a family trip to diani for 4 people next weekend with a low budget")

    assert "Costs should be checked against the stated budget before booking" in output
    assert "The plan may become too complex if family-safe pacing is not preserved" in output
