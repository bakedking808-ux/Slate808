from engine.catalogue import CatalogueItem, FULL_CATALOGUE


def test_full_catalogue_contains_expected_family_coverage():
    families = {item.family for item in FULL_CATALOGUE}
    assert families == {
        "destination",
        "traveller",
        "timing",
        "budget",
        "intent",
        "activity",
        "transport",
        "accommodation",
        "constraints",
        "calendar",
    }


def test_full_catalogue_contains_catalogue_items_with_unique_keys():
    assert FULL_CATALOGUE
    assert all(isinstance(item, CatalogueItem) for item in FULL_CATALOGUE)
    keys = [item.key for item in FULL_CATALOGUE]
    assert len(keys) == len(set(keys))
