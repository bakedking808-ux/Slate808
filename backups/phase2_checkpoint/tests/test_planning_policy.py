from engine.planning_policy import (
    derive_budget_policy,
    derive_mood_policy,
    derive_planning_constraints,
    derive_timing_policy,
    derive_traveller_policy,
)
from engine.travel_brief import build_timing


def _brief(**overrides):
    brief = {
        "destination": "diani",
        "traveller_count": 2,
        "timing": build_timing(),
        "budget_amount": None,
        "budget_level": "unspecified",
        "trip_mood": None,
    }
    brief.update(overrides)
    return brief


def test_budget_policy_low_medium_high_and_unspecified_cases():
    low = derive_budget_policy(_brief(budget_amount=20000, budget_level="low"))
    medium = derive_budget_policy(_brief(budget_amount=45000, budget_level="medium"))
    high = derive_budget_policy(_brief(budget_amount=250000, budget_level="high"))
    unspecified = derive_budget_policy(_brief())

    assert low["budget_posture"] == "cost_sensitive"
    assert low["should_prioritize_value"] is True
    assert low["should_avoid_premium"] is True

    assert medium["budget_posture"] == "balanced"
    assert medium["should_require_cost_check"] is True
    assert medium["should_allow_premium"] is False

    assert high["budget_posture"] == "premium"
    assert high["should_allow_premium"] is True
    assert high["should_avoid_premium"] is False

    assert unspecified["budget_posture"] == "unknown"
    assert unspecified["is_budget_known"] is False
    assert unspecified["should_require_cost_check"] is True


def test_numeric_budget_thresholds_drive_high_posture_and_constraints():
    constraints = derive_planning_constraints(
        _brief(budget_amount=100001, budget_level="medium")
    )

    assert constraints["budget_policy"]["budget_posture"] == "premium"
    assert constraints["constraint_policy"]["avoid_premium"] is False
    assert constraints["constraint_policy"]["value_focused"] is False


def test_traveller_policy_solo_pair_family_corporate_team_and_large_group():
    solo = derive_traveller_policy(_brief(traveller_count=1))
    pair = derive_traveller_policy(_brief(traveller_count=2))
    family = derive_traveller_policy(_brief(traveller_count=4, trip_mood="family"))
    corporate_team = derive_traveller_policy(_brief(traveller_count=10, trip_mood="corporate"))
    large_group = derive_traveller_policy(_brief(traveller_count=8))

    assert solo["group_type"] == "solo"
    assert solo["needs_group_coordination"] is False

    assert pair["group_type"] == "pair"
    assert pair["needs_group_coordination"] is False

    assert family["group_type"] == "family"
    assert family["needs_family_safe_planning"] is True
    assert family["needs_group_coordination"] is True
    assert family["should_reduce_complexity"] is True

    assert corporate_team["group_type"] == "team"
    assert corporate_team["needs_group_coordination"] is True
    assert corporate_team["should_reduce_complexity"] is True

    assert large_group["group_type"] == "large_group"
    assert large_group["needs_group_coordination"] is True
    assert large_group["should_reduce_complexity"] is True


def test_mood_policy_supported_moods_and_default_case():
    relaxed = derive_mood_policy(_brief(trip_mood="relaxed"))
    adventure = derive_mood_policy(_brief(trip_mood="adventure"))
    luxury = derive_mood_policy(_brief(trip_mood="luxury"))
    romantic = derive_mood_policy(_brief(trip_mood="romantic"))
    family = derive_mood_policy(_brief(trip_mood="family"))
    corporate = derive_mood_policy(_brief(trip_mood="corporate"))
    no_mood = derive_mood_policy(_brief())

    assert relaxed["transport_style"] == "smooth"
    assert "restful" in relaxed["preferred_activity_tags"]

    assert adventure["transport_style"] == "mobile"
    assert "adventure" in adventure["preferred_activity_tags"]

    assert luxury["transport_style"] == "premium"
    assert "premium" in luxury["preferred_activity_tags"]

    assert romantic["experience_style"] == "shared"
    assert "intimate" in romantic["preferred_activity_tags"]

    assert family["experience_style"] == "family_safe"
    assert "safe" in family["preferred_activity_tags"]

    assert corporate["pace"] == "efficient"
    assert "team" in corporate["preferred_activity_tags"]

    assert no_mood["trip_mood"] is None
    assert no_mood["preferred_activity_tags"] == []
    assert no_mood["transport_style"] == "standard"


def test_timing_policy_exact_relative_duration_month_and_missing_cases():
    exact = derive_timing_policy(
        _brief(
            timing=build_timing(
                raw_text="10 april to 14 april",
                start_date="10 april",
                end_date="14 april",
                date_flexibility="fixed",
                state="exact_timing",
                confidence="high",
            )
        )
    )
    relative = derive_timing_policy(
        _brief(
            timing=build_timing(
                raw_text="next weekend",
                date_flexibility="fixed",
                state="relative_timing",
                confidence="medium",
            )
        )
    )
    duration = derive_timing_policy(
        _brief(
            timing=build_timing(
                raw_text="2 nights",
                duration_nights=2,
                date_flexibility="unknown",
                state="duration_only",
                confidence="medium",
            )
        )
    )
    month = derive_timing_policy(
        _brief(
            timing=build_timing(
                raw_text="april",
                date_flexibility="flexible",
                state="month_only",
                confidence="low",
            )
        )
    )
    missing = derive_timing_policy(_brief())

    assert exact["is_exact_timing"] is True
    assert exact["timing_specificity"] == "high"
    assert exact["should_generate_concrete_plan"] is True

    assert relative["is_relative_timing"] is True
    assert relative["timing_summary"] == "next weekend"
    assert relative["planning_confidence"] == "medium"

    assert duration["is_duration_only"] is True
    assert duration["should_anchor_to_duration"] is True
    assert duration["timing_specificity"] == "medium"
    assert duration["is_timing_usable"] is False
    assert duration["should_generate_concrete_plan"] is False

    assert month["is_month_only"] is True
    assert month["should_request_dates_within_month"] is True
    assert month["should_treat_as_provisional"] is True
    assert month["is_timing_usable"] is False
    assert month["should_generate_concrete_plan"] is False

    assert missing["timing_state"] == "missing_timing"
    assert missing["is_timing_usable"] is False
    assert missing["should_generate_concrete_plan"] is False


def test_global_flags_cover_budget_constrained_family_safe_coordination_and_provisional_timing(monkeypatch):
    logged = []
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: logged.append((filename, line)))

    family_constraints = derive_planning_constraints(
        _brief(
            traveller_count=4,
            trip_mood="family",
            budget_amount=20000,
            budget_level="low",
            timing=build_timing(
                raw_text="april",
                date_flexibility="flexible",
                state="month_only",
                confidence="low",
            ),
        )
    )

    corporate_constraints = derive_planning_constraints(
        _brief(
            traveller_count=10,
            trip_mood="corporate",
            budget_amount=180000,
            budget_level="high",
            timing=build_timing(
                raw_text="next weekend",
                date_flexibility="fixed",
                state="relative_timing",
                confidence="medium",
            ),
        )
    )

    family_flags = family_constraints["global_flags"]
    corporate_flags = corporate_constraints["global_flags"]

    assert family_flags["is_budget_constrained"] is True
    assert family_flags["requires_safe_activity_filter"] is True
    assert family_flags["requires_coordination_bias"] is True
    assert "family_safe" in family_flags["constraints"]
    assert "provisional_timing" in family_flags["constraints"]

    assert corporate_flags["requires_coordination_bias"] is True
    assert "group_coordination" in corporate_flags["constraints"]
    assert "team_structure" in corporate_flags["constraints"]
    assert corporate_flags["is_timing_strong"] is True

    assert logged
    assert logged[0][0] == "decisions.log"
