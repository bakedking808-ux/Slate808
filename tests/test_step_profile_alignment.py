from engine.runner import run_engine


def test_nakuru_relaxed_trip_does_not_use_coastal_or_beach_language():
    output = run_engine("Plan a relaxed trip to Nakuru for 2 people at 12th June with a budget of 20000")

    assert "- Destination: Nakuru" in output
    assert "- Trip Mood: Relaxed" in output

    forbidden = [
        "coastal",
        "beach",
        "beachfront",
        "marine",
        "water activities",
    ]

    lowered = output.lower()
    for phrase in forbidden:
        assert phrase not in lowered


def test_diani_relaxed_trip_can_use_coastal_language_from_destination_profile():
    output = run_engine("Plan a relaxed trip to Diani for 2 people 10 April to 12 April")

    lowered = output.lower()

    assert "- destination: diani" in lowered
    assert "coast" in lowered or "coastal" in lowered
    assert "relaxed activities" in lowered
