import engine.checker as checker
import engine.generator as generator
from engine.planning_policy import build_planning_constraints
from engine.travel_brief import build_timing


def _brief(**overrides):
    brief = {
        "destination": "diani",
        "traveller_count": 2,
        "timing": build_timing(
            raw_text="next weekend",
            date_flexibility="fixed",
            state="relative_timing",
            confidence="medium",
        ),
        "budget_amount": None,
        "budget_level": "medium",
        "trip_mood": None,
    }
    brief.update(overrides)
    return brief


def test_generator_uses_planning_constraints_instead_of_raw_brief_branching(monkeypatch):
    monkeypatch.setattr(
        generator.travel_brief,
        "build_travel_brief",
        lambda request, decision_log=None: {
            "destination": "diani",
            "traveller_count": 4,
            "timing": {
                "raw_text": "next weekend",
                "state": "relative_timing",
                "date_flexibility": "fixed",
                "confidence": "medium",
            },
            "budget_amount": 15000,
            "budget_level": "low",
            "trip_mood": "family",
        },
    )
    monkeypatch.setattr(
        generator,
        "build_planning_constraints",
        lambda brief, trace_id=None: {
            "destination_policy": {
                "resolved_destination": "diani",
                "destination_type": "mixed_or_unknown",
                "activity_bias": ["general"],
                "transport_bias": "standard",
                "accommodation_bias": "standard",
                "pace_bias": "balanced",
                "risk_flags": [],
            },
            "budget_policy": {
                "budget_posture": "premium",
            },
            "traveller_policy": {
                "traveller_count": 4,
                "group_type": "small_group",
                "has_children": True,
                "needs_family_safe_planning": True,
                "needs_group_coordination": True,
                "should_reduce_complexity": True,
                "activity_intensity": "moderate",
            },
            "mood_policy": {
                "trip_mood": "luxury",
            },
            "timing_policy": {
                "timing_summary": "next weekend",
                "is_exact_timing": False,
                "is_relative_timing": True,
                "is_duration_only": False,
                "is_month_only": False,
                "is_timing_usable": True,
            },
            "constraint_policy": {
                "family_safe": False,
                "low_risk": False,
                "avoid_premium": False,
                "value_focused": False,
                "group_coordination": False,
                "kids_present": False,
                "low_mobility": False,
                "quiet_preferred": False,
                "slow_pace": False,
                "high_activity": False,
            },
            "sequence_policy": {
                "arrival_light": False,
                "departure_buffer": False,
                "short_trip_compressed": False,
                "remote_daylight_movement": False,
                "early_start_activity": False,
                "family_recovery_pacing": False,
                "base_first": False,
                "activity_grouping": "general",
                "sequence_flags": [],
            },
            "global_flags": {
                "constraints": [],
                "is_budget_constrained": False,
                "is_group_sensitive": False,
                "is_timing_strong": True,
                "requires_safe_activity_filter": False,
                "requires_coordination_bias": False,
                "conflict_flags": [],
                "resolved_constraints": [],
                "refinement_flags": [],
            },
        },
    )

    plan = generator.generate_plan("Plan a trip to diani")
    steps = [step.lower() for step in plan["steps"]]

    assert "premium budget" in steps[1]
    assert "comfortable and convenient transport options" in steps[2]
    assert "high-quality, curated experiences" in steps[3]
    assert "align premium bookings" in steps[4]
    assert "family-friendly" not in steps[3]


def test_generator_timing_step_can_follow_policy_flags_over_raw_timing_state():
    brief = _brief(
        timing={
            "raw_text": "april",
            "state": "relative_timing",
            "date_flexibility": "fixed",
            "confidence": "medium",
        }
    )
    planning_constraints = build_planning_constraints(brief)
    planning_constraints["timing_policy"].update(
        {
            "timing_summary": "april",
            "is_exact_timing": False,
            "is_relative_timing": False,
            "is_duration_only": False,
            "is_month_only": True,
        }
    )
    steps = generator.build_steps(
        "trip",
        {
            "brief": brief,
            "planning_constraints": planning_constraints,
        },
    )

    assert steps[4] == "Confirm the trip timing by choosing preferred dates within april and align bookings"


def test_timing_steps_remain_concrete_and_checker_safe_across_usable_timing_states():
    cases = [
        (
            "Plan a trip to diani for 2 people 10 april to 14 april",
            ["departure date as 10 april", "return date as 14 april", "align bookings"],
        ),
        (
            "Plan a trip to diani for 2 people next weekend",
            ["timing window as next weekend", "align bookings"],
        ),
        (
            "Plan a trip to diani for 2 people for 2 nights",
            ["timing as 2 nights", "align transport and accommodation"],
        ),
        (
            "Plan a trip to diani for 2 people in april",
            ["preferred dates within april", "align bookings"],
        ),
    ]

    for request, expected_bits in cases:
        plan = generator.generate_plan(request)
        timing_step = plan["steps"][4].lower()

        for bit in expected_bits:
            assert bit in timing_step

        assert "manageable pacing" not in timing_step
        assert "clear transitions" not in timing_step
        assert checker.check_plan(plan)["status"] == "pass"


def test_policy_aligned_outputs_for_supported_moods():
    cases = [
        (
            "Plan a relaxed trip to diani for 2 people next weekend",
            "choose transport arrangements that keep movement calm, smooth, and low-friction",
            "select restful and scenic activities that support a calm travel pace",
        ),
        (
            "Plan an adventure trip to mara for 3 people for 5 days",
            "choose transport arrangements that support active excursions and movement",
            "select adventurous activities and outdoor experiences",
        ),
        (
            "Plan a luxury trip to zanzibar for 2 people next month",
            "set a premium budget and estimate the costs for an elevated experience",
            "select high-quality, curated experiences",
        ),
        (
            "Plan a family trip to the coast for 4 people next weekend",
            "choose practical transport arrangements that make moving the family easy",
            "select family-friendly activities that keep everyone comfortable",
        ),
        (
            "Plan a corporate retreat to nairobi for 10 people for 2 days",
            "set a realistic budget with team coordination and efficient logistics in mind",
            "select structured activities suitable for a team or group",
        ),
    ]

    for request, expected_step_two_or_three, expected_step_three_or_four in cases:
        plan = generator.generate_plan(request)
        steps = [step.lower() for step in plan["steps"]]
        joined = " ".join(steps)

        assert expected_step_two_or_three in joined
        assert expected_step_three_or_four in joined


def test_generator_applies_destination_policy_to_generic_trip_steps():
    brief = _brief()
    planning_constraints = build_planning_constraints(brief)
    steps = generator.build_steps(
        "trip",
        {
            "brief": brief,
            "planning_constraints": planning_constraints,
        },
    )

    assert "road or air connections planned around the coast" in steps[2].lower()
    assert "beach, water, and relaxation experiences" in steps[3].lower()


def test_generator_combines_mood_and_destination_policy_wording():
    brief = _brief(
        destination="mara",
        trip_mood="adventure",
        timing={
            "raw_text": "for 5 days",
            "state": "duration_only",
            "duration_days": 5,
            "date_flexibility": "unknown",
            "confidence": "medium",
        },
    )
    planning_constraints = build_planning_constraints(brief)
    steps = generator.build_steps(
        "trip",
        {
            "brief": brief,
            "planning_constraints": planning_constraints,
        },
    )

    assert "support active excursions and movement" in steps[2].lower()
    assert "airstrip or 4x4 transfers suited to safari access" in steps[2].lower()
    assert "adventurous activities and outdoor experiences" in steps[3].lower()
    assert "wildlife viewing, game drives, and early-start excursions" in steps[3].lower()


def test_generator_preserves_generic_wording_for_unknown_destination_policy():
    brief = _brief(destination="hidden valley")
    planning_constraints = build_planning_constraints(brief)
    steps = generator.build_steps(
        "trip",
        {
            "brief": brief,
            "planning_constraints": planning_constraints,
        },
    )

    assert steps[2] == "Choose balanced transport and lodging options"
    assert steps[3] == "Select activities that balance cost and experience"
