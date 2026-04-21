import re

from engine.formatter import format_output
from engine.generator import build_travel_only_failure, is_travel_intent
from engine.runner import run_engine
from clarification_state import ClarificationStateManager
from engine.travel_brief import (
    MONTHS,
    build_travel_brief,
    extract_budget_info,
    extract_destination,
    extract_traveller_count,
    extract_timing,
    get_missing_critical_fields,
    is_timing_usable,
    summarize_timing,
)

state_manager = ClarificationStateManager()

EXIT_COMMANDS = {"exit", "cancel", "stop", "restart", "quit"}
NEW_TASK_OVERRIDE_PATTERNS = [
    r"^\s*(?:plan|book|organize|arrange|schedule|prepare)\s+(?:a|an|the|my|your)\b",
    r"^\s*(?:plan|book|organize|arrange|schedule|prepare)\b.*\b(?:trip|travel|journey|getaway|holiday|vacation|retreat|escape|staycation)\b",
]
TRAVELLER_HINTS = r"\b(?:people|persons|travellers|travelers|adults?|children|kids?|couples|group|party|team|crew|friends|colleagues|guests)\b"
BUDGET_HINTS = r"\b(?:budget|kes|ksh|sh)\b"
TIMING_HINTS = rf"\b(?:{MONTHS}|today|tomorrow|next weekend|this weekend|next week|next month|this month|fortnight|soon|later|sometime|days?|nights?|weeks?)\b"


def reset_state() -> None:
    state_manager.clear()


def run(user_input: str) -> str:
    text = user_input.strip().lower()

    # 🔴 HARD EXIT / RESET
    if text in EXIT_COMMANDS:
        state_manager.clear()
        return "\n==============================\nSession reset. What would you like to plan?\n==============================\n"

    # 🔴 DETECT NEW TASK INTENT (override active session)
    if state_manager.has_active_state():
        if _looks_like_new_request(text):
            state_manager.clear()
            return _start(user_input)

        return _resume(user_input)

    return _start(user_input)


def _start(user_input: str) -> str:
    if _is_trip_request(user_input):
        brief = build_travel_brief(user_input)
        missing_fields = get_missing_critical_fields(brief)

        if missing_fields:
            collected_fields = {}
            for field in (
                "destination",
                "traveller_count",
                "timing",
                "budget_amount",
                "budget_level",
            ):
                value = brief.get(field)
                if field == "timing" and value and value.get("state") != "missing_timing":
                    collected_fields[field] = value
                elif field not in missing_fields and value:
                    collected_fields[field] = value

            state = state_manager.start(
                task_type="trip",
                original_input=user_input,
                missing_fields=missing_fields,
                collected_fields=collected_fields,
            )
            return _next_prompt(missing_fields[0], state)

    return _run_with_travel_boundary(user_input)


def _is_trip_request(user_input: str) -> bool:
    return is_travel_intent(user_input)


def _run_with_travel_boundary(user_input: str) -> str:
    if _is_trip_request(user_input):
        return run_engine(user_input)

    return format_output(build_travel_only_failure(user_input))


def _resume(user_input: str) -> str:
    state = state_manager.get_state()
    current_field = state["current_field"]

    supplemental_fields = _extract_supplemental_fields(user_input)
    if supplemental_fields:
        state_manager.merge_fields(supplemental_fields)

    value = _extract_single(current_field, user_input)

    if value is None:
        state_manager.increment_retry()
        return _retry_prompt(current_field, state_manager.get_state())

    if current_field == "timing" and not is_timing_usable(value):
        state_manager.merge_fields({"timing": value})
        state_manager.increment_retry()
        return _retry_prompt(current_field, state_manager.get_state())

    state = state_manager.update_with_field(current_field, value)

    if state["status"] == "complete":
        full_input = _rebuild_input(state)
        state_manager.clear()
        return run_engine(full_input)

    return _next_prompt(state["current_field"], state)


def _extract_single(field: str, text: str):
    text = text.strip()

    if field == "destination":
        val = extract_destination(text)
        if val:
            return val

        fallback = text.lower().strip(" ,.-")
        return fallback if _looks_like_destination_candidate(fallback) else None

    if field == "traveller_count":
        val = extract_traveller_count(text)
        return val if val else None

    if field == "timing":
        timing = extract_timing(text)
        if timing.get("state") in {"exact_timing", "relative_timing", "duration_only", "month_only"}:
            return timing
        return None

    return None


def _looks_like_destination_candidate(candidate: str) -> bool:
    if not candidate:
        return False

    if candidate in EXIT_COMMANDS:
        return False

    if len(candidate) < 2:
        return False

    if re.search(r"\d", candidate):
        return False

    if _looks_like_timing(candidate):
        return False

    if _looks_like_budget(candidate):
        return False

    if _looks_like_traveller_phrase(candidate):
        return False

    if _looks_like_new_request(candidate):
        return False

    return True


def _looks_like_timing(text: str) -> bool:
    return bool(re.search(TIMING_HINTS, text))


def _looks_like_budget(text: str) -> bool:
    return bool(re.search(BUDGET_HINTS, text))


def _looks_like_traveller_phrase(text: str) -> bool:
    return bool(re.search(TRAVELLER_HINTS, text))


def _rebuild_input(state: dict) -> str:
    collected = state["collected_fields"]

    destination = collected.get("destination", "")
    travellers = collected.get("traveller_count", "")
    timing = collected.get("timing", {}).get("raw_text", "")
    budget_amount = collected.get("budget_amount")
    budget_level = collected.get("budget_level", "unspecified")

    traveller_phrase = (
        f"{travellers} people" if isinstance(travellers, int) else str(travellers)
    )

    rebuilt = f"Plan a trip to {destination} for {traveller_phrase}"

    if timing:
        if timing.startswith("for "):
            rebuilt += f" {timing}"
        else:
            rebuilt += f" at {timing}"

    if budget_amount is not None:
        rebuilt += f" with a budget of {budget_amount}"
    elif budget_level in {"low", "medium", "high"}:
        rebuilt += f" with a {budget_level} budget"

    return rebuilt


def _extract_supplemental_fields(text: str) -> dict:
    budget_info = extract_budget_info(text)
    supplemental = {}

    if budget_info["budget_amount"] is not None:
        supplemental["budget_amount"] = budget_info["budget_amount"]
        supplemental["budget_level"] = budget_info["budget_level"]
    elif budget_info["budget_level"] != "unspecified":
        supplemental["budget_level"] = budget_info["budget_level"]

    return supplemental


def _timing_prompt(state: dict | None, retry: bool = False) -> str:
    timing = (state or {}).get("collected_fields", {}).get("timing", {})
    timing_state = timing.get("state")
    timing_summary = summarize_timing(timing)

    if timing_state == "month_only" and timing_summary != "timing not specified":
        return f"Which exact dates in {timing_summary.title()} are you planning?"

    if timing_state == "duration_only" and timing_summary != "timing not specified":
        duration_label = timing_summary.removeprefix("for ")
        return f"What exact dates are you planning for those {duration_label}?"

    prompt = "What exact dates are you planning?"
    if retry:
        prompt += " Please give a specific answer."
    return prompt


def _next_prompt(field: str, state: dict | None = None) -> str:
    if field == "destination":
        return "\n==============================\nWhere would you like to go?\n==============================\n"

    if field == "traveller_count":
        return "\n==============================\nHow many travellers?\n==============================\n"

    if field == "timing":
        return f"\n==============================\n{_timing_prompt(state)}\n==============================\n"

    return ""


def _retry_prompt(field: str, state: dict | None = None) -> str:
    if field == "timing":
        return f"\n==============================\n{_timing_prompt(state, retry=True)}\n==============================\n"

    return _next_prompt(field, state)


def _looks_like_new_request(text: str) -> bool:
    return any(re.search(pattern, text) for pattern in NEW_TASK_OVERRIDE_PATTERNS)
