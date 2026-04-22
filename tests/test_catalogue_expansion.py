from contracts.extractor_contract import extract_catalogue_signals
from slate808_catalogue import FULL_CATALOGUE


EXPANSION_KEYS = {
    "destination_flexible_coastal",
    "destination_flexible_beach",
    "destination_flexible_international",
    "destination_flexible_near_nairobi",
    "destination_flexible_mountain",
    "large_group",
    "team",
    "multi_generational_family",
    "timing_relative_next_week",
    "timing_relative_next_month",
    "timing_holiday_period",
    "timing_duration_short",
    "timing_month_named",
    "timing_early_month",
    "timing_first_week",
    "timing_quarter_fuzzy",
    "budget_low",
    "budget_value",
    "budget_moderate",
    "budget_premium",
    "budget_premium_reasonable",
    "romantic",
    "celebration",
    "peaceful",
    "exploratory",
    "wellness",
    "social",
}


def test_catalogue_expansion_keys_are_in_full_catalogue():
    keys = {item.key for item in FULL_CATALOGUE}

    assert EXPANSION_KEYS <= keys


def test_catalogue_expansion_preserves_unique_keys():
    keys = [item.key for item in FULL_CATALOGUE]

    assert len(keys) == len(set(keys))


def test_catalogue_expansion_represents_target_families():
    by_key = {item.key: item for item in FULL_CATALOGUE}

    assert by_key["destination_flexible_coastal"].family == "destination"
    assert by_key["large_group"].family == "traveller"
    assert by_key["timing_first_week"].family == "timing"
    assert by_key["budget_value"].family == "budget"
    assert by_key["wellness"].family == "intent"


def test_extractor_uses_new_destination_traveller_timing_budget_and_intent_phrases():
    result = extract_catalogue_signals(
        "Plan a romantic beach destination for a large group first week of May "
        "with a premium but reasonable budget"
    )

    assert "destination_flexible_beach" in result.matched_keys
    assert "large_group" in result.matched_keys
    assert "timing_first_week" in result.matched_keys
    assert "budget_premium_reasonable" in result.matched_keys
    assert "romantic" in result.matched_keys


def test_extractor_uses_new_fuzzy_timing_and_value_budget_phrases():
    result = extract_catalogue_signals(
        "Need somewhere coastal for my work team mid-year, budget-friendly and peaceful"
    )

    assert "destination_flexible_coastal" in result.matched_keys
    assert "team" in result.matched_keys
    assert "timing_quarter_fuzzy" in result.matched_keys
    assert "budget_value" in result.matched_keys
    assert "peaceful" in result.matched_keys
