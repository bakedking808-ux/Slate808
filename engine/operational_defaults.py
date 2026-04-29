"""
Shared operational check and risk defaults for Slate808.

This module is presentation-neutral planning support.
It must not inspect briefs, profiles, mood, timing, budget, or destination.
"""

OPERATIONAL_CHECK_LABELS = (
    "Plan Integrity",
    "Travel Documents",
    "Transport & Stay",
    "Budget & Payments",
    "Safety & Local Conditions",
    "Supplier Readiness",
    "Activity Readiness",
    "Guest Comfort",
    "Park & Access",
)


def default_operational_checks() -> list[str]:
    return [
        "Plan Integrity: Confirm destination, traveller count, timing, budget, and trip mood remain consistent across the Travel Brief and Plan Steps.",
        "Travel Documents: Confirm guest identification, booking names, and any passport, visa, entry, health, or insurance requirements before booking.",
        "Transport & Stay: Confirm transport availability, route feasibility, accommodation availability, room setup, check-in window, and cancellation terms before locking the plan.",
        "Budget & Payments: Confirm the plan aligns with the stated budget, including hidden costs, peak-season surcharges, refund terms, and secure payment channels.",
        "Safety & Local Conditions: Review destination safety, weather, road conditions, local regulations, emergency contacts, and local support before final confirmation.",
        "Supplier Readiness: Verify supplier reliability, availability, cancellation terms, refund terms, payment instructions, local support, and backup options before booking.",
        "Activity Readiness: Verify activity feasibility, access requirements, age suitability, weather sensitivity, available time, and backup options before final confirmation.",
        "Guest Comfort: Verify pacing, rest windows, room setup, mobility needs, child suitability, and guest-specific comfort requirements before final confirmation.",
        "Park & Access: Verify park, conservancy, permit, residency or fee-category, vehicle, guide, and access-rule requirements before final confirmation.",
    ]


def default_operational_risks() -> list[str]:
    return [
        "Plan Integrity Risk: Missing information, contradictions, or mismatched brief details can weaken the plan before handoff.",
        "Availability Pressure: Transport, stay, and activity options may narrow if availability is not checked early.",
        "Budget Stretch: Hidden costs, peak-season surcharges, or unclear payment terms can push the trip beyond the intended budget.",
        "Safety Exposure: Weather, road conditions, local rules, or weak emergency support can increase travel friction.",
        "Supplier Reliability Risk: Weak supplier verification can expose the trip to failed bookings, poor communication, payment errors, or limited recovery options.",
        "Activity Constraint Risk: Unchecked activity access, age limits, weather sensitivity, or weak pacing can cause cancellations, guest fatigue, or unsuitable experiences.",
        "Guest Comfort Risk: Weak pacing, poor room setup, mobility gaps, or ignored traveller needs can reduce trip quality and increase operator rework.",
        "Access Rule Risk: Missed park, conservancy, permit, fee-category, vehicle, or guide requirements can block entry or force last-minute replanning.",
    ]
