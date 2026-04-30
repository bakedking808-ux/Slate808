from engine.display_language import compact_plan_step
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


def test_compact_plan_step_applies_destination_display_casing():
    step = compact_plan_step(
        "Define the trip goal clearly and set the destination to ol kalau",
        destination="ol kalau",
    )

    assert "destination to Ol Kalau" in step
    assert "destination to ol kalau" not in step


def test_compact_plan_step_bounds_relaxed_transport_and_activity_suffixes():
    transport = compact_plan_step(
        "Choose transport and stay options with simple transfers and relaxed pacing; "
        "shared meeting points and aligned movement; keeping transfers easy and low-strain"
    )
    activity = compact_plan_step(
        "Select relaxed activities that leave room for light pacing, quiet breaks, and recovery "
        "with calm, practical choices; logistics that keep the group coordinated; "
        "that keep physical effort light; in quieter settings; fewer activities and more recovery time"
    )

    assert transport.count(";") == 0
    assert " with " not in transport.lower().split(" with ", 1)[-1]
    assert "that keep physical effort light; in quieter settings" not in activity.lower()
    assert "fewer activities and more recovery time" not in activity.lower()


def test_compact_plan_step_bounds_relaxed_timing_suffixes():
    step = compact_plan_step(
        "Confirm the trip timing by setting the travel date as 22 june; align bookings "
        "with heat-aware booking buffers and a relaxed rhythm while confirming the shared schedule "
        "for the group; keep enough room for rest between activities"
    )

    assert step.count(";") == 0
    assert "relaxed rhythm" in step.lower()
    assert "rest between activities" in step.lower()
    assert "shared schedule for the group; keep enough room" not in step.lower()
