from itinerary_builder_contract import build_itinerary_plan
from itinerary_input_contract import ItineraryRequest


def _request(**overrides):
    request = {
        "destination": "destination_fixed",
        "traveller": "family",
        "timing": "weekend_trip",
        "budget": None,
        "intent": None,
        "activity": None,
        "transport": None,
        "accommodation": None,
        "constraints": None,
        "calendar": None,
        "ready": True,
    }
    request.update(overrides)
    return ItineraryRequest(**request)


def test_successful_plan_build_from_valid_request():
    plan = build_itinerary_plan(_request())

    assert plan.destination == "destination_fixed"
    assert plan.traveller == "family"
    assert plan.timing == "weekend_trip"
    assert len(plan.steps) == 5


def test_fixed_title_format():
    plan = build_itinerary_plan(_request(destination="destination_fixed"))

    assert plan.title == "Trip Plan: destination_fixed"


def test_fixed_step_ordering():
    plan = build_itinerary_plan(_request())

    assert [(step.order, step.title) for step in plan.steps] == [
        (1, "Confirm destination and trip scope"),
        (2, "Confirm traveller setup"),
        (3, "Confirm timing and schedule window"),
        (4, "Review optional preferences"),
        (5, "Prepare execution-ready itinerary"),
    ]


def test_missing_optional_field_reporting_in_required_order():
    plan = build_itinerary_plan(
        _request(
            transport="self_drive",
            calendar="calendar_check_required",
        )
    )

    assert plan.missing_optional_fields == [
        "budget",
        "intent",
        "activity",
        "accommodation",
        "constraints",
    ]


def test_assumptions_built_from_missing_optional_fields():
    plan = build_itinerary_plan(
        _request(
            budget="budget_total",
            activity="water",
        )
    )

    assert plan.assumptions == [
        "Trip intent not yet specified.",
        "Transport preference not yet specified.",
        "Accommodation preference not yet specified.",
        "Constraints not yet specified.",
        "Calendar preference not yet specified.",
    ]


def test_fail_loudly_if_request_ready_is_false():
    try:
        build_itinerary_plan(_request(ready=False))
    except ValueError as exc:
        assert str(exc) == "request.ready must be True when building itinerary plan"
    else:
        assert False, "Expected ValueError when request.ready is False"


def test_repeated_call_stability():
    first = build_itinerary_plan(_request())
    second = build_itinerary_plan(_request())

    assert first.model_dump() == second.model_dump()
