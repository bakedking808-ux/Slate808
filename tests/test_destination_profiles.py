from engine.destination_profiles import get_destination_profile


def test_representative_destination_profiles_include_safe_enrichment_metadata():
    expected = {
        "diani": "coastal",
        "nairobi": "urban",
        "maasai mara": "safari",
        "naivasha": "lake_rift",
        "chalbi desert": "northern_frontier",
    }

    for destination, category in expected.items():
        resolved, profile = get_destination_profile(destination)

        assert resolved == destination
        assert profile is not None
        assert profile["profile_category"] == category
        assert profile["planning_notes"]
        assert profile["verification_flags"]


def test_safari_profile_preserves_no_wildlife_guarantee_note():
    _resolved, profile = get_destination_profile("mara")

    assert profile is not None
    assert "wildlife_not_guaranteed" in profile["planning_notes"]
    assert "park_access_check" in profile["verification_flags"]
    assert "fee_category_check" in profile["verification_flags"]
    assert "vehicle_fit_check" in profile["verification_flags"]


def test_remote_arid_profile_marks_vehicle_and_local_support_review():
    _resolved, profile = get_destination_profile("chalbi desert")

    assert profile is not None
    assert "vehicle_fit_check" in profile["verification_flags"]
    assert "local_support_check" in profile["verification_flags"]
    assert "safety_conditions_review" in profile["verification_flags"]

from engine.itinerary_renderer import render_draft_itinerary


def test_safari_draft_itinerary_uses_profile_notes_without_wildlife_guarantees():
    itinerary = "\n".join(render_draft_itinerary({
        "brief": {
            "destination": "maasai mara",
            "traveller_count": 2,
            "timing": {"state": "exact_timing"},
            "trip_mood": "balanced",
        }
    }))

    assert "Profile Notes" in itinerary
    assert "Do not guarantee wildlife sightings" in itinerary
    assert "fee-category requirements" in itinerary
    assert "Confirm vehicle fit" in itinerary
    assert "Big Five guaranteed" not in itinerary


def test_coastal_draft_itinerary_uses_profile_notes():
    itinerary = "\n".join(render_draft_itinerary({
        "brief": {
            "destination": "diani",
            "traveller_count": 2,
            "timing": {"state": "exact_timing"},
            "trip_mood": "relaxed",
        }
    }))

    assert "Profile Notes" in itinerary
    assert "Review coastal weather and activity access" in itinerary
    assert "Confirm meal basis" in itinerary


def test_unknown_destination_draft_itinerary_does_not_add_profile_notes():
    itinerary = "\n".join(render_draft_itinerary({
        "brief": {
            "destination": "hidden valley",
            "traveller_count": 2,
            "timing": {"state": "exact_timing"},
            "trip_mood": "balanced",
        }
    }))

    assert "Profile Notes" not in itinerary


def test_ol_kalou_destination_profile_and_alias_resolve():
    resolved, profile = get_destination_profile("Ol Kalou")

    assert resolved == "ol kalou"
    assert profile is not None
    assert profile["destination_type"] == "highland_town"
    assert profile["profile_category"] == "highland"

    alias_resolved, alias_profile = get_destination_profile("Ol Kalau")

    assert alias_resolved == "ol kalou"
    assert alias_profile == profile
