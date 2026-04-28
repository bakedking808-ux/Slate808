"""
Draft itinerary renderer for Slate808.

This module creates safe, non-verified day-flow structures.
It must not invent venues, opening hours, prices, suppliers, exact travel
times, or guaranteed wildlife/activity outcomes.
"""

from engine.destination_profiles import get_destination_profile


def _timing_state(brief: dict) -> str:
    timing = brief.get("timing") or {}
    return timing.get("state") or "missing_timing"


def _profile_itinerary_notes(profile: dict | None) -> list[str]:
    if not profile:
        return []

    planning_notes = set(profile.get("planning_notes") or [])
    verification_flags = set(profile.get("verification_flags") or [])
    notes = []

    if "route_cushion" in planning_notes:
        notes.append("- Keep a route cushion visible before confirming movement between stay, activities, and departure.")

    if "coastal_weather_review" in planning_notes:
        notes.append("- Review coastal weather and activity access before confirming outdoor or water-based experiences.")

    if "traffic_review" in planning_notes:
        notes.append("- Review traffic-sensitive movement windows before locking the day flow.")

    if "remote_access_review" in planning_notes:
        notes.append("- Treat remote access as a verification item before confirming the route.")

    if "early_start_pacing" in planning_notes:
        notes.append("- Keep early-start pacing visible without overpacking the day.")

    if "weekend_crowd_review" in planning_notes:
        notes.append("- Review weekend crowd pressure before locking stay, movement, and activity timing.")

    if "water_activity_review" in planning_notes:
        notes.append("- Confirm water activity access and suitability before final confirmation.")

    if "wildlife_not_guaranteed" in planning_notes:
        notes.append("- Do not guarantee wildlife sightings; keep safari experiences conditional and expectation-safe.")

    if "park_access_check" in verification_flags or "fee_category_check" in verification_flags:
        notes.append("- Verify park, conservancy, access, and fee-category requirements before final confirmation.")

    if "vehicle_fit_check" in verification_flags:
        notes.append("- Confirm vehicle fit before finalizing rough-access or remote routing.")

    if "local_support_check" in verification_flags:
        notes.append("- Confirm local support availability before confirming the day flow.")

    if "safety_conditions_review" in verification_flags:
        notes.append("- Review safety conditions before confirming remote or low-support routing.")

    if "meal_basis_check" in planning_notes:
        notes.append("- Confirm meal basis before finalizing the stay flow.")

    return notes


def should_render_draft_itinerary(final_output: dict) -> bool:
    if final_output.get("clarification_needed"):
        return False

    if final_output.get("task_type") != "trip":
        return False

    brief = final_output.get("brief") or {}
    if not brief.get("destination"):
        return False
    if not brief.get("traveller_count"):
        return False

    timing_state = _timing_state(brief)
    return timing_state not in {"missing_timing", "ambiguous_timing", "vague_timing"}


def render_draft_itinerary(final_output: dict) -> list[str]:
    brief = final_output.get("brief") or {}
    destination = brief.get("destination") or "the destination"
    trip_mood = brief.get("trip_mood") or "balanced"
    timing_state = _timing_state(brief)

    itinerary = [
        "Day 1 — Arrival Ease",
        "- Arrive, transfer to the stay, and keep the first movement light.",
        "- Confirm the route cushion before locking the arrival flow.",
        "- Add a meal moment and open time to settle in.",
        "",
        "Day 2 — Main Experience",
        f"- Hold the main {trip_mood} experience around the destination without naming unverified venues.",
        "- Keep a rest window so the day does not become overpacked.",
        "- Add an optional experience only after transport, access, and timing are checked.",
        "",
        "Final Day — Departure Ease",
        "- Keep checkout, return movement, and guest communication clear.",
        "- Leave a route cushion before departure or onward travel.",
    ]

    if timing_state != "exact_timing":
        itinerary.append("- Treat this as a draft day flow until exact dates are confirmed.")

    _resolved_destination, profile = get_destination_profile(destination)
    profile_notes = _profile_itinerary_notes(profile)
    if profile_notes:
        itinerary.append("")
        itinerary.append("Profile Notes:")
        itinerary.extend(profile_notes)

    return itinerary
