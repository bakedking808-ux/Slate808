from extractor_contract import extract_catalogue_signals


def test_exact_destination_extraction():
    result = extract_catalogue_signals("Plan a trip to Naivasha")

    assert "destination_fixed" in result.matched_keys
    assert any(signal.family == "destination" for signal in result.signals)


def test_traveller_extraction():
    result = extract_catalogue_signals("Plan a trip for 2 adults and 3 kids")

    assert "family" in result.matched_keys
    assert any(signal.family == "traveller" for signal in result.signals)


def test_timing_extraction():
    result = extract_catalogue_signals("Plan a trip next weekend")

    assert "weekend_trip" in result.matched_keys
    assert any(signal.family == "timing" for signal in result.signals)


def test_missing_required_field_detection():
    result = extract_catalogue_signals("Plan something relaxing with a driver")

    assert result.missing_fields == ["destination", "traveller", "timing"]
    assert result.clarification_needed is True


def test_duplicate_key_prevention_in_output():
    result = extract_catalogue_signals("Naivasha Naivasha next weekend next weekend")

    assert result.matched_keys.count("destination_fixed") == 1
    assert result.matched_keys.count("weekend_trip") == 1


def test_repeated_calls_are_deterministic():
    user_input = "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"

    first = extract_catalogue_signals(user_input)
    second = extract_catalogue_signals(user_input)

    assert first.model_dump() == second.model_dump()
    assert "destination_fixed" in first.matched_keys
    assert "family" in first.matched_keys
    assert "weekend_trip" in first.matched_keys
    assert "budget_total" not in first.matched_keys
    assert first.clarification_needed is False
