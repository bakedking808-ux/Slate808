from engine.travel_scope import classify_travel_scope
from engine.runner import run_engine


def test_travel_scope_classifies_known_kenya_destination_as_domestic():
    assert classify_travel_scope("Diani") == "domestic_kenya"
    assert classify_travel_scope("Maasai Mara") == "domestic_kenya"


def test_travel_scope_classifies_regional_destinations():
    assert classify_travel_scope("Rwanda") == "regional_cross_border"
    assert classify_travel_scope("Zanzibar") == "regional_cross_border"


def test_travel_scope_classifies_international_destinations():
    assert classify_travel_scope("Dubai") == "international"
    assert classify_travel_scope("Bali") == "international"


def test_travel_scope_unknown_for_unprofiled_destination():
    assert classify_travel_scope("Hidden Valley") == "unknown"


def test_domestic_trip_uses_domestic_document_check():
    output = run_engine("Plan a trip to Diani for 2 people 10 April to 12 April")

    assert "Travel Documents: Confirm guest identification, booking names, and any child travel documents before domestic booking." in output
    assert "passport validity" not in output.lower()


def test_international_trip_uses_international_document_check():
    output = run_engine("Plan a trip to Dubai for 2 people 10 April to 12 April")

    assert "Travel Documents: Verify passport validity, visa or eTA requirements, transit rules, health documents, insurance, and booking-name accuracy before booking." in output
    assert "Document Gap: International travel may be blocked" in output


def test_regional_trip_uses_cross_border_document_check():
    output = run_engine("Plan a trip to Rwanda for 2 people 10 April to 12 April")

    assert "Travel Documents: Verify passport, entry clearance, health, insurance, and cross-border requirements before booking." in output
    assert "Document Gap: Regional travel may be blocked" in output
