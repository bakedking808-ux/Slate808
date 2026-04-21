from clarification_state import ClarificationStateManager
from engine.clarification_runner import reset_state, run


def setup_function():
    reset_state()


def test_clarification_preserves_trip_mood_in_initial_and_completed_output():
    initial = run("Plan an adventure trip to mara for 3 people for 5 days")

    assert "- Trip Mood: adventure" in initial
    assert "What exact dates are you planning for those 5 days?" in initial

    completed = run("10-14 April")

    assert "Slate808 Output" in completed
    assert "Status: pass" in completed
    assert "- Destination: mara" in completed
    assert "- Traveller Count: 3" in completed
    assert "- Timing: 10 april to 14 april" in completed
    assert "- Trip Mood: adventure" in completed


def test_clarification_state_merge_does_not_overwrite_trip_mood_with_none():
    manager = ClarificationStateManager()
    manager.start(
        task_type="trip",
        original_input="Plan an adventure trip to mara for 3 people for 5 days",
        missing_fields=["timing"],
        collected_fields={
            "destination": "mara",
            "traveller_count": 3,
            "trip_mood": "adventure",
        },
    )

    state = manager.merge_fields({"trip_mood": None, "budget_level": "medium"})

    assert state["collected_fields"]["trip_mood"] == "adventure"
    assert state["collected_fields"]["budget_level"] == "medium"
