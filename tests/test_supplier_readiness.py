from engine.runner import run_engine
from engine.plan_refiner import refine_plan
from engine.planning_policy import build_planning_constraints


def test_trip_output_includes_supplier_readiness_check_and_risk():
    output = run_engine("Plan a trip to Diani for 2 people 10 April to 12 April with a budget of 60000")

    assert "Supplier Readiness:" in output
    assert "Verify supplier reliability, availability, cancellation terms, refund terms, payment instructions, local support, and backup options before booking." in output
    assert "Supplier Reliability Risk:" in output


def test_refiner_default_operational_checks_include_supplier_readiness_for_legacy_plans():
    legacy_plan = {
        "task_type": "trip",
        "goal": "Plan a trip",
        "brief": {
            "destination": "diani",
            "traveller_count": 2,
            "budget_level": "medium",
            "timing": {"state": "exact_timing"},
        },
        "steps": ["Choose transport", "Choose stay"],
        "checks": ["Old generic check"],
        "risks": ["Old generic risk"],
        "planning_constraints": build_planning_constraints({
            "destination": "diani",
            "traveller_count": 2,
            "budget_level": "medium",
            "timing": {"state": "exact_timing"},
        }),
    }

    refined = refine_plan(legacy_plan)

    assert any(check.startswith("Supplier Readiness:") for check in refined["checks"])
    assert any(risk.startswith("Supplier Reliability Risk:") for risk in refined["risks"])
