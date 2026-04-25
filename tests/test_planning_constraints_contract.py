import pytest
from pydantic import ValidationError

import engine.generator as generator
from engine.checker import check_plan
from engine.planning_constraints import PlanningConstraints
from engine.planning_policy import build_planning_constraints
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


def test_planning_constraints_contract_validates_and_preserves_dict_shape(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    planning_constraints = build_planning_constraints(_brief())
    model = PlanningConstraints(**planning_constraints)
    dumped = model.model_dump()

    assert set(dumped.keys()) == {
        "destination_policy",
        "budget_policy",
        "traveller_policy",
        "mood_policy",
        "timing_policy",
        "constraint_policy",
        "sequence_policy",
        "global_flags",
    }
    assert dumped == planning_constraints


def test_invalid_planning_constraints_shape_fails_loudly():
    with pytest.raises(ValidationError):
        PlanningConstraints(
            budget_policy={},
            traveller_policy={},
            mood_policy={},
            timing_policy={},
            constraint_policy={},
            sequence_policy={},
            global_flags={},
        )


def test_generator_works_with_validated_planning_constraints(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    brief = _brief()
    planning_constraints = build_planning_constraints(brief)
    steps = generator.build_steps(
        "trip",
        {
            "brief": brief,
            "planning_constraints": planning_constraints,
        },
    )

    assert len(steps) == 5
    assert "destination" in steps[0].lower()


def test_checker_works_with_validated_planning_constraints(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    brief = _brief()
    planning_constraints = build_planning_constraints(brief)
    plan = {
        "task_type": "trip",
        "goal": "Plan a trip",
        "steps": generator.build_steps(
            "trip",
            {
                "brief": brief,
                "planning_constraints": planning_constraints,
            },
        ),
        "checks": [],
        "risks": [],
        "brief": brief,
        "planning_constraints": planning_constraints,
    }

    result = check_plan(plan)
    assert result["status"] == "pass"
