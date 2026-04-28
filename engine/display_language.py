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
