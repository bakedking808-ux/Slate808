from engine.runner import run_engine


def test_safari_trip_checks_use_profile_metadata():
    output = run_engine("Plan a safari trip to Maasai Mara for 2 people 10 April to 12 April")

    assert "Activity Readiness: Keep wildlife experiences expectation-safe" in output
    assert "Park & Access: Verify park, conservancy, access, fee-category, vehicle-fit, guide, and access-rule requirements" in output
    assert "wildlife guaranteed" not in output.lower()


def test_coastal_trip_checks_use_profile_metadata():
    output = run_engine("Plan a relaxed trip to Diani for 2 people 10 April to 12 April")

    assert "Activity Readiness: Verify coastal weather sensitivity, water or outdoor activity access" in output
    assert "Guest Comfort: Confirm pacing, rest windows, room setup, meal basis" in output


def test_urban_trip_checks_use_profile_metadata():
    output = run_engine("Plan a trip to Nairobi for 2 people 10 April to 12 April")

    assert "Transport & Stay: Confirm traffic-sensitive movement windows" in output


def test_northern_frontier_trip_checks_use_profile_metadata():
    output = run_engine("Plan a trip to Chalbi Desert for 2 people 10 April to 12 April")

    assert "Safety & Local Conditions: Remote-access logistics should be confirmed before committing to the route" in output
    assert "Supplier Readiness: Verify supplier reliability, local support" in output
    assert "Park & Access: Verify vehicle-fit, access-rule, permit, guide, and route-readiness requirements" in output
