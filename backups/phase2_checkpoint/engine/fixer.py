"""
engine/fixer.py
Slate808 — Controlled Repair Layer
Architecture: checker errors -> canonical codes -> repair registry -> clean execution
"""

from typing import Callable


ERROR_PATTERNS: dict[str, list[str]] = {
    "MISSING_GOAL": [
        "first step must define or understand the goal",
    ],
    "MISSING_TRANSPORT": [
        "trip plan must include transport information",
    ],
    "MISSING_BUDGET": [
        "trip plan must include a budget or cost step",
    ],
    "MISSING_TIMING": [
        "trip plan must include time or timing information",
    ],
    "MISSING_DESTINATION": [
        "trip plan must include a destination",
        "trip plan must include a specific destination",
        "weak trip destination step detected",
    ],
    "MISSING_STUDY_SUBJECT": [
        "study plan must include a specific subject or topic",
        "study plan must include a subject or topic",
    ],
    "DUPLICATE_STEPS": [
        "duplicate steps found",
    ],
    "WRONG_ORDER": [
        "review step should be last",
    ],
}


def normalize_errors(errors: list[str]) -> set[str]:
    """
    Convert raw checker errors into canonical repair codes.
    """
    codes = set()
    for error in errors:
        error_lower = error.lower()
        for code, patterns in ERROR_PATTERNS.items():
            if any(pattern in error_lower for pattern in patterns):
                codes.add(code)
    return codes


def steps_contain(steps: list[str], *keywords: str) -> bool:
    text = " ".join(steps).lower()
    return any(keyword.lower() in text for keyword in keywords)


def deduplicate_steps(steps: list[str]) -> tuple[list[str], list[str]]:
    seen = set()
    unique = []
    removed = []

    for step in steps:
        key = step.strip().lower()
        if key not in seen:
            unique.append(step)
            seen.add(key)
        else:
            removed.append(step)

    return unique, removed


def extract_destination(goal: str) -> str:
    """
    Pull destination from goal text, but keep it conservative.
    Example:
        'Plan a trip to coast' -> 'coast'
    """
    goal_lower = goal.lower().strip()

    for marker in ["to the ", "to "]:
        if marker in goal_lower:
            return goal_lower.split(marker, 1)[-1].strip()

    return ""


RepairFn = Callable[[dict], tuple[dict, str]]


def repair_trip_goal_step(plan: dict) -> tuple[dict, str]:
    steps = plan.get("steps", [])
    goal = plan.get("goal", "")
    destination = extract_destination(goal)

    if not steps:
        if destination:
            steps.append(f"Define the trip goal clearly and set the destination to {destination}")
            action = f"Inserted first step with destination '{destination}'"
        else:
            steps.append("Define the trip goal clearly and set a specific destination")
            action = "Inserted first step with generic destination"
    else:
        if destination:
            steps[0] = f"Define the trip goal clearly and set the destination to {destination}"
            action = f"Repaired first trip step using destination '{destination}'"
        else:
            steps[0] = "Define the trip goal clearly and set a specific destination"
            action = "Repaired first trip step with generic destination"

    plan["steps"] = steps
    return plan, action


def repair_trip_budget(plan: dict) -> tuple[dict, str]:
    steps = plan.get("steps", [])

    if not steps_contain(steps, "budget", "cost"):
        insert_at = 1 if len(steps) >= 1 else len(steps)
        steps.insert(insert_at, "Set a budget and estimate the main costs")
        action = "Added missing budget step"
    else:
        action = "Budget step already present"

    plan["steps"] = steps
    return plan, action


def repair_trip_timing(plan: dict) -> tuple[dict, str]:
    steps = plan.get("steps", [])

    if not steps_contain(steps, "time", "timing", "date", "dates", "schedule", "duration", "next week", "tomorrow", "today"):
        insert_at = 3 if len(steps) >= 3 else len(steps)
        steps.insert(insert_at, "Define travel timing and dates clearly")
        action = "Added missing timing step"
    else:
        action = "Timing step already present"

    plan["steps"] = steps
    return plan, action


def repair_trip_transport(plan: dict) -> tuple[dict, str]:
    steps = plan.get("steps", [])

    if not steps_contain(steps, "transport", "flight", "bus", "train", "drive", "travel route"):
        insert_at = 3 if len(steps) >= 3 else len(steps)
        steps.insert(insert_at, "Arrange transportation and confirm the travel route")
        action = "Added missing transport step"
    else:
        action = "Transport step already present"

    plan["steps"] = steps
    return plan, action


def repair_study_subject(plan: dict) -> tuple[dict, str]:
    steps = plan.get("steps", [])

    if not steps:
        steps.append("Define the study goal clearly and choose a specific subject")
        action = "Inserted study subject step"
    else:
        steps[0] = "Define the study goal clearly and choose a specific subject"
        action = "Repaired weak study subject step"

    plan["steps"] = steps
    return plan, action


def repair_wrong_order(plan: dict) -> tuple[dict, str]:
    """
    If a review step exists but is not last, move it to the end.
    """
    steps = plan.get("steps", [])
    review_index = None

    for i, step in enumerate(steps):
        if step.lower().startswith("review"):
            review_index = i
            break

    if review_index is not None and review_index != len(steps) - 1:
        review_step = steps.pop(review_index)
        steps.append(review_step)
        action = "Moved review step to the end"
    else:
        action = "Step order already acceptable"

    plan["steps"] = steps
    return plan, action


REPAIR_REGISTRY: dict[str, dict[str, RepairFn]] = {
    "trip": {
        "MISSING_GOAL": repair_trip_goal_step,
        "MISSING_DESTINATION": repair_trip_goal_step,
        "MISSING_BUDGET": repair_trip_budget,
        "MISSING_TIMING": repair_trip_timing,
        "MISSING_TRANSPORT": repair_trip_transport,
        "WRONG_ORDER": repair_wrong_order,
    },
    "study": {
        "MISSING_STUDY_SUBJECT": repair_study_subject,
        "WRONG_ORDER": repair_wrong_order,
    },
    "generic": {
        "WRONG_ORDER": repair_wrong_order,
    },
}


def fix_plan(plan: dict, errors: list[str]) -> tuple[dict, list[str]]:
    """
    Repair a plan based on checker errors.
    """
    task_type = plan.get("task_type", "generic")
    error_codes = normalize_errors(errors)
    registry = REPAIR_REGISTRY.get(task_type, REPAIR_REGISTRY["generic"])
    fixer_actions = []

    for code in error_codes:
        if code in registry:
            plan, action = registry[code](plan)
            fixer_actions.append(f"[{code}] {action}")
        else:
            fixer_actions.append(f"[{code}] No repair registered — skipped")

    steps = plan.get("steps", [])
    deduped_steps, removed_steps = deduplicate_steps(steps)
    plan["steps"] = deduped_steps

    for step in removed_steps:
        fixer_actions.append(f"[DUPLICATE_STEPS] Removed duplicate step: '{step}'")

    return plan, fixer_actions
