import re

"""
Display-language helpers for Slate808.

This layer is presentation-only. It must not change planning logic,
classification, readiness, extraction, or execution behavior.
"""


def title_label(value) -> str:
    if value is None:
        return "None"

    text = str(value).strip()
    if not text:
        return "None"

    return " ".join(word[:1].upper() + word[1:] for word in text.split())


def display_trip_mood(value) -> str:
    labels = {
        "relaxed": "Relaxed",
        "adventure": "Adventure",
        "luxury": "Luxury",
        "romantic": "Romantic",
        "family": "Family",
        "corporate": "Corporate",
        "balanced": "Balanced",
    }
    if value is None:
        return "None"
    return labels.get(str(value).strip().lower(), title_label(value))


def compact_plan_step(step: str, destination: str | None = None) -> str:
    updated = str(step).strip()

    if (
        updated.startswith("Choose transport and stay options")
        and "relaxed pacing" in updated
        and "shared meeting points and aligned movement" in updated
    ):
        updated = "Choose transport and stay options with relaxed pacing and coordinated movement"

    if (
        updated.startswith("Select relaxed activities")
        and "with time for" not in updated
        and ("that keep physical effort light" in updated or "fewer activities and more recovery time" in updated)
    ):
        group = " and group-friendly pacing" if "group coordinated" in updated else ""
        updated = f"Select relaxed, light activities with quiet breaks{group}"

    if updated.startswith("Confirm the trip timing") and "relaxed rhythm" in updated and "rest between activities" in updated:
        updated = re.sub(
            r"; align bookings.*$",
            " with a relaxed rhythm, booking buffers, and rest between activities",
            updated,
        )

    if destination:
        display_destination = title_label(destination)
        raw_destination = str(destination).strip().lower()
        if raw_destination:
            updated = updated.replace(f"destination to {raw_destination}", f"destination to {display_destination}")

    return updated


def polish_display_text(text: str) -> str:
    replacements = (
        ("before locking the plan", "before the plan is finalized"),
        ("before locking the day flow", "before the day flow is finalized"),
        ("before locking stay, movement, and activity timing", "before stay, movement, and activity timing are finalized"),
        ("before finalizing rough-access or remote routing", "before rough-access or remote routing is finalized"),
        ("before finalizing the stay flow", "before the stay flow is finalized"),
        ("before final confirmation", "before confirmation"),
        ("before domestic booking", "before domestic booking confirmation"),
        ("before booking.", "before booking confirmation."),
        ("fee-category", "fee category"),
        ("vehicle-fit", "vehicle fit"),
        ("route-readiness", "route readiness"),
        ("expectation-safe", "expectation safe"),
    )

    updated = str(text)
    for old, new in replacements:
        updated = updated.replace(old, new)
    return updated
