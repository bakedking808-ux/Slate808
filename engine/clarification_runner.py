import re

from engine.formatter import format_output
from engine.generator import build_travel_only_failure, is_travel_intent
from engine.runner import run_engine
from engine.logger import log_event
from clarification_state import ClarificationStateManager
from contracts.input_normalization_contract import normalize_travel_input
from engine.travel_brief import (
    MONTHS,
    build_travel_brief,
    extract_budget_info,
    extract_destination,
    extract_trip_mood,
    extract_traveller_count,
    extract_timing,
    get_missing_critical_fields,
    is_contaminated_destination,
    is_uncertain_destination,
    is_timing_usable,
    summarize_timing,
)

state_manager = ClarificationStateManager()
HARD_FIELDS = ("destination", "timing", "traveller_count")

EXIT_COMMANDS = {"exit", "cancel", "stop", "restart", "quit"}
NEW_TASK_OVERRIDE_PATTERNS = [
    r"^\s*(?:plan|book|organize|arrange|schedule|prepare)\s+(?:a|an|the|my|your)\b",
    r"^\s*(?:plan|book|organize|arrange|schedule|prepare)\b.*\b(?:trip|travel|journey|getaway|holiday|vacation|retreat|escape|staycation)\b",
]
TRAVELLER_HINTS = r"\b(?:people|persons|travellers|travelers|adults?|children|kids?|couples|group|party|team|crew|friends|colleagues|guests)\b"
BUDGET_HINTS = r"\b(?:budget|kes|ksh|sh)\b"
TIMING_HINTS = rf"\b(?:{MONTHS}|today|tomorrow|next weekend|this weekend|next week|next month|this month|fortnight|soon|later|sometime|days?|nights?|weeks?)\b"
EXPLICIT_CORRECTION_PATTERNS = (
    r"^\s*actually\b",
    r"\binstead\b",
    r"\bi meant\b",
    r"^\s*no[, ]",
    r"\bmake it\b",
)


def reset_state() -> None:
    state_manager.clear()


def run(user_input: str) -> str:
    normalized_input = normalize_travel_input(user_input)
    text = normalized_input.normalized_input.strip().lower()

    # 🔴 HARD EXIT / RESET
    if text in EXIT_COMMANDS:
        state_manager.clear()
        return "\n==============================\nSession reset. What would you like to plan?\n==============================\n"

    # 🔴 DETECT NEW TASK INTENT (override active session)
    if state_manager.has_active_state():
        if _looks_like_new_request(text):
            state_manager.clear()
            return _start(user_input, normalized_input.normalized_input)

        return _resume(user_input, normalized_input.normalized_input)

    return _start(user_input, normalized_input.normalized_input)


def _start(user_input: str, normalized_input: str) -> str:
    if _is_trip_request(normalized_input):
        brief = build_travel_brief(normalized_input)
        missing_fields = get_missing_critical_fields(brief)

        if missing_fields:
            collected_fields = {}
            for field in (
                "destination",
                "traveller_count",
                "timing",
                "budget_amount",
                "budget_level",
                "trip_mood",
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
            
            # Emit clarification routing metric
            log_event(
                filename="engine.log",
                source="clarification_runner",
                layer="clarification",
                event="clarification_routed",
                status="routed",
                trace_id=state["trace_id"],
                details={
                    "missing_fields": missing_fields,
                    "collected_fields_count": len(collected_fields),
                    "collected_field_names": sorted(collected_fields),
                }
            )
            
            return _next_prompt(missing_fields[0], state)

    return _run_with_travel_boundary(normalized_input)


def _is_trip_request(user_input: str) -> bool:
    return is_travel_intent(user_input)


def _run_with_travel_boundary(user_input: str) -> str:
    if _is_trip_request(user_input):
        return run_engine(user_input)

    return format_output(build_travel_only_failure(user_input))


def _resume(user_input: str, normalized_input: str) -> str:
    state = state_manager.get_state()
    current_field = state["current_field"]
    extracted_fields = _extract_resume_fields(normalized_input, state)
    if extracted_fields:
        state_manager.merge_fields(extracted_fields)

    merged_state = state_manager.get_state()
    value = merged_state["collected_fields"].get(current_field)
    hard_missing = _remaining_hard_fields(merged_state["collected_fields"])

    if value is None:
        state_manager.increment_retry()
        return _retry_prompt(current_field, state_manager.get_state())

    if current_field == "timing" and current_field in hard_missing and not is_timing_usable(value):
        state_manager.increment_retry()
        return _retry_prompt(current_field, state_manager.get_state())

    if current_field == "timing" and current_field in hard_missing and _needs_exact_timing_refinement(value):
        state_manager.increment_retry()

        # Emit relative timing refinement metric
        log_event(
            filename="engine.log",
            source="clarification_runner",
            layer="clarification",
            event="relative_timing_exact_date_refinement",
            status="detected",
            trace_id=state["trace_id"],
            details={
                "current_state": value.get("state"),
                "retry_count": state_manager.get_state()["retry_count"]
            }
        )

        return _retry_prompt(current_field, state_manager.get_state())

    if current_field == "timing" and _duration_conflicts_with_exact_range(state, value):
        state_manager.increment_retry()
        prompt = _timing_prompt(state_manager.get_state(), retry=True)
        return f"\n==============================\n{prompt}\n==============================\n"

    if current_field in HARD_FIELDS:
        if hard_missing:
            state = state_manager.start(
                task_type=state["task_type"],
                original_input=state["original_input"],
                missing_fields=hard_missing,
                collected_fields=merged_state["collected_fields"],
                trace_id=state["trace_id"],
            )
            return _next_prompt(state["current_field"], state)

        state = dict(merged_state)
        state["missing_fields"] = []
        state["current_field"] = None
        state["status"] = "complete"
        state["active"] = False
        state["retry_count"] = 0
    else:
        state = state_manager.update_with_field(current_field, value)

    if state["status"] == "complete":
        if "trip_mood" not in state["collected_fields"]:
            state = state_manager.start(
                task_type=state["task_type"],
                original_input=state["original_input"],
                missing_fields=["trip_mood"],
                collected_fields=state["collected_fields"],
                trace_id=state["trace_id"],
            )
            return _next_prompt("trip_mood", state)

        full_input = _rebuild_input(state)
        state_manager.clear()
        return run_engine(full_input)

    return _next_prompt(state["current_field"], state)


def _duration_conflicts_with_exact_range(state: dict, timing: dict) -> bool:
    previous = state.get("collected_fields", {}).get("timing", {})
    expected_days = previous.get("duration_days")

    if not expected_days or timing.get("state") != "exact_timing":
        return False

    actual_days = _exact_range_day_count(timing)
    return actual_days is not None and actual_days != expected_days


def _exact_range_day_count(timing: dict) -> int | None:
    start_date = timing.get("start_date")
    end_date = timing.get("end_date")

    if not start_date or not end_date:
        return None

    start = _day_month_pair(start_date)
    end = _day_month_pair(end_date)
    if not start or not end:
        return None

    start_day, start_month = start
    end_day, end_month = end

    if start_month == end_month:
        if end_day < start_day:
            return None
        return end_day - start_day + 1

    months = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]
    month_lengths = {
        "january": 31,
        "february": 28,
        "march": 31,
        "april": 30,
        "may": 31,
        "june": 30,
        "july": 31,
        "august": 31,
        "september": 30,
        "october": 31,
        "november": 30,
        "december": 31,
    }
    if start_month not in month_lengths or end_month not in month_lengths:
        return None

    start_index = months.index(start_month)
    end_index = months.index(end_month)
    if end_index < start_index:
        return None

    days = month_lengths[start_month] - start_day + 1 + end_day
    for month in months[start_index + 1:end_index]:
        days += month_lengths.get(month, 0)
    return days


def _day_month_pair(value: str) -> tuple[int, str] | None:
    match = re.match(r"^(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)$", value.strip().lower())
    if not match:
        return None
    return int(match.group(1)), match.group(2)


def _needs_exact_timing_refinement(timing: dict) -> bool:
    if timing.get("state") != "relative_timing":
        return False

    return True


def _extract_single(field: str, text: str):
    text = text.strip()

    if field == "destination":
        return _extract_destination_value(text)

    if field == "traveller_count":
        val = extract_traveller_count(text)
        return val if val else None

    if field == "timing":
        timing = extract_timing(text)
        if timing.get("state") in {"exact_timing", "relative_timing", "duration_only", "month_only"}:
            return timing
        return None

    if field == "trip_mood":
        return extract_trip_mood(text)

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

    if is_contaminated_destination(candidate):
        return False

    if is_uncertain_destination(candidate):
        return False

    return True


def _looks_like_timing(text: str) -> bool:
    return bool(re.search(TIMING_HINTS, text))


def _looks_like_budget(text: str) -> bool:
    return bool(re.search(BUDGET_HINTS, text))


def _looks_like_traveller_phrase(text: str) -> bool:
    return bool(re.search(TRAVELLER_HINTS, text))


def _is_explicit_correction(text: str) -> bool:
    normalized = text.lower()
    return any(re.search(pattern, normalized) for pattern in EXPLICIT_CORRECTION_PATTERNS)


def _remaining_hard_fields(collected_fields: dict) -> list[str]:
    return get_missing_critical_fields(
        {
            "destination": collected_fields.get("destination"),
            "timing": collected_fields.get("timing"),
            "traveller_count": collected_fields.get("traveller_count"),
        }
    )


def _extract_resume_fields(text: str, state: dict) -> dict:
    collected = state.get("collected_fields", {})
    missing_fields = set(state.get("missing_fields", []))
    fields_to_extract = set(missing_fields)

    if _is_explicit_correction(text):
        fields_to_extract.update(HARD_FIELDS)

    extracted = {}
    is_correction = _is_explicit_correction(text)
    for field in HARD_FIELDS:
        if field not in fields_to_extract:
            continue
        value = _extract_single(field, text)
        if value is not None and (
            field not in collected or field in missing_fields or is_correction
        ):
            extracted[field] = value

    extracted.update(_extract_supplemental_fields(text))
    return extracted


def _extract_destination_value(text: str):
    val = extract_destination(text)
    if val:
        return val

    for fragment in _destination_fragments(text):
        if _looks_like_destination_candidate(fragment):
            return fragment

    return None


def _destination_fragments(text: str) -> list[str]:
    cleaned = text.lower()
    cleaned = re.sub(r"\b(?:actually|make it|i meant|instead)\b", "", cleaned)
    cleaned = re.sub(r"^\s*no[, ]*", "", cleaned).strip(" ,.-")
    fragments = re.split(r",|\band\b", cleaned)
    return [fragment.strip(" ,.-") for fragment in fragments if fragment.strip(" ,.-")]


def _rebuild_input(state: dict) -> str:
    collected = state["collected_fields"]

    destination = collected.get("destination", "")
    travellers = collected.get("traveller_count", "")
    timing = collected.get("timing", {}).get("raw_text", "")
    budget_amount = collected.get("budget_amount")
    budget_level = collected.get("budget_level", "unspecified")
    trip_mood = collected.get("trip_mood")

    traveller_phrase = (
        f"{travellers} people" if isinstance(travellers, int) else str(travellers)
    )

    mood_phrase = f"{trip_mood} " if trip_mood else ""
    rebuilt = f"Plan a {mood_phrase}trip to {destination} for {traveller_phrase}"

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

    trip_mood = extract_trip_mood(text)
    if trip_mood is not None:
        supplemental["trip_mood"] = trip_mood

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

    if timing_state == "relative_timing" and timing_summary != "timing not specified":
        return f"What exact dates are you planning for {timing_summary}?"

    prompt = "What exact dates are you planning?"
    if retry:
        prompt += " Please give a specific answer."
    return prompt


def _format_clarification_prompt(prompt: str, state: dict | None = None) -> str:
    collected = (state or {}).get("collected_fields", {})
    if (
        not collected.get("trip_mood")
        and prompt != "What kind of trip mood should this have?"
    ):
        return f"\n==============================\n{prompt}\n==============================\n"

    lines = ["Slate808 Output", "==============================", "", "Status: pass", ""]
    brief_lines = []

    if collected.get("destination"):
        brief_lines.append(f"- Destination: {collected['destination']}")
    if collected.get("traveller_count"):
        brief_lines.append(f"- Traveller Count: {collected['traveller_count']}")
    if collected.get("timing") and collected["timing"].get("state") != "missing_timing":
        brief_lines.append(f"- Timing: {summarize_timing(collected['timing'])}")
    if collected.get("budget_amount") is not None:
        brief_lines.append(
            f"- Budget: {collected['budget_amount']} ({collected.get('budget_level', 'unspecified')})"
        )
    elif collected.get("budget_level") in {"low", "medium", "high"}:
        brief_lines.append(f"- Budget Level: {collected['budget_level']}")
    if collected.get("trip_mood"):
        brief_lines.append(f"- Trip Mood: {collected['trip_mood']}")

    if brief_lines:
        lines.append("Travel Brief:")
        lines.extend(brief_lines)
        lines.append("")

    lines.append("==============================")
    lines.append(prompt)
    lines.append("==============================")
    return "\n".join(lines)


def _next_prompt(field: str, state: dict | None = None) -> str:
    if field == "destination":
        return _format_clarification_prompt("Where would you like to go?", state)

    if field == "traveller_count":
        return _format_clarification_prompt("How many travellers?", state)

    if field == "timing":
        return _format_clarification_prompt(_timing_prompt(state), state)

    if field == "trip_mood":
        return _format_clarification_prompt("What kind of trip mood should this have?", state)

    return ""


def _retry_prompt(field: str, state: dict | None = None) -> str:
    if field == "timing":
        return _format_clarification_prompt(_timing_prompt(state, retry=True), state)

    return _next_prompt(field, state)


def _looks_like_new_request(text: str) -> bool:
    return any(re.search(pattern, text) for pattern in NEW_TASK_OVERRIDE_PATTERNS)
