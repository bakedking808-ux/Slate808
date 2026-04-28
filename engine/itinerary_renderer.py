"""
Draft itinerary renderer for Slate808.

This module creates safe, non-verified day-flow structures.
It must not invent venues, opening hours, prices, suppliers, exact travel
times, or guaranteed wildlife/activity outcomes.
"""


def _timing_state(brief: dict) -> str:
    timing = brief.get("timing") or {}
    return timing.get("state") or "missing_timing"


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

    destination_lower = str(destination).lower()
    if any(token in destination_lower for token in ("mara", "samburu", "amboseli", "tsavo", "safari", "conservancy", "park")):
        itinerary.append("- Do not guarantee wildlife sightings; confirm park, conservancy, access, and fee requirements before final confirmation.")

    return itinerary
