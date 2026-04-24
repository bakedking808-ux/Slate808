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
    assert refined["steps"][0] == original["steps"][0]
    assert "transport" in refined["steps"][2].lower()
    assert "activities" in refined["steps"][3].lower()
    assert "timing" in refined["steps"][4].lower()
    assert refined["task_type"] == original["task_type"]
    assert refined["goal"] == original["goal"]
    assert refined["brief"]["destination"] == original["brief"]["destination"]
    assert refined["brief"]["traveller_count"] == original["brief"]["traveller_count"]
    assert refined["brief"]["timing"] == original["brief"]["timing"]


def test_refinement_specializes_checks_and_risks_without_changing_step_shape(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan()
    original = deepcopy(plan)

    refined = refine_plan(plan)

    assert len(refined["steps"]) == len(original["steps"])
    assert [step.split()[0] for step in refined["steps"]] == [step.split()[0] for step in original["steps"]]
    assert refined["checks"] != original["checks"]
    assert refined["risks"] != original["risks"]
    assert "stated budget" in refined["checks"][1]
    assert "family-safe pacing" in refined["risks"][1]


def test_refinement_suppresses_repeated_semantic_tails_deterministically(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan(_brief(trip_mood="luxury", budget_level="high", traveller_count=2))
    plan["steps"][4] = (
        "Confirm the trip timing by setting the departure date as 20 july "
        "and the return date as 24 july, then align bookings and align premium bookings"
    )

    first = refine_plan(plan)
    second = refine_plan(plan)

    assert first["steps"] == second["steps"]
    assert len(first["steps"]) == len(plan["steps"])
    assert first["steps"][4].count("align") == 1
    assert "align premium bookings" in first["steps"][4]


def test_refinement_compacts_shaped_step_suffixes_without_losing_context(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan()
    plan["steps"][2] = (
        "Choose practical transport arrangements that make moving the family easy "
        "with safe and comfortable movement for everyone; practical and safe movement; "
        "shared meeting points and aligned movement"
    )
    plan["steps"][3] = (
        "Select family-friendly activities that keep everyone comfortable "
        "with family-friendly, comfortable options; logistics that keep the group coordinated"
    )

    refined = refine_plan(plan)

    assert refined["steps"][2].startswith("Choose practical transport arrangements")
    assert "family easy" in refined["steps"][2]
    assert "shared meeting points and aligned movement" in refined["steps"][2]
    assert "practical and safe movement" not in refined["steps"][2]
    assert "family-friendly activities" in refined["steps"][3]
    assert "comfortable family options" in refined["steps"][3]
    assert "logistics that keep the group coordinated" in refined["steps"][3]


def test_family_timing_compaction_preserves_booking_anchor(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan()
    plan["steps"][4] = (
        "Confirm the trip timing window as next weekend and align bookings "
        "and align transport and accommodation for the family"
    )

    refined = refine_plan(plan)

    assert "align bookings" in refined["steps"][4]
    assert refined["steps"][4].count("align") == 1
    assert "transport" in refined["steps"][4]
    assert "accommodation" in refined["steps"][4]


def test_weak_generic_steps_upgrade_when_destination_context_exists(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan()
    plan["steps"][2] = "Choose transport and lodging options that fit the trip"
    plan["steps"][3] = "Select activities that match your travel goals"

    first = refine_plan(plan)
    second = refine_plan(plan)

    assert first["steps"] == second["steps"]
    assert len(first["steps"]) == len(plan["steps"])
    assert first["steps"][2] == "Choose transport and lodging options for diani that fit the trip"
    assert first["steps"][3] == "Select activities in diani that match your travel goals"


def test_weak_generic_steps_remain_unchanged_without_destination_context(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan(_brief(destination=None))
    plan["steps"][2] = "Choose transport and lodging options that fit the trip"
    plan["steps"][3] = "Select activities that match your travel goals"

    refined = refine_plan(plan)

    assert refined["steps"][2] == plan["steps"][2]
    assert refined["steps"][3] == plan["steps"][3]


def test_post_update_like_completed_plan_steps_become_more_specific(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)
    plan = _plan(_brief(destination="lamu", traveller_count=2, trip_mood=None, budget_level="unspecified"))
    plan["steps"][2] = "Choose transport and lodging options that fit the trip"
    plan["steps"][3] = "Select activities that match your travel goals"
    original = deepcopy(plan)

    refined = refine_plan(plan)

    assert len(refined["steps"]) == len(original["steps"])
    assert [step.split()[0] for step in refined["steps"]] == [step.split()[0] for step in original["steps"]]
    assert "for lamu" in refined["steps"][2]
    assert "in lamu" in refined["steps"][3]
    assert refined["brief"]["destination"] == "lamu"


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
