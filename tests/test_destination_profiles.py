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
