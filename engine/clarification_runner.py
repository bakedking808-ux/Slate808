import re

from engine.formatter import format_destination_for_display, format_output, format_timing_for_display
from engine.display_language import display_trip_mood
from engine.generator import build_travel_only_failure, is_travel_intent
from engine.runner import run_engine, set_execution_observability_context
from engine.logger import log_event
from clarification_state import ClarificationStateManager
from contracts.input_normalization_contract import normalize_travel_input
from engine.interpretation import interpret_input
from contracts.interpretation_outcome_contract import (
    InterpretationContext,
    InterpretationOutcome,
    InterpretationTargetField,
)
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
from contracts.timing_parsing_contract import parse_timing_text
from contracts.operator_workflow_contract import OperatorWorkflowInput, map_operator_workflow

state_manager = ClarificationStateManager()
HARD_FIELDS = ("destination", "timing", "traveller_count")
recent_completed_trip: dict | None = None

EXIT_COMMANDS = {"exit", "cancel", "stop", "restart", "quit"}
APPROVAL_ACCEPT_COMMANDS = {"approved", "approve", "yes approved", "yes, approved"}
APPROVAL_REJECT_COMMANDS = {"declined", "reject", "rejected", "not approved", "no, declined"}
NEW_TASK_OVERRIDE_PATTERNS = [
    r"^\s*(?:plan|book|organize|arrange|schedule|prepare)\s+(?:a|an|the|my|your)\b",
    r"^\s*(?:plan|book|organize|arrange|schedule|prepare)\b.*\b(?:trip|travel|journey|getaway|holiday|vacation|retreat|escape|staycation)\b",
]
TRAVELLER_HINTS = r"\b(?:people|persons|travellers|travelers|adults?|children|kids?|couples|group|party|team|crew|friends|colleagues|guests)\b"
BUDGET_HINTS = r"\b(?:budget|kes|ksh|sh)\b"
TIMING_HINTS = rf"\b(?:{MONTHS}|today|tomorrow|next weekend|this weekend|next week|next month|this month|fortnight|soon|later|sometime|days?|nights?|weeks?)\b"
EXPLICIT_CORRECTION_PATTERNS = (
    r"^\s*actually\b",
    r"^\s*wait\b",
    r"^\s*forget\b",
    r"\binstead\b",
    r"\bi meant\b",
    r"^\s*no[, ]",
    r"\bmake it\b",
)
POST_COMPLETION_UPDATE_PATTERNS = EXPLICIT_CORRECTION_PATTERNS + (
    r"\bchange the destination\b",
    r"\bchange the dates\b",
    r"\bmove the dates\b",
    r"\bshift the dates\b",
    r"\bswitch the destination\b",
    r"\bwe(?:'re| are)\s+\d+\s+now\b",
)


def reset_state() -> None:
    state_manager.clear()
    global recent_completed_trip
    recent_completed_trip = None


def run(user_input: str) -> str:
    normalized_input = normalize_travel_input(user_input)
    text = normalized_input.normalized_input.strip().lower()

    # 🔴 HARD EXIT / RESET
    if text in EXIT_COMMANDS:
        state_manager.clear()
        return _format_session_control_prompt("Session reset. What would you like to plan?", "scope_reset")

    # 🔴 DETECT NEW TASK INTENT (override active session)
    if state_manager.has_active_state():
        if _looks_like_new_request(text):
            state_manager.clear()
            return _start(user_input, normalized_input.normalized_input)

        return _resume(user_input, normalized_input.normalized_input)

    completed_update = _resume_completed_trip_update(user_input, normalized_input.normalized_input)
    if completed_update is not None:
        return completed_update

    approval_update = _resume_recent_approval(normalized_input.normalized_input)
    if approval_update is not None:
        return approval_update

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

        _remember_completed_trip(user_input, brief)

    return _run_with_travel_boundary(normalized_input)


def _is_trip_request(user_input: str) -> bool:
    return is_travel_intent(user_input)


def _run_with_travel_boundary(user_input: str) -> str:
    if _is_trip_request(user_input):
        set_execution_observability_context(flow_shape="direct_ready_completion")
        return run_engine(user_input)

    return format_output(build_travel_only_failure(user_input))


def _resume(user_input: str, normalized_input: str) -> str:
    state = state_manager.get_state()
    current_field = state["current_field"]

    extracted_fields = None

    if current_field and not _should_bypass_ioc_for_legacy_resume(normalized_input):
        ioc_context = InterpretationContext(
            active_field=_ioc_target_for_field(current_field),
            workflow_state=state.get("workflow_state"),
            clarification_attempt_count=state.get("retry_count", 0),
            previous_prompt=state.get("last_prompt"),
            has_active_clarification=True,
            approval_expected=(state.get("workflow_state") == "human_approval_required"),
        )
        ioc_result = interpret_input(normalized_input, ioc_context)

        if ioc_result.outcome == InterpretationOutcome.INTERPRET:
            target_field = _field_for_ioc_result(current_field, ioc_result)
            extracted_fields = _ioc_extracted_fields(
                target_field,
                ioc_result.extracted_value,
            )

            # If IOC captured a supplemental field such as budget or mood while
            # the active hard field is still unresolved, also run legacy
            # extraction on the same reply. This preserves mixed replies like:
            # "27th April, 10AM to 3PM, budget friendly".
            if (
                extracted_fields
                and current_field not in extracted_fields
                and _has_supplemental_update(extracted_fields)
            ):
                legacy_fields = _extract_resume_fields(normalized_input, state)
                legacy_fields.update(extracted_fields)
                extracted_fields = legacy_fields

            # If IOC understood the input but the value cannot be adapted to
            # Slate's native field shape, fall back to legacy extraction instead
            # of turning IOC into a second state machine.
            if not extracted_fields:
                extracted_fields = None

        elif ioc_result.outcome == InterpretationOutcome.CLARIFY:
            if _ioc_has_specific_prompt(ioc_result):
                state_manager.increment_retry()
                return _format_clarification_prompt(
                    ioc_result.clarification_prompt
                    or _plain_prompt_for_field(current_field, state_manager.get_state(), retry=True),
                    state_manager.get_state(),
                )
            extracted_fields = None

        elif ioc_result.outcome == InterpretationOutcome.CORRECT:
            state_manager.increment_retry()
            return _format_clarification_prompt(
                ioc_result.correction_prompt
                or _plain_prompt_for_field(current_field, state_manager.get_state(), retry=True),
                state_manager.get_state(),
            )

        elif ioc_result.outcome == InterpretationOutcome.REJECT:
            reason = getattr(ioc_result.reason_code, "value", None) or ""
            if reason == "approval_not_expected":
                state_manager.increment_retry()
                return _format_clarification_prompt(
                    "Approval is not expected at this step.",
                    state_manager.get_state(),
                )
            extracted_fields = None

    if extracted_fields is None:
        extracted_fields = _extract_resume_fields(normalized_input, state)

    if extracted_fields:
        state_manager.merge_fields(extracted_fields)

    merged_state = state_manager.get_state()
    value = merged_state["collected_fields"].get(current_field)
    hard_missing = _remaining_hard_fields(merged_state["collected_fields"])

    if value is None and _has_progressing_hard_field_update(extracted_fields, current_field):
        if hard_missing:
            state = state_manager.start(
                task_type=state["task_type"],
                original_input=state["original_input"],
                missing_fields=hard_missing,
                collected_fields=merged_state["collected_fields"],
                trace_id=state["trace_id"],
            )
            return _next_prompt(state["current_field"], state)

    if value is None and _has_supplemental_update(extracted_fields):
        state_manager.increment_retry()
        label = _supplemental_acknowledgement(extracted_fields)
        prompt = _plain_prompt_for_field(current_field, state_manager.get_state(), retry=False)
        return _format_clarification_prompt(
            f"{label} {prompt}",
            state_manager.get_state(),
        )

    if value is None:
        state_manager.increment_retry()
        return _retry_prompt(current_field, state_manager.get_state())

    if current_field == "timing" and current_field in hard_missing and not is_timing_usable(value):
        state_manager.increment_retry()
        return _retry_prompt(current_field, state_manager.get_state())

    if current_field == "timing" and current_field in hard_missing and _needs_exact_timing_refinement(value):
        state_manager.increment_retry()

        log_event(
            filename="engine.log",
            source="clarification_runner",
            layer="clarification",
            event="relative_timing_exact_date_refinement",
            status="detected",
            trace_id=state["trace_id"],
            details={
                "current_state": value.get("state"),
                "retry_count": state_manager.get_state()["retry_count"],
            },
        )

        return _retry_prompt(current_field, state_manager.get_state())

    if current_field == "timing" and _duration_conflicts_with_exact_range(state, value):
        state_manager.increment_retry()
        prompt = _timing_prompt(state_manager.get_state(), retry=True)
        return "\\n==============================\\n" + prompt + "\\n==============================\\n"

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

        _remember_completed_fields(state["original_input"], state["collected_fields"])
        full_input = _rebuild_input(state)
        state_manager.clear()
        set_execution_observability_context(flow_shape="clarification_resume_completion")
        return run_engine(full_input)

    return _next_prompt(state["current_field"], state)


def _ioc_has_specific_prompt(result) -> bool:
    prompt = (
        result.clarification_prompt
        or result.correction_prompt
        or ""
    ).strip().lower()

    return bool(prompt) and prompt not in {
        "could you clarify your request?",
        "please give a specific answer.",
    }


def _should_bypass_ioc_for_legacy_resume(text: str) -> bool:
    normalized = text.strip().lower()

    # Explicit corrections already have stable legacy handling that can replace
    # previously collected fields and recompute the next clarification target.
    if _is_update_style_reply(normalized):
        return True

    # Relative/provisional timing should stay in the legacy timing pipeline so
    # prompts preserve context: "for next weekend", "for tomorrow", etc.
    if re.search(
        r"\b(?:next weekend|this weekend|tomorrow|next month|this month|next week|this week)\b",
        normalized,
    ):
        return True

    # Mixed destination + broad timing answers, e.g. "Watamu next month", are
    # better handled by legacy multi-field extraction than by active-field IOC.
    if current_destination := extract_destination(normalized):
        timing = extract_timing(normalized)
        if timing and timing.get("state") in {"relative_timing", "month_only"}:
            return True

    return False




def _field_for_ioc_result(current_field: str, result) -> str:
    target = result.target_field

    if target == InterpretationTargetField.BUDGET:
        if isinstance(result.extracted_value, int):
            return "budget_amount"
        return "budget_level"

    if target == InterpretationTargetField.MOOD:
        return "trip_mood"

    if target == InterpretationTargetField.TIMING:
        return "timing"

    if target == InterpretationTargetField.DESTINATION:
        return "destination"

    if target == InterpretationTargetField.TRAVELLER_COUNT:
        return "traveller_count"

    return current_field


def _ioc_target_for_field(field: str):
    value_map = {
        "destination": "destination",
        "timing": "timing",
        "traveller_count": "traveller_count",
        "budget_amount": "budget",
        "budget_level": "budget",
        "trip_mood": "mood",
        "approval": "approval",
    }
    target_value = value_map.get(field, "unknown")

    try:
        return InterpretationTargetField(target_value)
    except Exception:
        enum_name = target_value.upper()
        return getattr(
            InterpretationTargetField,
            enum_name,
            getattr(InterpretationTargetField, "UNKNOWN"),
        )


def _ioc_extracted_fields(field: str, value) -> dict:
    if value is None:
        return {}

    if field == "timing":
        timing = _ioc_timing_from_value(value)
        if timing:
            return {"timing": timing}
        return {}

    if field == "destination":
        if isinstance(value, str) and value.strip():
            return {"destination": value.strip().lower()}
        return {}

    if field == "traveller_count":
        if isinstance(value, int):
            return {"traveller_count": value}
        return {}

    if field == "budget_amount":
        if isinstance(value, int):
            info = extract_budget_info(f"budget {value}")
            return {
                "budget_amount": value,
                "budget_level": info.get("budget_level", "unspecified"),
            }
        return {}

    if field == "budget_level":
        if isinstance(value, str):
            mapped = {
                "budget_friendly": "low",
                "low": "low",
                "medium": "medium",
                "high": "high",
                "unspecified": "unspecified",
            }.get(value.strip().lower())
            if mapped:
                return {"budget_level": mapped}
        return {}

    if field == "trip_mood":
        if isinstance(value, str) and value.strip():
            mood = extract_trip_mood(value) or value.strip().lower()
            return {"trip_mood": mood}
        return {}

    return {field: value}


def _ioc_timing_from_value(value) -> dict | None:
    if isinstance(value, dict):
        if value.get("state") and value.get("state") != "missing_timing":
            return value
        return None

    if not isinstance(value, str):
        return None

    parsed = extract_timing(value)
    if parsed and parsed.get("state") != "missing_timing":
        return parsed

    contract_result = parse_timing_text(value)
    if not contract_result.matched or contract_result.parsed is None:
        return None

    contract_timing = contract_result.parsed
    if contract_timing.category not in {"exact_date", "date_range", "composite_timing"}:
        return None

    if not (contract_timing.start_date or contract_timing.end_date):
        return None

    return {
        "raw_text": contract_timing.normalized_text or contract_timing.raw_text,
        "start_date": contract_timing.start_date,
        "end_date": contract_timing.end_date,
        "duration_days": contract_timing.duration_days,
        "duration_nights": contract_timing.duration_nights,
        "date_flexibility": "fixed",
        "state": "exact_timing",
        "confidence": contract_timing.confidence,
    }


def _has_supplemental_update(extracted_fields: dict) -> bool:
    return any(
        field in extracted_fields
        for field in ("budget_amount", "budget_level", "trip_mood")
    )


def _supplemental_acknowledgement(extracted_fields: dict) -> str:
    if "budget_amount" in extracted_fields or "budget_level" in extracted_fields:
        return "Budget noted."
    if "trip_mood" in extracted_fields:
        return "Trip mood noted."
    return "Detail noted."


def _plain_prompt_for_field(field: str, state: dict | None = None, retry: bool = False) -> str:
    if field == "destination":
        return "Where would you like to go?"

    if field == "traveller_count":
        return "How many travellers?"

    if field == "timing":
        return _timing_prompt(state, retry=retry)

    if field == "trip_mood":
        return "What kind of trip mood should this have?"

    return "Please give a specific answer."


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
        val = _extract_traveller_count_value(text)
        return val if val else None

    if field == "timing":
        timing_text = _normalize_timing_correction_scaffold(text)
        timing = _ioc_timing_from_value(timing_text)
        if timing and timing.get("state") in {"exact_timing", "relative_timing", "duration_only", "month_only"}:
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


def _has_progressing_hard_field_update(extracted_fields: dict, current_field: str) -> bool:
    return any(
        field in extracted_fields
        for field in HARD_FIELDS
        if field != current_field
    )


def _extract_resume_fields(text: str, state: dict) -> dict:
    collected = state.get("collected_fields", {})
    missing_fields = set(state.get("missing_fields", []))
    fields_to_extract = set(missing_fields)

    if _is_update_style_reply(text):
        fields_to_extract.update(HARD_FIELDS)

    extracted = {}
    is_correction = _is_update_style_reply(text)
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
    if _is_update_style_reply(text):
        for fragment in _destination_fragments(text):
            val = extract_destination(fragment)
            if val:
                return val
            if _looks_like_destination_candidate(fragment):
                return fragment
        return None

    val = extract_destination(text)
    if val:
        return val

    for fragment in _destination_fragments(text):
        val = extract_destination(fragment)
        if val:
            return val
        if _looks_like_destination_candidate(fragment):
            return fragment

    return None


def _extract_traveller_count_value(text: str) -> int | None:
    value = extract_traveller_count(text)
    if value is not None:
        return value

    match = re.search(r"\b(?:we(?:'re| are)?|us)\s+(\d{1,3})\b", text.lower())
    if match:
        return int(match.group(1))

    return None


def _resume_completed_trip_update(user_input: str, normalized_input: str) -> str | None:
    if not recent_completed_trip or not _is_update_style_reply(normalized_input):
        return None

    state = {
        "task_type": "trip",
        "original_input": recent_completed_trip["original_input"],
        "collected_fields": dict(recent_completed_trip["collected_fields"]),
        "missing_fields": [],
    }
    extracted_fields = _extract_resume_fields(normalized_input, state)
    if not any(field in extracted_fields for field in HARD_FIELDS):
        return None

    collected_fields = dict(recent_completed_trip["collected_fields"])
    collected_fields.update(extracted_fields)
    hard_missing = _remaining_hard_fields(collected_fields)

    if hard_missing:
        active_state = state_manager.start(
            task_type="trip",
            original_input=recent_completed_trip["original_input"],
            missing_fields=hard_missing,
            collected_fields=collected_fields,
        )
        return _next_prompt(active_state["current_field"], active_state)

    _remember_completed_fields(recent_completed_trip["original_input"], collected_fields)
    set_execution_observability_context(flow_shape="post_completion_update_completion")
    return run_engine(_rebuild_input({"collected_fields": collected_fields}))


def _destination_fragments(text: str) -> list[str]:
    cleaned = _normalize_correction_scaffold(text)
    fragments = [cleaned]
    fragments.extend(re.split(r",|\band\b|[-—]", cleaned))

    candidates = []
    for fragment in fragments:
        fragment = fragment.strip(" ,.-")
        if not fragment:
            continue
        extracted = _extract_destination_fragment_candidate(fragment)
        if extracted:
            candidates.append(extracted)
        if not _looks_like_scaffold_fragment(fragment):
            candidates.append(fragment)

    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def _normalize_correction_scaffold(text: str) -> str:
    cleaned = text.lower()
    cleaned = cleaned.replace("’", "'")
    cleaned = re.sub(r"^\s*no,\s*not\s+[^,.-]+(?:\s+[-—]\s*|\s+)", "", cleaned)
    cleaned = re.sub(r"^\s*no\b[,\s-]*", "", cleaned)
    cleaned = re.sub(r"^\s*(?:actually|wait)\b[,\s-]*", "", cleaned)
    cleaned = re.sub(r"^\s*change\b[,\s-]*", "", cleaned)
    cleaned = re.sub(r"^\s*forget\b[^-—,]*[-—,]\s*", "", cleaned)
    cleaned = re.sub(r"^\s*make it\b\s*", "", cleaned)
    cleaned = re.sub(r"^\s*(?:move|shift)\s+the\s+dates\b(?:\s+to)?\s*", "", cleaned)
    cleaned = re.sub(r"\b(?:instead|please)\b", "", cleaned)
    return cleaned.strip(" ,.-")


def _normalize_timing_correction_scaffold(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = cleaned.replace("’", "'")

    patterns = [
        r"^\s*wait\b[\s,\-]*",
        r"^\s*actually\b[\s,\-]*",
        r"^\s*no\b[\s,\-]*",
        r"^\s*change\s+to\b[\s,\-]*",
        r"^\s*shift\s+to\b[\s,\-]*",
        r"^\s*move\s+to\b[\s,\-]*",
    ]

    for pattern in patterns:
        while True:
            normalized = re.sub(pattern, "", cleaned)
            if normalized == cleaned:
                break
            cleaned = normalized.strip()

    return cleaned.strip(" ,.-")


def _extract_destination_fragment_candidate(fragment: str) -> str | None:
    patterns = (
        r"\bdestination\s+(?:to|is)\s+(.+)$",
        r"\b(?:trip|retreat|getaway|escape|staycation)\s+(?:to|in)\s+(.+)$",
        r"\b(?:beach|corporate|family|quiet|calm|solo|adventure|hiking)\s+(?:trip|retreat|getaway|escape|staycation)\s+(?:to|in)\s+(.+)$",
    )

    for pattern in patterns:
        match = re.search(pattern, fragment)
        if match:
            return match.group(1).strip(" ,.-")

    return None


def _looks_like_scaffold_fragment(fragment: str) -> bool:
    return bool(
        re.search(
            r"\b(?:this is now|not a group|for my parents|just me|solo trip|group one|change|switch|move the dates|shift the dates)\b",
            fragment,
        )
    ) or fragment in {"no", "actually", "wait", "change"}


def _is_update_style_reply(text: str) -> bool:
    normalized = text.lower()
    return any(re.search(pattern, normalized) for pattern in POST_COMPLETION_UPDATE_PATTERNS)


def _remember_completed_trip(original_input: str, brief: dict) -> None:
    collected_fields = _collected_fields_from_brief(brief)
    _remember_completed_fields(original_input, collected_fields)


def _remember_completed_fields(original_input: str, collected_fields: dict) -> None:
    global recent_completed_trip
    recent_completed_trip = {
        "original_input": original_input,
        "collected_fields": dict(collected_fields),
        "approval_state": "pending" if _completed_fields_require_approval(collected_fields) else "not_requested",
    }


def _completed_fields_require_approval(collected_fields: dict) -> bool:
    timing = collected_fields.get("timing") or {}
    return bool(
        collected_fields.get("destination")
        and collected_fields.get("traveller_count") is not None
        and timing.get("state") == "exact_timing"
        and timing.get("start_date")
        and timing.get("end_date")
    )


def _resume_recent_approval(normalized_input: str) -> str | None:
    global recent_completed_trip

    if not recent_completed_trip:
        return None

    if recent_completed_trip.get("approval_state") != "pending":
        return None

    text = normalized_input.strip().lower()

    if text in APPROVAL_ACCEPT_COMMANDS:
        recent_completed_trip["approval_state"] = "approved"
        return _format_approval_continuation_prompt(
            workflow_state="execution_prep_ready",
            approval_state="approved",
            message="Approval recorded. Execution-prep may continue through the guarded adapter path.",
        )

    if text in APPROVAL_REJECT_COMMANDS:
        recent_completed_trip["approval_state"] = "rejected"
        return _format_approval_continuation_prompt(
            workflow_state="plan_ready_only",
            approval_state="rejected",
            message="Approval declined. Execution-prep remains blocked.",
        )

    return None


def _format_approval_continuation_prompt(
    *,
    workflow_state: str,
    approval_state: str,
    message: str,
) -> str:
    return (
        "Slate808 Output\n"
        "==============================\n\n"
        "Status: pass\n\n"
        "Operator Workflow:\n"
        f"- State: {workflow_state}\n"
        f"- Approval State: {approval_state}\n"
        f"- Human Approval Required: False\n"
        f"- Execution Prep Eligible: {workflow_state == 'execution_prep_ready'}\n\n"
        f"{message}\n"
        "=============================="
    )


def _collected_fields_from_brief(brief: dict) -> dict:
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
        if field == "timing":
            if value and value.get("state") != "missing_timing":
                collected_fields[field] = value
            continue
        if value:
            collected_fields[field] = value
    return collected_fields


def _get_indefinite_article(word: str) -> str:
    return "an" if re.match(r"^[aeiou]", word.strip().lower()) else "a"


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

    if trip_mood:
        article = _get_indefinite_article(trip_mood)
        rebuilt = f"Plan {article} {trip_mood} trip to {destination} for {traveller_phrase}"
    else:
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
    workflow_lines = _prompt_workflow_lines(state)
    if (
        not collected.get("trip_mood")
        and prompt != "What kind of trip mood should this have?"
    ):
        lines = ["", "=============================="]
        lines.extend(workflow_lines)
        lines.append(prompt)
        lines.append("==============================")
        return "\n".join(lines) + "\n"

    lines = ["Slate808 Output", "==============================", "", "Status: pass", ""]
    brief_lines = []

    if collected.get("destination"):
        brief_lines.append(f"- Destination: {format_destination_for_display(collected['destination'])}")
    if collected.get("traveller_count"):
        brief_lines.append(f"- Traveller Count: {collected['traveller_count']}")
    if collected.get("timing") and collected["timing"].get("state") != "missing_timing":
        brief_lines.append(f"- Timing: {format_timing_for_display(summarize_timing(collected['timing']))}")
    if collected.get("budget_amount") is not None:
        brief_lines.append(
            f"- Budget: {collected['budget_amount']} ({collected.get('budget_level', 'unspecified')})"
        )
    elif collected.get("budget_level") in {"low", "medium", "high"}:
        brief_lines.append(f"- Budget Level: {collected['budget_level']}")
    if collected.get("trip_mood"):
        brief_lines.append(f"- Trip Mood: {display_trip_mood(collected['trip_mood'])}")

    if brief_lines:
        lines.append("Travel Brief:")
        lines.extend(brief_lines)
        lines.append("")

    lines.extend(workflow_lines)
    if workflow_lines:
        lines.append("")

    lines.append("==============================")
    lines.append(prompt)
    lines.append("==============================")
    return "\n".join(lines)


def _format_session_control_prompt(prompt: str, workflow_state: str) -> str:
    return (
        "\n==============================\n"
        "Operator Workflow:\n"
        f"- State: {workflow_state}\n"
        f"{prompt}\n"
        "==============================\n"
    )


def _prompt_workflow_lines(state: dict | None) -> list[str]:
    if not state:
        return []

    workflow = map_operator_workflow(
        OperatorWorkflowInput(
            clarification_active=_has_meaningful_prompt_context(state.get("collected_fields", {})),
            clarification_needed=True,
            missing_fields=list(state.get("missing_fields") or []),
        )
    )
    return [
        "Operator Workflow:",
        f"- State: {workflow.state}",
    ]


def _has_meaningful_prompt_context(collected_fields: dict) -> bool:
    return any(
        value is not None and not (field == "budget_level" and value == "unspecified")
        for field, value in collected_fields.items()
    )


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


def get_console_state() -> dict:
    """Return a small read-only state snapshot for the operator console.

    This is intentionally narrow. It exposes enough state for the local console
    to explain what Slate is waiting for without leaking or mutating internals.
    """
    state = state_manager.get_state()

    if state and state.get("active"):
        collected_fields = state.get("collected_fields") or {}

        return {
            "active": True,
            "current_field": state.get("current_field"),
            "missing_fields": list(state.get("missing_fields") or []),
            "workflow_state": state.get("workflow_state") or "clarification_in_progress",
            "approval_state": "pending"
            if (recent_completed_trip or {}).get("approval_state") == "pending"
            else (recent_completed_trip or {}).get("approval_state", "not_requested"),
            "readiness_level": None,
            "blockers": [],
            "collected_fields": {
                key: value
                for key, value in collected_fields.items()
                if key in {"destination", "traveller_count", "budget_amount", "budget_level", "trip_mood"}
            },
        }

    approval_state = (recent_completed_trip or {}).get("approval_state", "not_requested")

    return {
        "active": False,
        "current_field": None,
        "missing_fields": [],
        "workflow_state": "idle",
        "approval_state": approval_state,
        "readiness_level": None,
        "blockers": [],
        "collected_fields": {},
    }
