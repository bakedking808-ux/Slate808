import json
import re
from pathlib import Path

from engine.planning_policy import validate_planning_constraints


class ConstraintViolationError(ValueError):
    def __init__(self, violations: list[str]):
        super().__init__("Constraint violations found")
        self.violations = violations


VAGUE_WORDS = ["things", "stuff", "handle", "manage", "do something"]
WEAK_STARTERS = ["it", "this", "that", "there"]
RISKY_KEYWORDS = ["risky", "dangerous", "extreme", "bungee", "unsafe", "rough access"]
PREMIUM_KEYWORDS = ["premium", "luxury", "curated", "exclusive", "high-quality", "elevated"]
HIGH_EXERTION_KEYWORDS = ["steep hike", "steep hikes", "high exertion", "strenuous", "long trek", "long walk"]
LOUD_VENUE_KEYWORDS = ["nightlife", "club", "party", "loud venue", "bar hopping"]
ADULT_ONLY_KEYWORDS = ["adult-only", "adults-only", "late-night", "casino", "cocktail"]

PLACEHOLDER_PATTERNS = [
    r"\bas\s+the destination\b",
    r"\bas\s+the subject\b",
    r"\bas\s+the participants\b",
    r"\bas\s+the planned time\b",
    r"\bas\s+the needed items\b",
    r"\bas\s+the available budget\b",
    r"\bas\s+the target areas\b",
    r"\bfor\s+the task\b"
]


def load_rules():
    rules_path = Path(__file__).resolve().parent.parent / "rules" / "planning_rules.json"
    with open(rules_path, "r") as f:
        return json.load(f)


def is_actionable(step: str) -> bool:
    words = step.strip().split()
    if not words:
        return False

    first_word = words[0].lower()

    if first_word in WEAK_STARTERS:
        return False

    return True


def contains_placeholder(step: str) -> bool:
    step_lower = step.lower()
    return any(re.search(pattern, step_lower) for pattern in PLACEHOLDER_PATTERNS)


def is_weak_trip_destination(step: str) -> bool:
    """
    Flag trip steps that mention destination weakly, without any specific value.
    """
    step_lower = step.lower().strip()

    weak_phrases = [
        "choose the destination",
        "choose a destination",
        "pick the destination",
        "pick a destination",
        "select the destination",
        "select a destination"
    ]

    # If the step contains a stronger specific form, it is not weak
    strong_signals = [
        "as ",
        "specific destination"
    ]

    if "destination" not in step_lower:
        return False

    if any(signal in step_lower for signal in strong_signals):
        return False

    return any(phrase in step_lower for phrase in weak_phrases)


def check_task_specific_rules(plan: dict) -> list:
    """
    Check rules for supported travel planning tasks.
    """
    errors = []

    task_type = plan.get("task_type", "")
    steps = [step.lower() for step in plan.get("steps", [])]
    full_text = " ".join(steps)

    if task_type != "trip":
        return errors

    if "destination" not in full_text:
        errors.append("Trip plan must include a destination")
    elif "as the destination" in full_text:
        errors.append("Trip plan must include a specific destination")

    if "budget" not in full_text and "cost" not in full_text:
        errors.append("Trip plan must include a budget or cost step")

    if "transport" not in full_text:
        errors.append("Trip plan must include transport information")

    if "time" not in full_text and "timing" not in full_text:
        errors.append("Trip plan must include time or timing information")

    return errors


def _constraint_violations(plan: dict) -> list[str]:
    raw_planning_constraints = plan.get("planning_constraints") or {}
    if not raw_planning_constraints:
        return []

    planning_constraints = validate_planning_constraints(raw_planning_constraints).model_dump()
    constraint_policy = planning_constraints.get("constraint_policy") or {}

    steps = [step.lower() for step in plan.get("steps", [])]
    full_text = " ".join(steps)
    violations: list[str] = []

    if constraint_policy.get("family_safe") or constraint_policy.get("kids_present"):
        if any(keyword in full_text for keyword in RISKY_KEYWORDS + LOUD_VENUE_KEYWORDS + ADULT_ONLY_KEYWORDS):
            violations.append("family_safe constraints violated by risky, loud, or adult-only wording")

    if constraint_policy.get("avoid_premium"):
        if any(keyword in full_text for keyword in PREMIUM_KEYWORDS):
            violations.append("avoid_premium constraints violated by premium wording")

    if constraint_policy.get("low_mobility"):
        if any(keyword in full_text for keyword in HIGH_EXERTION_KEYWORDS):
            violations.append("low_mobility constraints violated by high-exertion wording")

    if constraint_policy.get("quiet_preferred"):
        if any(keyword in full_text for keyword in LOUD_VENUE_KEYWORDS):
            violations.append("quiet_preferred constraints violated by loud venue wording")

    if constraint_policy.get("low_risk"):
        if any(keyword in full_text for keyword in RISKY_KEYWORDS):
            violations.append("low_risk constraints violated by risky wording")

    return violations


def check_plan(plan: dict) -> dict:
    """
    Strict validation of the plan.
    """
    rules = load_rules()
    steps = plan.get("steps", [])

    errors = []

    if len(steps) < rules["min_steps"] or len(steps) > rules["max_steps"]:
        errors.append("Invalid number of steps")

    for step in steps:
        step_lower = step.lower()

        if len(step.split()) < 3:
            errors.append(f"Step too short: '{step}'")

        for word in VAGUE_WORDS:
            if word in step_lower:
                errors.append(f"Vague step detected: '{step}'")
                break

        if not is_actionable(step):
            errors.append(f"Non-actionable step: '{step}'")

    normalized_steps = [s.lower().strip() for s in steps]
    if len(normalized_steps) != len(set(normalized_steps)):
        errors.append("Duplicate steps found")

    if steps:
        first = steps[0].lower()
        if not ("understand" in first or "define" in first):
            errors.append("First step must define or understand the goal")

    if "review" in " ".join(steps).lower():
        if not steps[-1].lower().startswith("review"):
            errors.append("Review step should be last")

    for step in steps:
        if contains_placeholder(step):
            errors.append(f"Placeholder value detected: '{step}'")

    if plan.get("task_type") == "trip":
        for step in steps:
            if is_weak_trip_destination(step):
                errors.append(f"Weak trip destination step detected: '{step}'")

    errors.extend(check_task_specific_rules(plan))

    constraint_violations = _constraint_violations(plan)
    if constraint_violations:
        raise ConstraintViolationError(constraint_violations)

    if errors:
        return {
            "status": "fail",
            "errors": errors
        }

    return {
        "status": "pass",
        "errors": []
    }
