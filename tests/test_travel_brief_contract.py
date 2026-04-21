from extractor_contract import extract_catalogue_signals
from travel_brief_contract import build_travel_brief


def test_brief_assembly_from_required_family_extraction():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )

    brief = build_travel_brief(extraction_result)

    assert brief.destination.value == "destination_fixed"
    assert brief.destination.resolved is True
    assert brief.traveller.value == "family"
    assert brief.traveller.resolved is True
    assert brief.timing.value == "weekend_trip"
    assert brief.timing.resolved is True
    assert brief.clarification_needed is False
    assert brief.is_minimum_ready is True


def test_unresolved_optional_families_remain_none():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )

    brief = build_travel_brief(extraction_result)

    assert brief.budget.value is None
    assert brief.budget.resolved is False
    assert brief.intent.value is None
    assert brief.intent.resolved is False
    assert brief.transport.value is None
    assert brief.transport.resolved is False


def test_missing_required_fields_pass_through_correctly():
    extraction_result = extract_catalogue_signals("Need a driver and a private place")

    brief = build_travel_brief(extraction_result)

    assert brief.missing_fields == ["destination", "traveller", "timing"]
    assert brief.clarification_needed is True
    assert brief.is_minimum_ready is False
    assert brief.destination.resolved is False
    assert brief.traveller.resolved is False
    assert brief.timing.resolved is False


def test_repeated_calls_are_deterministic():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )

    first = build_travel_brief(extraction_result)
    second = build_travel_brief(extraction_result)

    assert first.model_dump() == second.model_dump()


def test_multi_signal_family_aggregation_remains_stable():
    extraction_result = extract_catalogue_signals(
        "Plan Naivasha and Nakuru with kids next weekend"
    )

    brief = build_travel_brief(extraction_result)

    assert brief.destination.value == "destination_fixed, multiple_destinations"
    assert brief.destination.source_keys == [
        "destination_fixed",
        "multiple_destinations",
    ]


def test_resolved_families_helper_returns_resolved_slots_in_brief_order():
    extraction_result = extract_catalogue_signals(
        "Plan Naivasha and Nakuru for 2 adults and 3 kids with kids next weekend"
    )

    brief = build_travel_brief(extraction_result)

    assert brief.resolved_families() == [
        "destination",
        "traveller",
        "timing",
        "constraints",
    ]
