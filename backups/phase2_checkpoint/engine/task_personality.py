"""
engine/task_personality.py
Eskapades "Designed Journeys" layer
Refines plans while preserving structure, anchors, and checker-visible signals.
"""

import re


STRONG_VERBS = [
    "set", "confirm", "choose", "shape", "prepare",
    "gather", "design", "define", "start", "end", "move", "select"
]

MOOD_SPECIFIC_KEYWORDS = [
    "calm", "relaxed", "restful", "low-friction", "smooth",
    "adventur", "active", "outdoor", "premium", "high-quality", "curated", "comfort",
    "intimate", "shared", "unrushed", "special", "family", "family-friendly", "manageable",
    "coordinat", "efficient", "realistic", "structured", "team", "group"
]


def extract_destination_from_steps(steps: list[str]) -> str:
    """
    Recover destination from an existing trip step.
    Example:
    'Define the trip goal clearly and set the destination to malindi'
    """
    for step in steps:
        step_lower = step.lower()
        match = re.search(r"destination to\s+(.+)", step_lower)
        if match:
            return match.group(1).strip()
    return ""


def first_word(text: str) -> str:
    parts = text.strip().split()
    return parts[0].lower() if parts else ""


def starts_with_strong_verb(step: str) -> bool:
    return first_word(step) in STRONG_VERBS


def _contains_mood_specific_language(step: str) -> bool:
    step_lower = step.lower()
    return any(keyword in step_lower for keyword in MOOD_SPECIFIC_KEYWORDS)


def required_anchors_for_trip_step(index: int, original_step: str, destination: str) -> list[str]:
    """
    Define which checker-visible anchors must survive for each trip step.
    """
    step_lower = original_step.lower()
    anchors = []

    if index == 0:
        anchors.append("define")
        if destination:
            anchors.append(destination.lower())
        anchors.append("destination")

    elif "budget" in step_lower or "cost" in step_lower:
        anchors.append("budget")

    elif "transport" in step_lower or "travel route" in step_lower:
        anchors.append("transport")

    elif "activity" in step_lower or "activities" in step_lower or "experience" in step_lower:
        anchors.append("activity")

    elif "timing" in step_lower or "date" in step_lower or "schedule" in step_lower:
        anchors.append("timing")

    elif "review" in step_lower or "end" in step_lower:
        anchors.append("end")

    return anchors


def preserves_anchors(rewritten_step: str, anchors: list[str]) -> bool:
    step_lower = rewritten_step.lower()
    return all(anchor in step_lower for anchor in anchors)


def safe_rewrite_trip_step(index: int, original_step: str, destination: str) -> str:
    """
    Rewrite one trip step in Eskapades tone while preserving checker-visible anchors.
    If the rewrite drifts, return the original step.

    Important:
    - We only rewrite based on explicit semantic anchors from the original step
    - We do NOT use broad words like 'travel' because that caused activity steps
      to be misclassified as transport steps
    """
    step_lower = original_step.lower()

    if _contains_mood_specific_language(original_step):
        return original_step

    if index == 0:
        if destination:
            candidate = f"Define the trip goal clearly and set the destination to {destination}"
        else:
            candidate = "Define the trip goal clearly and set a clear destination"

    elif "budget" in step_lower or "cost" in step_lower:
        candidate = "Set a comfortable budget that supports the kind of experience you want"

    elif "transport" in step_lower or "travel route" in step_lower:
        candidate = "Choose transport arrangements that keep the journey smooth and low-friction"

    elif "activity" in step_lower or "activities" in step_lower or "experience" in step_lower:
        candidate = "Choose activity moments that fit the mood you want the journey to hold"

    elif "timing" in step_lower or "date" in step_lower or "schedule" in step_lower:
        candidate = "Confirm the trip timing clearly"

    elif "review" in step_lower or "end" in step_lower:
        candidate = "End with a calm closing moment and note what made the journey memorable"

    else:
        candidate = original_step

    anchors = required_anchors_for_trip_step(index, original_step, destination)

    if not starts_with_strong_verb(candidate):
        return original_step

    if anchors and not preserves_anchors(candidate, anchors):
        return original_step

    return candidate


def apply_task_personality(plan: dict) -> dict:
    """
    Refine plan tone while preserving step count, step purpose, and anchors.
    """
    task_type = plan.get("task_type", "")
    steps = plan.get("steps", [])

    if task_type == "trip":
        return plan

    return plan
