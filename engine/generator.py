import re
import uuid

from engine.goal_normalizer import normalize_goal
from engine.planning_policy import build_planning_constraints, validate_planning_constraints
import engine.travel_brief as travel_brief
from engine.travel_brief import MONTHS, summarize_timing

TRAVEL_INTENT_KEYWORDS = (
    "trip",
    "travel",
    "journey",
    "getaway",
    "holiday",
    "vacation",
    "retreat",
    "escape",
    "staycation",
)
NATURAL_TRAVEL_INTENT_PATTERNS = (
    r"\b(?:help me\s+)?(?:plan|arrange|organize|organise|create|prepare|book)\b.*\b(?:break|weekend away)\b",
    r"\b(?:thinking of|considering|looking at|want)\b.*\b(?:long weekend|weekend away)\b",
    r"\b\d+\s*-\s*day\s+break\b|\b\d+\s+day\s+break\b",
    r"\b\d+\s*-\s*night\s+break\b|\b\d+\s+night\s+break\b",
    r"\blong weekend\b",
    r"\bweekend away\b",
    rf"\b(?:(?:i|we)\s+(?:really\s+)?need|need|i\s+could\s+use|i\s+want)\s+a\s+(?:little\s+|short\s+)?break\b.*\b(?:{MONTHS}|next month|this month|next week|this weekend|next weekend|sometime|coast)\b",
    r"^somewhere\s+\w+\b.*\b(?:next month|this month|next week|this weekend|next weekend|for\s+\d+)\b",
    rf"\bwe\s+could\s+use\s+a\s+break\b.*\b(?:diani|watamu|naivasha|nairobi|coast|mara|{MONTHS})\b",
    rf"\bplan\s+something\s+\w+\b.*\b(?:for\s+\d+|{MONTHS})\b",
    r"^near\s+\w+\b.*\bfor\s+\d+\b",
    r"\b(?:diani|watamu|naivasha|nairobi|coast|mara|maasai mara)\s+stay\b.*\b(?:budget|for\s+\d+|from\s+\d+|\d+\s+(?:january|february|march|april|may|june|july|august|september|october|november|december))\b",
    rf"\bthinking\s+maybe\b.*\b(?:coast|mara|diani|watamu|naivasha|nairobi|{MONTHS}|sometime)\b",
    rf"\bi\s+want\s+something\b.*\b(?:romantic|family|adventure|quiet|low-key)\b.*\b(?:coast|mara|diani|watamu|naivasha|nairobi|{MONTHS})\b",
    rf"\bcan\s+you\s+sort\b.*\bbreak\b.*\b(?:{MONTHS}|next week|next month|this weekend|next weekend|low budget|for\s+\d+)\b",
)
NON_TRAVEL_BREAK_PATTERNS = (
    r"\bbreak\s+from\s+(?:work|studying|school|class|classes|job)\b",
    r"\bbreak\s+on\s+(?:this\s+)?(?:project|task|assignment)\b",
    r"\bbreak\s+in\s+(?:the\s+)?(?:meeting|session|class)\b",
)
TRAVEL_ONLY_ERROR = "Slate808 currently supports travel planning only."


def _validated_planning_constraints(details: dict) -> dict:
    planning_constraints = details.get("planning_constraints")
    if not planning_constraints:
        return {}
    return validate_planning_constraints(planning_constraints).model_dump()


def _get_destination_policy(details: dict) -> dict:
    planning_constraints = _validated_planning_constraints(details)
    return planning_constraints.get("destination_policy", {})


def _get_constraint_policy(details: dict) -> dict:
    planning_constraints = _validated_planning_constraints(details)
    return planning_constraints.get("constraint_policy", {})


def _destination_transport_suffix(details: dict) -> str:
    destination_policy = _get_destination_policy(details)
    destination_type = destination_policy.get("destination_type")
    transport_bias = destination_policy.get("transport_bias")

    if destination_type == "coastal" and transport_bias == "road_or_air_connection":
        return "with road or air connections planned around the coast"
    if destination_type == "mountain" and transport_bias == "road_transfer":
        return "with road transfers suited to mountain access"
    if destination_type == "safari" and transport_bias == "airstrip_or_4x4":
        return "with airstrip or 4x4 transfers suited to safari access"
    if destination_type == "city" and transport_bias == "urban_road_transfer":
        return "with urban transfers and traffic-aware movement planned in advance"
    if destination_type == "lake" and transport_bias == "road_transfer":
        return "with road transfers planned around the lake area"
    if destination_type == "forest" and transport_bias == "road_transfer":
        return "with road access planned around trail entry points"
    if destination_type == "arid" and transport_bias == "4x4_required":
        return "with rugged transport planned for remote access"

    return ""


def _destination_activity_suffix(details: dict) -> str:
    destination_policy = _get_destination_policy(details)
    destination_type = destination_policy.get("destination_type")
    activity_bias = destination_policy.get("activity_bias", [])
    pace_bias = destination_policy.get("pace_bias")

    if destination_type == "coastal" and activity_bias == ["beach", "water", "relaxation"]:
        return "with time for beach, water, and relaxation experiences"
    if destination_type == "mountain" and activity_bias == ["hiking", "nature", "outdoor"]:
        return "with time for hiking, outdoor exploration, and nature experiences"
    if destination_type == "safari" and activity_bias == ["wildlife", "game_drive", "photography"]:
        if pace_bias == "early_start":
            return "with time for wildlife viewing, game drives, and early-start excursions"
        return "with time for wildlife viewing and game drives"
    if destination_type == "city" and activity_bias == ["urban", "dining", "culture", "logistics"]:
        return "with time for dining, culture, and urban experiences"
    if destination_type == "lake" and activity_bias == ["boat", "nature", "relaxation"]:
        return "with time for boat rides, scenic views, and calm nature experiences"
    if destination_type == "forest" and activity_bias == ["trail", "nature", "quiet"]:
        return "with time for trail walks, quiet surroundings, and nature experiences"
    if destination_type == "arid" and activity_bias == ["rugged", "remote", "scenic"]:
        return "with time for scenic and rugged exploration"

    return ""


def _append_destination_suffix(step: str, suffix: str) -> str:
    if not suffix:
        return step
    return f"{step} {suffix}"


def _append_constraint_suffix(step: str, suffix: str) -> str:
    if not suffix or suffix in step:
        return step
    return f"{step} {suffix}"


def _merge_constraint_suffixes(step: str, suffixes: list[str]) -> str:
    merged_suffixes: list[str] = []
    normalized_suffixes: list[str] = []

    for suffix in suffixes:
        normalized_suffix = re.sub(r"^(with|while|and)\s+", "", suffix).strip(" ;,.")
        if not normalized_suffix or suffix in step:
            continue
        if any(
            normalized_suffix == existing
            or normalized_suffix in existing
            or existing in normalized_suffix
            for existing in normalized_suffixes
        ):
            continue
        merged_suffixes.append(suffix)
        normalized_suffixes.append(normalized_suffix)

    if not merged_suffixes:
        return step

    rendered_suffixes = [merged_suffixes[0]]
    for suffix in merged_suffixes[1:]:
        rendered_suffixes.append(re.sub(r"^(with|while|and)\s+", "", suffix))

    return f"{step} {'; '.join(rendered_suffixes)}"


def _replace_step_terms(step: str, replacements: list[tuple[str, str]]) -> str:
    updated = step
    for old, new in replacements:
        updated = updated.replace(old, new)
    return updated


def _apply_constraint_policy(steps: list[str], details: dict) -> list[str]:
    constraint_policy = _get_constraint_policy(details)
    if not constraint_policy:
        return steps

    if constraint_policy.get("value_focused"):
        steps[1] = _replace_step_terms(
            steps[1],
            [
                ("premium budget", "cost-conscious budget"),
                ("practical budget", "cost-conscious budget"),
                ("Set a budget", "Set a cost-conscious budget"),
            ],
        )
        steps[1] = _append_constraint_suffix(
            steps[1],
            "while keeping choices simple and good-value",
        )
    elif constraint_policy.get("avoid_premium"):
        steps[1] = _replace_step_terms(
            steps[1],
            [
                ("premium budget", "practical budget"),
                ("elevated experience", "well-planned experience"),
            ],
        )
        steps[1] = _append_constraint_suffix(
            steps[1],
            "while keeping spending practical",
        )

    if constraint_policy.get("avoid_premium"):
        steps[2] = _replace_step_terms(
            steps[2],
            [
                ("premium transport and lodging options", "practical transport and lodging options"),
                ("comfortable and convenient transport options", "practical and convenient transport options"),
            ],
        )
        steps[3] = _replace_step_terms(
            steps[3],
            [
                ("high-quality, curated experiences", "balanced and memorable experiences"),
                ("high-quality and memorable experiences", "balanced and memorable experiences"),
                ("premium", "practical"),
                ("curated", "well-planned"),
                ("exclusive", "well-organized"),
            ],
        )
        steps[4] = _replace_step_terms(
            steps[4],
            [
                ("and align premium bookings", "and align bookings carefully"),
            ],
        )

    transport_suffixes: list[str] = []
    activity_suffixes: list[str] = []
    timing_suffixes: list[str] = []

    if constraint_policy.get("family_safe") or constraint_policy.get("kids_present"):
        transport_suffixes.append("with safe and comfortable movement for everyone")
        activity_suffixes.append("with family-friendly and comfortable options")
        timing_suffixes.append("while keeping the schedule easy for families")

    if constraint_policy.get("low_risk"):
        transport_suffixes.append("with practical and safe movement")
        activity_suffixes.append("with safe and practical choices")

    if constraint_policy.get("value_focused"):
        transport_suffixes.append("using practical and cost-conscious routing")
        activity_suffixes.append("using simple and good-value options")

    if constraint_policy.get("group_coordination"):
        transport_suffixes.append("with shared meeting points and aligned movement")
        activity_suffixes.append("with logistics that keep the group coordinated")
        timing_suffixes.append("confirm the shared schedule for the group")

    if constraint_policy.get("low_mobility"):
        transport_suffixes.append("while keeping transfers easy and low-strain")
        activity_suffixes.append("that keep physical effort light")

    if constraint_policy.get("quiet_preferred"):
        activity_suffixes.append("in calm and quieter settings")

    if constraint_policy.get("slow_pace"):
        activity_suffixes.append("with fewer activities and more recovery time")
        timing_suffixes.append("keep enough room for rest between activities")

    if constraint_policy.get("high_activity"):
        transport_suffixes.append("while keeping movement structured for active segments")
        activity_suffixes.append("with active and well-structured movement")

    steps[2] = _merge_constraint_suffixes(steps[2], transport_suffixes)
    steps[3] = _merge_constraint_suffixes(steps[3], activity_suffixes)
    steps[4] = _merge_constraint_suffixes(steps[4], timing_suffixes)

    return steps


def normalize_request(request: str) -> str:
    text = request.strip().lower()

    replacements = {
        "oneday": "one day",
        "tmrw": "tomorrow",
        "wknd": "weekend",
        "wkend": "weekend",
        "plana": "plan a",
        "paln": "plan",
    }

    for wrong, correct in replacements.items():
        text = re.sub(rf"\b{re.escape(wrong)}\b", correct, text)

    return re.sub(r"\s+", " ", text).strip()


def is_travel_intent(request: str) -> bool:
    text = normalize_request(request)

    if any(re.search(pattern, text) for pattern in NON_TRAVEL_BREAK_PATTERNS):
        return False

    if any(keyword in text for keyword in TRAVEL_INTENT_KEYWORDS):
        return True

    if any(re.search(pattern, text) for pattern in NATURAL_TRAVEL_INTENT_PATTERNS):
        return True

    return _looks_like_trip_shorthand(text)


def detect_task_type(request: str) -> str:
    if is_travel_intent(request):
        return "trip"

    return "unsupported"


def build_travel_only_failure(request: str) -> dict:
    goal = normalize_request(request).capitalize()

    return {
        "trace_id": str(uuid.uuid4()),
        "task_type": "unsupported",
        "goal": goal,
        "mode": "normal",
        "clarification_needed": None,
        "clarification_response": None,
        "missing_fields": [],
        "steps": [],
        "checks": [],
        "risks": [],
        "brief": None,
        "planning_constraints": None,
        "status": "fail",
        "errors": [TRAVEL_ONLY_ERROR],
    }


def _looks_like_trip_shorthand(text: str) -> bool:
    destination = travel_brief.extract_destination(text, decision_log=None)
    traveller_count = travel_brief.extract_traveller_count(text, decision_log=None)
    timing = travel_brief.extract_timing(text, decision_log=None)
    budget_info = travel_brief.extract_budget_info(text, decision_log=None)

    support_signals = 0

    if traveller_count:
        support_signals += 1

    if timing.get("state") in {"exact_timing", "relative_timing", "duration_only", "month_only"}:
        support_signals += 1

    if (
        budget_info.get("budget_amount") is not None
        or budget_info.get("budget_level") != "unspecified"
    ):
        support_signals += 1

    if (
        not destination
        and traveller_count
        and timing.get("state") == "exact_timing"
        and re.match(r"^(?:somewhere\s+\w+|near\s+\w+|outside\s+\w+)\b", text)
    ):
        return True

    return bool(destination and support_signals >= 2)


def _duration_label(timing: dict) -> str:
    duration_days = timing.get("duration_days")
    duration_nights = timing.get("duration_nights")

    if duration_days:
        return f"{duration_days} days"

    if duration_nights:
        return f"{duration_nights} nights"

    raw_text = summarize_timing(timing)
    return raw_text.removeprefix("for ").strip()


def _build_timing_step(details: dict, mood: str | None = None) -> str:
    brief = details.get("brief", {})
    timing = brief.get("timing", {})
    timing_policy = _validated_planning_constraints(details).get("timing_policy", {})
    timing_text = timing_policy.get("timing_summary", summarize_timing(timing))
    timing_state = timing_policy.get("timing_state") or timing.get("state", "missing_timing")
    is_exact_timing = timing_policy.get("is_exact_timing", timing_state == "exact_timing")
    is_relative_timing = timing_policy.get("is_relative_timing", timing_state == "relative_timing")
    is_month_only = timing_policy.get("is_month_only", timing_state == "month_only")
    is_duration_only = timing_policy.get("is_duration_only", timing_state == "duration_only")

    mood_suffixes = {
        "relaxed": "and keep the itinerary relaxed",
        "adventure": "and reserve time for active excursions",
        "luxury": "and align premium bookings",
        "romantic": "and protect shared time for special moments",
        "family": "and align transport and accommodation for the family",
        "corporate": "and align team logistics efficiently",
    }

    if is_exact_timing:
        start_date = timing.get("start_date")
        end_date = timing.get("end_date")

        if start_date and end_date and start_date != end_date:
            step = (
                f"Confirm the trip timing by setting the departure date as {start_date} and the return date as {end_date}, "
                "then align bookings"
            )
        elif start_date:
            step = f"Confirm the trip timing by setting the travel date as {start_date} and align bookings"
        else:
            step = f"Confirm the trip timing as {timing_text} and align bookings"

    elif is_relative_timing and timing_text != "timing not specified":
        step = f"Confirm the trip timing window as {timing_text} and align bookings"

    elif is_month_only and timing_text != "timing not specified":
        step = f"Confirm the trip timing by choosing preferred dates within {timing_text} and align bookings"

    elif is_duration_only:
        step = (
            f"Confirm the trip timing as {_duration_label(timing)} and align transport and accommodation"
        )

    else:
        step = "Confirm the trip timing clearly"

    suffix = mood_suffixes.get(mood)
    if suffix:
        return f"{step} {suffix}"

    return step


def _apply_mood_to_trip_steps(steps: list[str], details: dict) -> list[str]:
    mood_policy = _validated_planning_constraints(details).get("mood_policy", {})
    mood = mood_policy.get("trip_mood")
    if not mood:
        return steps

    transport_suffix = _destination_transport_suffix(details)
    activity_suffix = _destination_activity_suffix(details)

    if mood == "relaxed":
        steps[2] = _append_destination_suffix(
            "Choose transport arrangements that keep movement calm, smooth, and low-friction",
            transport_suffix,
        )
        steps[3] = _append_destination_suffix(
            "Select restful and scenic activities that support a calm travel pace",
            activity_suffix,
        )
        steps[4] = _build_timing_step(details, mood="relaxed")

    elif mood == "adventure":
        steps[2] = _append_destination_suffix(
            "Choose transport arrangements that support active excursions and movement",
            transport_suffix,
        )
        steps[3] = _append_destination_suffix(
            "Select adventurous activities and outdoor experiences",
            activity_suffix,
        )
        steps[4] = _build_timing_step(details, mood="adventure")

    elif mood == "luxury":
        steps[1] = "Set a premium budget and estimate the costs for an elevated experience"
        steps[2] = _append_destination_suffix(
            "Choose comfortable and convenient transport options",
            transport_suffix,
        )
        steps[3] = _append_destination_suffix(
            "Select high-quality, curated experiences",
            activity_suffix,
        )
        steps[4] = _build_timing_step(details, mood="luxury")

    elif mood == "romantic":
        steps[3] = _append_destination_suffix(
            "Select intimate activities and memorable shared moments",
            activity_suffix,
        )
        steps[4] = _build_timing_step(details, mood="romantic")

    elif mood == "family":
        steps[2] = _append_destination_suffix(
            "Choose practical transport arrangements that make moving the family easy",
            transport_suffix,
        )
        steps[3] = _append_destination_suffix(
            "Select family-friendly activities that keep everyone comfortable",
            activity_suffix,
        )
        steps[4] = _build_timing_step(details, mood="family")

    elif mood == "corporate":
        steps[1] = "Set a realistic budget with team coordination and efficient logistics in mind"
        steps[2] = _append_destination_suffix(
            "Choose transport arrangements that emphasize coordination and efficiency",
            transport_suffix,
        )
        steps[3] = _append_destination_suffix(
            "Select structured activities suitable for a team or group",
            activity_suffix,
        )
        steps[4] = _build_timing_step(details, mood="corporate")

    return steps


def _budget_aware_trip_steps(details: dict) -> list[str]:
    brief = details.get("brief", {})
    planning_constraints = _validated_planning_constraints(details)
    budget_policy = planning_constraints.get("budget_policy", {})
    destination = brief.get("destination", "")
    posture = budget_policy.get("budget_posture", "unknown")
    transport_suffix = _destination_transport_suffix(details)
    activity_suffix = _destination_activity_suffix(details)

    destination_text = destination if destination else "the destination"

    step_1 = f"Define the trip goal clearly and set the destination to {destination_text}"
    step_2 = "Set a budget and estimate the main costs"

    if posture == "cost_sensitive":
        step_3 = _append_destination_suffix(
            "Choose cost-conscious transport and lodging options",
            transport_suffix,
        )
        step_4 = _append_destination_suffix(
            "Select simple but enjoyable activities",
            activity_suffix,
        )
    elif posture == "balanced":
        step_3 = _append_destination_suffix(
            "Choose balanced transport and lodging options",
            transport_suffix,
        )
        step_4 = _append_destination_suffix(
            "Select activities that balance cost and experience",
            activity_suffix,
        )
    elif posture == "premium":
        step_3 = _append_destination_suffix(
            "Choose premium transport and lodging options",
            transport_suffix,
        )
        step_4 = _append_destination_suffix(
            "Select high-quality and memorable experiences",
            activity_suffix,
        )
    else:
        step_3 = _append_destination_suffix(
            "Choose transport and lodging options that fit the trip",
            transport_suffix,
        )
        step_4 = _append_destination_suffix(
            "Select activities that match your travel goals",
            activity_suffix,
        )

    step_5 = _build_timing_step(details)

    steps = [step_1, step_2, step_3, step_4, step_5]
    steps = _apply_mood_to_trip_steps(steps, details)
    return _apply_constraint_policy(steps, details)


def _finalize_trip_steps(steps: list[str], details: dict) -> list[str]:
    if len(steps) != 5:
        raise ValueError("Trip plans must produce exactly 5 non-empty steps")

    finalized_steps = [step.strip() for step in steps]
    if not finalized_steps[3]:
        finalized_steps[3] = _append_destination_suffix(
            "Select activities that match your travel goals",
            _destination_activity_suffix(details),
        )
    if any(not step for step in finalized_steps):
        raise ValueError("Trip plans must produce exactly 5 non-empty steps")
    return finalized_steps


def build_steps(task_type: str, details: dict | None = None) -> list:
    details = details or {}

    if task_type == "trip":
        return _finalize_trip_steps(_budget_aware_trip_steps(details), details)

    raise ValueError(TRAVEL_ONLY_ERROR)


def generate_plan(request: str) -> dict:
    normalized = normalize_goal(request)
    goal_core = normalized["goal_core"]

    goal = normalize_request(goal_core).capitalize()
    task_type = detect_task_type(goal_core)

    if task_type != "trip":
        return build_travel_only_failure(goal_core)

    brief = None
    brief = travel_brief.build_travel_brief(goal_core, decision_log=None)
    planning_constraints = build_planning_constraints(brief)

    details = {
        "brief": brief,
        "planning_constraints": planning_constraints,
    }

    steps = build_steps(task_type, details)

    return {
        "trace_id": str(uuid.uuid4()),
        "task_type": task_type,
        "goal": goal,
        "mode": "normal",
        "clarification_needed": None,
        "clarification_response": None,
        "missing_fields": [],
        "steps": steps,
        "checks": [
            "All required components are included",
            "Steps follow a logical order",
        ],
        "risks": [
            "Missing key planning detail",
            "Poor sequencing of steps",
        ],
        "brief": brief,
        "planning_constraints": details.get("planning_constraints"),
    }
