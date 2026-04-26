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
    assert "- Destination: maasai mara" in completed
    assert "- Traveller Count: 3" in completed
    assert "- Timing: 10 april to 14 april" in completed
    assert "- Trip Mood: adventure" in completed


def test_clarification_prompts_for_trip_mood_after_hard_fields_complete():
    initial = run("Plan a trip to mara for 3 people")
    assert "What exact dates are you planning?" in initial

    mood_prompt = run("10-14 April")

    assert "What kind of trip mood should this have?" in mood_prompt
    assert "- Destination: maasai mara" in mood_prompt
    assert "- Traveller Count: 3" in mood_prompt
    assert "- Timing: 10 april to 14 april" in mood_prompt
    assert "Slate808 Output" in mood_prompt


def test_clarification_trip_mood_answer_completes_preserved_trip():
    run("Plan a trip to mara for 3 people")
    run("10-14 April")

    completed = run("relaxed")

    assert "Slate808 Output" in completed
    assert "Status: pass" in completed
    assert "- Destination: maasai mara" in completed
    assert "- Traveller Count: 3" in completed
    assert "- Timing: 10 april to 14 april" in completed
    assert "- Trip Mood: relaxed" in completed


def test_trip_mood_does_not_outrank_hard_missing_destination():
    result = run("Plan a relaxed trip for 2 people 10 April to 12 April")

    assert "Where would you like to go?" in result
    assert "What kind of trip mood should this have?" not in result


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


def test_clarification_resume_accepts_time_window_with_budget_friendly_phrase():
    run("Plan a relaxed trip to tigoni for 2 people tomorrow")

    completed = run("27th April, 10AM to 3PM, budget friendly")

    assert "Slate808 Output" in completed
    assert "Status: pass" in completed
    assert "- Destination: tigoni" in completed
    assert "- Timing: 27 april" in completed
    assert "- Budget Level: low" in completed
