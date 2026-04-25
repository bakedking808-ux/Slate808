from engine.planning_policy import derive_planning_constraints
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
        "has_children": False,
    }
    brief.update(overrides)
    return brief


def _sequence(**overrides):
    return derive_planning_constraints(_brief(**overrides))["sequence_policy"]


def test_short_duration_trip_derives_compression_flag(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    policy = _sequence(
        timing=build_timing(
            raw_text="for 2 days",
            duration_days=2,
            date_flexibility="unknown",
            state="duration_only",
            confidence="medium",
        )
    )

    assert policy["short_trip_compressed"] is True
    assert "short_trip_compressed" in policy["sequence_flags"]


def test_family_trip_derives_recovery_and_light_arrival_flags(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    policy = _sequence(trip_mood="adventure", traveller_count=4, has_children=True)

    assert policy["family_recovery_pacing"] is True
    assert policy["arrival_light"] is True


def test_mountain_trip_derives_conservative_arrival_flag(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    policy = _sequence(destination="mt kenya")

    assert policy["arrival_light"] is True
    assert policy["base_first"] is True
    assert policy["activity_grouping"] == "mountain"


def test_safari_trip_derives_early_start_sequence_flag(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    policy = _sequence(destination="maasai mara")

    assert policy["early_start_activity"] is True
    assert policy["base_first"] is True
    assert policy["activity_grouping"] == "safari"


def test_city_traffic_derives_departure_buffer_flag(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    policy = _sequence(destination="nairobi")

    assert policy["departure_buffer"] is True
    assert policy["remote_daylight_movement"] is False
    assert policy["activity_grouping"] == "city"


def test_remote_arid_trip_derives_daylight_and_departure_flags(monkeypatch):
    monkeypatch.setattr("engine.planning_policy.append_log", lambda filename, line: None)

    policy = _sequence(destination="chalbi desert", traveller_count=4)

    assert policy["remote_daylight_movement"] is True
    assert policy["departure_buffer"] is True
    assert policy["base_first"] is True
    assert policy["activity_grouping"] == "arid"
