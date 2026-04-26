import re
from contracts.interpretation_outcome_contract import *

def interpret_input(text: str, context: InterpretationContext) -> InterpretationResult:
    # Approval continuation
    approval_result = interpret_approval(text, context)
    if approval_result:
        return approval_result
    # Month typo/correction
    month_correction = interpret_month_typo(text, context)
    if month_correction:
        return month_correction
    # Budget
    if context.active_field == InterpretationTargetField.BUDGET or 'budget' in text.lower():
        budget_result = interpret_budget(text, context)
        if budget_result:
            return budget_result
    # Timing
    if context.active_field == InterpretationTargetField.TIMING or re.search(r'\d', text):
        timing_result = interpret_timing(text, context)
        if timing_result:
            return timing_result
    # Resume answer for active clarification
    resume_result = interpret_resume_answer(text, context)
    if resume_result:
        return resume_result
    # Fallback
    return clarify_result(
        target_field=context.active_field or InterpretationTargetField.UNKNOWN,
        clarification_prompt="Could you clarify your request?",
        reason_code=InterpretationReasonCode.MISSING_PRECISION
    )

def interpret_timing(text: str, context: InterpretationContext) -> InterpretationResult | None:
    # Handle ambiguous date ranges like "4-8"
    if re.fullmatch(r"\d{1,2}\s*-\s*\d{1,2}", text.strip()):
        return correct_result(
            target_field=InterpretationTargetField.TIMING,
            correction_prompt="Please specify the month for your dates (e.g., 4-8 May).",
            reason_code=InterpretationReasonCode.MISSING_MONTH
        )
    # Handle valid date ranges like "4th-8th May", "23-30 August"
    if re.fullmatch(r"\d{1,2}(st|nd|rd|th)?-\d{1,2}(st|nd|rd|th)?\s+[A-Za-z]+", text.strip()):
        return interpret_result(
            target_field=InterpretationTargetField.TIMING,
            extracted_value=text.strip(),
            reason_code=InterpretationReasonCode.VALID_FIELD_ANSWER
        )
    if re.fullmatch(r"[A-Za-z]+\s+\d{1,2}-\d{1,2}", text.strip()):
        # Accept if month is valid, else correct
        month = text.strip().split()[0]
        if is_valid_month(month):
            return interpret_result(
                target_field=InterpretationTargetField.TIMING,
                extracted_value=text.strip(),
                reason_code=InterpretationReasonCode.VALID_FIELD_ANSWER
            )
        else:
            return correct_result(
                target_field=InterpretationTargetField.TIMING,
                correction_prompt=f"Please confirm the month. Did you mean {closest_month(month)}?",
                reason_code=InterpretationReasonCode.MALFORMED_MONTH
            )
    # Handle relative timing
    if re.search(r"next weekend|tomorrow|this coming|friday|sunday|morning|evening", text.lower()):
        return clarify_result(
            target_field=InterpretationTargetField.TIMING,
            clarification_prompt="Please provide the exact dates (e.g., 4-8 May).",
            reason_code=InterpretationReasonCode.MISSING_PRECISION
        )
    return None

def interpret_month_typo(text: str, context: InterpretationContext) -> InterpretationResult | None:
    # Detect malformed months
    typo_months = [
        "Augurts", "Agust", "Februry", "Jenuary", "Sebtember", "Novemba"
    ]
    for typo in typo_months:
        if typo.lower() in text.lower():
            return correct_result(
                target_field=InterpretationTargetField.TIMING,
                correction_prompt=f"Please confirm the month. Did you mean {closest_month(typo)}?",
                reason_code=InterpretationReasonCode.MALFORMED_MONTH
            )
    return None

def interpret_budget(text: str, context: InterpretationContext) -> InterpretationResult | None:
    # Acceptable: 80k, 30k, 80,000 (but NOT 80000K or 80,000K)
    cleaned = text.strip().replace(' ', '').lower()
    # Malformed: 80000K, 80,000K (full numeric value followed by K)
    if re.fullmatch(r"\d{5,}k", cleaned) or re.fullmatch(r"\d{2,},\d{3}k", cleaned):
        return correct_result(
            target_field=InterpretationTargetField.BUDGET,
            correction_prompt="Please enter the budget as either 80k or 80,000, not both.",
            reason_code=InterpretationReasonCode.MALFORMED_BUDGET
        )
    # Acceptable: 80k, 30k, 80,000
    m = re.fullmatch(r"(\d{1,3}(,\d{3})*|\d+)(k)?", cleaned)
    if m:
        val = m.group(1).replace(",", "")
        if m.group(3):
            val = int(val) * 1000
        else:
            val = int(val)
        return interpret_result(
            target_field=InterpretationTargetField.BUDGET,
            extracted_value=val,
            reason_code=InterpretationReasonCode.VALID_FIELD_ANSWER
        )
    # Budget level
    if "budget friendly" in text.lower():
        return interpret_result(
            target_field=InterpretationTargetField.BUDGET,
            extracted_value="budget_friendly",
            reason_code=InterpretationReasonCode.VALID_FIELD_ANSWER
        )
    # Budget range
    if re.search(r"\d+\s*-\s*\d+k", text.lower()):
        return clarify_result(
            target_field=InterpretationTargetField.BUDGET,
            clarification_prompt="Please specify a single budget amount.",
            reason_code=InterpretationReasonCode.BUDGET_RANGE_REQUIRES_CLARIFICATION
        )
    # Vague
    if "cheap" in text.lower():
        return clarify_result(
            target_field=InterpretationTargetField.BUDGET,
            clarification_prompt="Could you specify your budget amount?",
            reason_code=InterpretationReasonCode.MISSING_PRECISION
        )
    return None

def interpret_approval(text: str, context: InterpretationContext) -> InterpretationResult | None:
    approval_true = ["approved", "yes, approved", "yes approved"]
    approval_false = ["not approved", "declined"]
    if context.approval_expected:
        if text.strip().lower() in approval_true:
            return interpret_result(
                target_field=InterpretationTargetField.APPROVAL,
                extracted_value=True,
                reason_code=InterpretationReasonCode.APPROVAL_EXPECTED
            )
        if text.strip().lower() in approval_false:
            return interpret_result(
                target_field=InterpretationTargetField.APPROVAL,
                extracted_value=False,
                reason_code=InterpretationReasonCode.APPROVAL_EXPECTED
            )
    else:
        if text.strip().lower() in approval_true:
            return reject_result(
                target_field=InterpretationTargetField.APPROVAL,
                reason_code=InterpretationReasonCode.APPROVAL_NOT_EXPECTED
            )
    return None

def interpret_resume_answer(text: str, context: InterpretationContext) -> InterpretationResult | None:
    # Only if there is an active clarification
    if not context.has_active_clarification or not context.active_field:
        return None
    field = context.active_field
    if field == InterpretationTargetField.DESTINATION:
        if re.fullmatch(r"[A-Za-z ]+", text.strip()):
            return interpret_result(
                target_field=InterpretationTargetField.DESTINATION,
                extracted_value=text.strip().lower(),
                reason_code=InterpretationReasonCode.VALID_FIELD_ANSWER
            )
    if field == InterpretationTargetField.TRAVELLER_COUNT:
        m = re.search(r"(\d+)", text)
        if m:
            return interpret_result(
                target_field=InterpretationTargetField.TRAVELLER_COUNT,
                extracted_value=int(m.group(1)),
                reason_code=InterpretationReasonCode.VALID_FIELD_ANSWER
            )
    if field == InterpretationTargetField.BUDGET:
        # Route through budget interpreter, but allow for leading 'budget' word
        cleaned = text.strip().lower()
        if cleaned.startswith("budget"):
            # Remove leading 'budget' and any punctuation/space
            rest = cleaned[len("budget"):].lstrip(" :,-")
            if rest:
                return interpret_budget(rest, context)
        return interpret_budget(text, context)
    if field == InterpretationTargetField.MOOD:
        # Accept simple moods
        if any(mood in text.lower() for mood in ["quiet retreat", "adventure", "relaxing", "group fun", "romantic"]):
            return interpret_result(
                target_field=InterpretationTargetField.MOOD,
                extracted_value=text.strip().lower(),
                reason_code=InterpretationReasonCode.VALID_FIELD_ANSWER
            )
    if field == InterpretationTargetField.TIMING:
        return interpret_timing(text, context)
    return None

def is_valid_month(month: str) -> bool:
    months = [
        "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
    ]
    return month.lower() in months

def closest_month(typo: str) -> str:
    # Simple mapping for known typos
    mapping = {
        "Augurts": "August",
        "Agust": "August",
        "Februry": "February",
        "Jenuary": "January",
        "Sebtember": "September",
        "Novemba": "November"
    }
    return mapping.get(typo, "the correct month")
