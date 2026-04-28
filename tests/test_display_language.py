from engine.runner import run_engine


def test_trip_mood_display_is_human_readable():
    output = run_engine("Plan a relaxed trip to Diani for 2 people 10 April to 12 April")

    assert "- Trip Mood: Relaxed" in output
    assert "- Trip Mood: relaxed" not in output


def test_display_language_polishes_confirmation_wording_without_changing_categories():
    output = run_engine("Plan a safari trip to Maasai Mara for 2 people 10 April to 12 April")

    assert "Activity Readiness:" in output
    assert "Park & Access:" in output
    assert "expectation safe" in output
    assert "fee category" in output
    assert "vehicle fit" in output
    assert "expectation-safe" not in output
    assert "fee-category" not in output
    assert "vehicle-fit" not in output


def test_draft_itinerary_profile_notes_label_is_punctuated():
    output = run_engine("Plan a safari trip to Maasai Mara for 2 people 10 April to 12 April")

    assert "Profile Notes:" in output
    assert "Profile Notes\n" not in output
