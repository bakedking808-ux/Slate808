"""
engine/task_checks.py
Task-aware checks layer for Slate808
"""

from engine.travel_scope import classify_travel_scope
from engine.destination_profiles import get_destination_profile


def _trip_checks_and_risks(plan: dict) -> tuple[list[str], list[str]]:
    brief = plan.get("brief") or {}
    destination = brief.get("destination")
    travel_scope = classify_travel_scope(destination)
    _resolved_destination, destination_profile = get_destination_profile(destination)
    planning_notes = set((destination_profile or {}).get("planning_notes") or [])
    verification_flags = set((destination_profile or {}).get("verification_flags") or [])
    profile_category = (destination_profile or {}).get("profile_category")
    budget_level = brief.get("budget_level")
    trip_mood = brief.get("trip_mood")
    timing_state = ((brief.get("timing") or {}).get("state")) or "missing_timing"

    checks = [
        "Plan Integrity: Confirm destination, traveller count, timing, budget, and trip mood remain consistent across the Travel Brief and Plan Steps.",
        "Travel Documents: Confirm guest identification and booking names before booking.",
        "Transport & Stay: Confirm transport availability, route feasibility, accommodation availability, room setup, check-in window, and cancellation terms before locking the plan.",
        "Budget & Payments: Confirm the plan aligns with the stated budget, including hidden costs, peak-season surcharges, refund terms, and secure payment channels.",
        "Safety & Local Conditions: Review destination safety, weather, road conditions, local regulations, emergency contacts, and local support before final confirmation.",
        "Supplier Readiness: Verify supplier reliability, availability, cancellation terms, refund terms, payment instructions, local support, and backup options before booking.",
        "Activity Readiness: Verify activity feasibility, access requirements, age suitability, weather sensitivity, available time, and backup options before final confirmation.",
        "Guest Comfort: Verify pacing, rest windows, room setup, mobility needs, child suitability, and guest-specific comfort requirements before final confirmation.",
        "Park & Access: Verify park, conservancy, permit, residency or fee-category, vehicle, guide, and access-rule requirements before final confirmation.",
    ]
    risks = [
        "Plan Integrity Risk: Missing information, contradictions, or mismatched brief details can weaken the plan before handoff.",
        "Availability Pressure: Transport, stay, and activity options may narrow if availability is not checked early.",
        "Budget Stretch: Hidden costs, peak-season surcharges, or unclear payment terms can push the trip beyond the intended budget.",
        "Safety Exposure: Weather, road conditions, local rules, or weak emergency support can increase travel friction.",
        "Supplier Reliability Risk: Weak supplier verification can expose the trip to failed bookings, poor communication, payment errors, or limited recovery options.",
        "Activity Constraint Risk: Unchecked activity access, age limits, weather sensitivity, or weak pacing can cause cancellations, guest fatigue, or unsuitable experiences.",
        "Guest Comfort Risk: Weak pacing, poor room setup, mobility gaps, or ignored traveller needs can reduce trip quality and increase operator rework.",
        "Access Rule Risk: Missed park, conservancy, permit, fee-category, vehicle, or guide requirements can block entry or force last-minute replanning.",
    ]

    if profile_category == "safari":
        checks[6] = "Activity Readiness: Keep wildlife experiences expectation-safe; verify activity access, available time, early-start pacing, and backup options before final confirmation."
        checks[8] = "Park & Access: Verify park, conservancy, access, fee-category, vehicle-fit, guide, and access-rule requirements before final confirmation."
    elif profile_category == "coastal":
        checks[6] = "Activity Readiness: Verify coastal weather sensitivity, water or outdoor activity access, available time, and backup options before final confirmation."
        if "meal_basis_check" in planning_notes:
            checks[7] = "Guest Comfort: Confirm pacing, rest windows, room setup, meal basis, and guest-specific comfort requirements before final confirmation."
    elif profile_category == "urban":
        checks[2] = "Transport & Stay: Confirm traffic-sensitive movement windows, route feasibility, accommodation access, check-in timing, and cancellation terms before locking the plan."
    elif profile_category == "lake_rift":
        checks[6] = "Activity Readiness: Verify water activity access, weekend crowd pressure, available time, and backup options before final confirmation."
    elif profile_category == "northern_frontier":
        checks[4] = "Safety & Local Conditions: Review remote access, heat exposure, safety conditions, local regulations, emergency contacts, and local support before final confirmation."
        checks[8] = "Park & Access: Verify vehicle-fit, local support, access-rule, permit, guide, and route-readiness requirements before final confirmation."

    if "local_support_check" in verification_flags:
        checks[5] = "Supplier Readiness: Verify supplier reliability, local support, availability, cancellation terms, refund terms, payment instructions, and backup options before booking."

    if "vehicle_fit_check" in verification_flags and profile_category != "safari":
        checks[8] = "Park & Access: Verify vehicle-fit, access-rule, permit, guide, and route-readiness requirements before final confirmation."

    if travel_scope == "domestic_kenya":
        checks[1] = "Travel Documents: Confirm guest identification, booking names, and any child travel documents before domestic booking."
    elif travel_scope == "regional_cross_border":
        checks[1] = "Travel Documents: Verify passport, entry clearance, health, insurance, and cross-border requirements before booking."
        risks.append("Document Gap: Regional travel may be blocked by missing passport, entry, health, insurance, or transit requirements.")
    elif travel_scope == "international":
        checks[1] = "Travel Documents: Verify passport validity, visa or eTA requirements, transit rules, health documents, insurance, and booking-name accuracy before booking."
        risks.append("Document Gap: International travel may be blocked by passport, visa, transit, health, insurance, or entry-clearance issues.")
    else:
        checks[1] = "Travel Documents: Confirm whether this trip is domestic or international before deciding ID, passport, visa, health, or insurance checks."

    if trip_mood == "family":
        checks[0] = "Plan Integrity: Confirm the family traveller count, child suitability, pacing, and comfort needs remain consistent across the Travel Brief and Plan Steps."
        risks[0] = "Plan Integrity Risk: The plan may become too complex if family-safe pacing and child suitability are not preserved."
    elif trip_mood == "corporate":
        checks[0] = "Plan Integrity: Confirm group coordination, meeting points, timing, and shared movement remain consistent across the Travel Brief and Plan Steps."
        risks[0] = "Plan Integrity Risk: Group coordination can slip if meeting points, timing, and shared movement are not confirmed early."
    elif trip_mood == "relaxed":
        checks[0] = "Plan Integrity: Confirm the trip pace, rest windows, and activity load remain aligned with the relaxed travel mood."
        risks[0] = "Plan Integrity Risk: Overscheduling can undercut the slower pace the trip needs."
    elif trip_mood == "luxury":
        checks[0] = "Plan Integrity: Confirm transport, stay, and experience choices remain aligned with the premium trip mood."
        risks[0] = "Plan Integrity Risk: Premium experiences may lose quality if key bookings are confirmed too late."

    if budget_level == "low":
        checks[3] = "Budget & Payments: Confirm lower-cost transport, stay, and activity choices remain practical, secure, and consistent with the stated budget."
        risks[2] = "Budget Stretch: Lower-cost options may narrow quickly if bookings are left too late."
    elif budget_level == "high":
        checks[3] = "Budget & Payments: Confirm premium spending maps cleanly to the trip priorities, supplier quality, refund terms, and secure payment channels."
        risks[2] = "Budget Stretch: Premium bookings may require early confirmation to avoid last-minute compromises."
    elif budget_level == "unspecified":
        checks[3] = "Budget & Payments: Confirm the working budget, hidden costs, refund terms, and payment method before supplier shortlisting."
        risks[2] = "Budget Stretch: Costs may drift quickly while the budget remains unspecified."

    if timing_state != "exact_timing":
        checks[2] = "Transport & Stay: Keep transport, accommodation, and transfer decisions provisional until exact travel dates are confirmed."
        risks[1] = "Availability Pressure: Bookings may remain provisional until exact travel dates are confirmed."

    return checks, risks


def apply_task_checks(plan: dict) -> dict:
    """
    Replace generic checks with task-relevant checks.
    """

    task_type = plan.get("task_type", "")

    if task_type == "trip":
        plan["checks"], plan["risks"] = _trip_checks_and_risks(plan)

    elif task_type == "study":
        plan["checks"] = [
            "The study plan should include a clear subject and realistic duration",
            "Materials should be prepared before the study session begins",
            "The session should stay focused without feeling overloaded",
            "The ending should include a short review of what was learned"
        ]

    elif task_type == "meeting":
        plan["checks"] = [
            "The meeting should include the right participants and a clear purpose",
            "Timing should be realistic and easy to follow",
            "Discussion points should stay focused and relevant",
            "The meeting should close with clear next steps"
        ]

    elif task_type == "shopping":
        plan["checks"] = [
            "The shopping plan should include the needed items and a clear budget",
            "Store choices should be practical and easy to access",
            "The trip should avoid unnecessary back-and-forth movement",
            "The final list should feel complete without excess"
        ]

    elif task_type == "cleaning":
        plan["checks"] = [
            "The cleaning plan should clearly identify the target areas",
            "Tools and supplies should be ready before starting",
            "The work should move in a logical and efficient sequence",
            "The final result should feel complete and easy to maintain"
        ]

    else:
        plan["checks"] = [
            "The goal should be clear and easy to act on",
            "The steps should remain logical and manageable",
            "Resources and preparation should be considered before execution",
            "The ending should include a simple review or closing step"
        ]

    return plan
