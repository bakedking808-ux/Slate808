from cross_field_validation_contract import validate_travel_brief_cross_fields
from extractor_contract import extract_catalogue_signals
from travel_brief_contract import TravelBrief, TravelBriefField, build_travel_brief


def _field(
    family: str,
    value: str | None = None,
    resolved: bool = False,
    source_keys: list[str] | None = None,
) -> TravelBriefField:
    return TravelBriefField(
        family=family,
        value=value,
        resolved=resolved,
        source_keys=source_keys or [],
    )


def _brief(**overrides) -> TravelBrief:
    brief = TravelBrief(
        destination=_field("destination", "destination_fixed", True, ["destination_fixed"]),
        traveller=_field("traveller", "family", True, ["family"]),
        timing=_field("timing", "weekend_trip", True, ["weekend_trip"]),
        budget=_field("budget"),
        intent=_field("intent"),
        activity=_field("activity"),
        transport=_field("transport"),
        accommodation=_field("accommodation"),
        constraints=_field("constraints"),
        calendar=_field("calendar"),
        missing_fields=[],
        clarification_needed=False,
        is_minimum_ready=True,
    )
    return brief.model_copy(update=overrides)


def test_clean_valid_brief():
    extraction_result = extract_catalogue_signals(
        "Plan a trip to Naivasha for 2 adults and 3 kids next weekend"
    )
    brief = build_travel_brief(extraction_result)

    result = validate_travel_brief_cross_fields(brief)

    assert result.valid is True
    assert result.violations == []
    assert result.warnings == []


def test_destination_contamination_case():
    brief = _brief(
        destination=_field("destination", "naivasha april", True, ["destination_fixed"])
    )

    result = validate_travel_brief_cross_fields(brief)

    assert result.valid is True
    assert [violation.model_dump() for violation in result.violations] == [
        {
            "field_name": "destination",
            "issue": "Destination appears to contain timing-like fragments.",
            "severity": "warning",
        }
    ]
    assert result.warnings == ["Destination appears to contain timing-like fragments."]


def test_unresolved_timing_case_fails_validation():
    brief = _brief(
        timing=_field("timing"),
        is_minimum_ready=True,
        clarification_needed=False,
    )

    result = validate_travel_brief_cross_fields(brief)

    assert result.valid is False
    assert [violation.model_dump() for violation in result.violations] == [
        {
            "field_name": "timing",
            "issue": "Timing is unresolved while downstream readiness is implied.",
            "severity": "error",
        }
    ]
    assert result.warnings == []


def test_conflicting_timing_precision_fails_validation():
    brief = _brief(
        timing=_field(
            "timing",
            "exact_date, flexible_timing",
            True,
            ["exact_date", "flexible_timing"],
        )
    )

    result = validate_travel_brief_cross_fields(brief)

    assert result.valid is False
    assert [violation.model_dump() for violation in result.violations] == [
        {
            "field_name": "timing",
            "issue": "Timing contains conflicting precision levels.",
            "severity": "error",
        }
    ]


def test_repeated_call_determinism():
    brief = _brief(
        destination=_field("destination", "naivasha april", True, ["destination_fixed"])
    )

    first = validate_travel_brief_cross_fields(brief)
    second = validate_travel_brief_cross_fields(brief)

    assert first.model_dump() == second.model_dump()
