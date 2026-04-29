from engine.operational_defaults import (
    OPERATIONAL_CHECK_LABELS,
    default_operational_checks,
    default_operational_risks,
)


def test_operational_defaults_cover_all_required_labels():
    checks = default_operational_checks()

    for label in OPERATIONAL_CHECK_LABELS:
        assert any(check.startswith(f"{label}:") for check in checks)


def test_operational_defaults_return_fresh_lists():
    checks = default_operational_checks()
    risks = default_operational_risks()

    checks.append("Injected Check")
    risks.append("Injected Risk")

    assert "Injected Check" not in default_operational_checks()
    assert "Injected Risk" not in default_operational_risks()


def test_operational_defaults_include_operator_readiness_categories():
    labels = set(OPERATIONAL_CHECK_LABELS)

    assert "Supplier Readiness" in labels
    assert "Activity Readiness" in labels
    assert "Guest Comfort" in labels
    assert "Park & Access" in labels
