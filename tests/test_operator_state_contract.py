from operator_flow_contract import classify_operator_flow
from operator_state_contract import interpret_operator_state


def _action(text: str):
    result = interpret_operator_state(classify_operator_flow(text))
    assert result.action is not None
    return result.action


def test_information_correction_maps_to_replace_field():
    action = _action("Actually, make it for two people.")

    assert action.action == "replace_field"
    assert action.reset_required is False
    assert action.resume_allowed is True


def test_information_supply_maps_to_supply_field():
    action = _action("Next month works for me.")

    assert action.action == "supply_field"
    assert action.reset_required is False
    assert action.resume_allowed is True


def test_clarification_request_maps_to_request_options():
    action = _action("What options do I have?")

    assert action.action == "request_options"
    assert action.resume_allowed is True


def test_meta_continuation_maps_to_resume_previous():
    action = _action("Continue from where we left off.")

    assert action.action == "resume_previous"
    assert action.reset_required is False
    assert action.resume_allowed is True


def test_meta_reset_maps_to_reset_scope():
    action = _action("Start over.")

    assert action.action == "reset_scope"
    assert action.reset_required is True
    assert action.resume_allowed is False


def test_goal_shift_maps_to_shift_goal():
    action = _action("Let's switch to a beach trip instead.")

    assert action.action == "shift_goal"
    assert action.reset_required is True
    assert action.resume_allowed is False


def test_completion_signal_maps_to_complete_flow():
    action = _action("That looks good.")

    assert action.action == "complete_flow"
    assert action.reset_required is False
    assert action.resume_allowed is False


def test_unknown_signal_has_no_state_action():
    result = interpret_operator_state(classify_operator_flow("The sky is blue today."))

    assert result.matched is False
    assert result.action is None


def test_correction_of_traveller_count_sets_target_field():
    action = _action("Actually, make it for two people.")

    assert action.target_field == "traveller_count"


def test_meta_instruction_targeting_destination_sets_target_field():
    result = interpret_operator_state(
        classify_operator_flow("Ignore the earlier destination.")
    )

    assert result.matched is True
    assert result.action.action == "none"
    assert result.action.target_field == "destination"
    assert result.warnings == ["Meta instruction recognized but not actionable in v1."]


def test_repeated_call_determinism():
    first = interpret_operator_state(
        classify_operator_flow("Actually, make it for two people.")
    )
    second = interpret_operator_state(
        classify_operator_flow("Actually, make it for two people.")
    )

    assert first.model_dump() == second.model_dump()
