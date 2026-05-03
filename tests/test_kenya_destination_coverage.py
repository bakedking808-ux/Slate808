from engine.destination_profiles import get_destination_profile
from engine.runner import run_engine
from engine.travel_scope import classify_travel_scope


COMMON_KENYA_DESTINATIONS = [
    "Nanyuki",
    "Nyeri",
    "Kericho",
    "Eldoret",
    "Kisumu",
    "Kakamega",
    "Machakos",
    "Elementaita",
    "Lake Elementaita",
    "Lake Elemantaita",
    "Sagana",
    "Naro Moru",
    "Naro-Moru",
    "Isiolo",
    "Meru",
    "Embu",
    "Kitale",
]


def test_common_kenya_destinations_resolve_to_profiles():
    for destination in COMMON_KENYA_DESTINATIONS:
        resolved, profile = get_destination_profile(destination)

        assert resolved is not None
        assert profile is not None, destination


def test_common_kenya_destinations_classify_as_domestic():
    for destination in COMMON_KENYA_DESTINATIONS:
        assert classify_travel_scope(destination) == "domestic_kenya", destination


def test_common_kenya_destination_output_does_not_request_scope_confirmation():
    output = run_engine(
        "Plan a relaxed trip to Nanyuki for 2 people from 10 April to 12 April "
        "with a budget of 50000"
    )

    assert "confirm whether this trip is domestic or international" not in output.lower()
    assert (
        "Travel Documents: Confirm guest identification, booking names, and any child travel documents "
        "before domestic booking confirmation."
    ) in output
    assert "passport validity" not in output.lower()


def test_lake_elementaita_alias_output_does_not_request_scope_confirmation():
    output = run_engine(
        "Plan a relaxed trip to Lake Elementaita for 2 people from 10 April to 12 April "
        "with a budget of 50000"
    )

    assert "confirm whether this trip is domestic or international" not in output.lower()
    assert (
        "Travel Documents: Confirm guest identification, booking names, and any child travel documents "
        "before domestic booking confirmation."
    ) in output
    assert "passport validity" not in output.lower()
