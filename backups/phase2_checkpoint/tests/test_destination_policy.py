from engine.planning_policy import (
    derive_destination_policy,
    derive_planning_constraints,
    normalize_destination_name,
)


def _brief(destination=None):
    return {
        "destination": destination,
        "traveller_count": 2,
        "timing": {
            "raw_text": "next weekend",
            "state": "relative_timing",
            "date_flexibility": "fixed",
            "confidence": "medium",
        },
        "budget_amount": None,
        "budget_level": "unspecified",
        "trip_mood": None,
    }


def test_destination_alias_normalization():
    assert normalize_destination_name("mount kenya") == "mt kenya"
    assert normalize_destination_name("mt kenya") == "mt kenya"
    assert normalize_destination_name("masai mara") == "maasai mara"
    assert normalize_destination_name("mara") == "maasai mara"
    assert normalize_destination_name("lake naivasha") == "naivasha"
    assert normalize_destination_name("lake nakuru") == "nakuru"
    assert normalize_destination_name("ngare dare") == "ngare ndare"


def test_coastal_destination_profile():
    policy = derive_destination_policy(_brief("diani"))

    assert policy["resolved_destination"] == "diani"
    assert policy["destination_type"] == "coastal"
    assert policy["activity_bias"] == ["beach", "water", "relaxation"]
    assert policy["transport_bias"] == "road_or_air_connection"
    assert policy["accommodation_bias"] == "resort_or_beachfront"
    assert policy["pace_bias"] == "relaxed"
    assert "heat" in policy["risk_flags"]


def test_mountain_destination_profile():
    policy = derive_destination_policy(_brief("mount kenya"))

    assert policy["resolved_destination"] == "mt kenya"
    assert policy["destination_type"] == "mountain"
    assert policy["activity_bias"] == ["hiking", "nature", "outdoor"]
    assert policy["transport_bias"] == "road_transfer"
    assert policy["accommodation_bias"] == "lodge_or_cabin"
    assert policy["pace_bias"] == "active"
    assert "altitude" in policy["risk_flags"]


def test_city_destination_profile():
    policy = derive_destination_policy(_brief("nairobi"))

    assert policy["resolved_destination"] == "nairobi"
    assert policy["destination_type"] == "city"
    assert policy["activity_bias"] == ["urban", "dining", "culture", "logistics"]
    assert policy["transport_bias"] == "urban_road_transfer"
    assert policy["accommodation_bias"] == "city_hotel"
    assert policy["pace_bias"] == "fast"
    assert "traffic" in policy["risk_flags"]


def test_safari_destination_profile():
    policy = derive_destination_policy(_brief("mara"))

    assert policy["resolved_destination"] == "maasai mara"
    assert policy["destination_type"] == "safari"
    assert policy["activity_bias"] == ["wildlife", "game_drive", "photography"]
    assert policy["transport_bias"] == "airstrip_or_4x4"
    assert policy["accommodation_bias"] == "camp_or_lodge"
    assert policy["pace_bias"] == "early_start"
    assert "distance" in policy["risk_flags"]


def test_lake_destination_profile():
    policy = derive_destination_policy(_brief("lake naivasha"))

    assert policy["resolved_destination"] == "naivasha"
    assert policy["destination_type"] == "lake"
    assert policy["activity_bias"] == ["boat", "nature", "relaxation"]
    assert policy["transport_bias"] == "road_transfer"
    assert policy["accommodation_bias"] == "lodge_or_lakeside"
    assert policy["pace_bias"] == "relaxed"
    assert "weekend_crowds" in policy["risk_flags"]


def test_forest_destination_profile():
    policy = derive_destination_policy(_brief("ngare dare"))

    assert policy["resolved_destination"] == "ngare ndare"
    assert policy["destination_type"] == "forest"
    assert policy["activity_bias"] == ["trail", "nature", "quiet"]
    assert policy["transport_bias"] == "road_transfer"
    assert policy["accommodation_bias"] == "camp_or_lodge"
    assert policy["pace_bias"] == "balanced"
    assert "distance" in policy["risk_flags"]


def test_arid_destination_profile():
    policy = derive_destination_policy(_brief("chalbi desert"))

    assert policy["resolved_destination"] == "chalbi desert"
    assert policy["destination_type"] == "arid"
    assert policy["activity_bias"] == ["rugged", "remote", "scenic"]
    assert policy["transport_bias"] == "4x4_required"
    assert policy["accommodation_bias"] == "camp"
    assert policy["pace_bias"] == "steady"
    assert "remote_access" in policy["risk_flags"]


def test_destination_policy_fallback_mixed_or_unknown():
    policy = derive_destination_policy(_brief("hidden valley"))

    assert policy == {
        "resolved_destination": "hidden valley",
        "destination_type": "mixed_or_unknown",
        "activity_bias": ["general"],
        "transport_bias": "standard",
        "accommodation_bias": "standard",
        "pace_bias": "balanced",
        "risk_flags": [],
    }


def test_destination_policy_partial_match_fallback():
    policy = derive_destination_policy(_brief("south coast diani"))

    assert policy["resolved_destination"] == "diani"
    assert policy["destination_type"] == "coastal"
    assert policy["activity_bias"] == ["beach", "water", "relaxation"]
    assert policy["transport_bias"] == "road_or_air_connection"
    assert policy["accommodation_bias"] == "resort_or_beachfront"
    assert policy["pace_bias"] == "relaxed"
    assert "heat" in policy["risk_flags"]


def test_destination_policy_fallback_handles_missing_destination():
    policy = derive_destination_policy(_brief())

    assert policy == {
        "resolved_destination": None,
        "destination_type": "mixed_or_unknown",
        "activity_bias": ["general"],
        "transport_bias": "standard",
        "accommodation_bias": "standard",
        "pace_bias": "balanced",
        "risk_flags": [],
    }


def test_derive_planning_constraints_includes_destination_policy(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    constraints = derive_planning_constraints(_brief("watamu"))

    assert "destination_policy" in constraints
    assert constraints["destination_policy"]["resolved_destination"] == "watamu"
    assert constraints["destination_policy"]["destination_type"] == "coastal"
