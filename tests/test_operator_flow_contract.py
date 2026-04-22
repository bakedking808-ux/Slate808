from contracts.operator_flow_contract import classify_operator_flow


def _signal_type(text: str) -> str:
    result = classify_operator_flow(text)
    assert result.signal is not None
    return result.signal.signal_type


def test_intent_declaration_classification():
    result = classify_operator_flow("Plan a trip for me.")

    assert result.matched is True
    assert result.signal.signal_type == "intent_declaration"
    assert result.signal.normalized_text == "Plan a trip for me."
    assert result.signal.confidence == "high"


def test_information_correction_with_actually():
    assert _signal_type("Actually, make it for two people.") == "information_correction"


def test_information_correction_with_negation_and_replacement():
    assert (
        _signal_type("No, not that - I meant something relaxing.")
        == "information_correction"
    )


def test_information_supply_relative_timing_answer():
    assert _signal_type("Next month works for me.") == "information_supply"


def test_information_supply_traveller_answer():
    assert _signal_type("2 people.") == "information_supply"


def test_information_supply_budget_answer():
    assert _signal_type("I need something affordable.") == "information_supply"


def test_clarification_request_classification():
    assert _signal_type("What options do I have?") == "clarification_request"


def test_meta_instruction_ignore_prior_field():
    assert _signal_type("Ignore the earlier destination.") == "meta_instruction"


def test_meta_instruction_continue_previous_state():
    assert _signal_type("Continue from where we left off.") == "meta_instruction"


def test_goal_shift_classification():
    assert _signal_type("Let's switch to a beach trip instead.") == "goal_shift"


def test_completion_signal_classification():
    assert _signal_type("That looks good.") == "completion_signal"


def test_unknown_classification():
    result = classify_operator_flow("The sky feels very blue today.")

    assert result.matched is False
    assert result.signal.signal_type == "unknown"
    assert result.signal.confidence == "low"


def test_repeated_call_determinism():
    first = classify_operator_flow("Actually, make it for two people.")
    second = classify_operator_flow("Actually, make it for two people.")

    assert first.model_dump() == second.model_dump()
