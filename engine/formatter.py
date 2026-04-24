from engine.travel_brief import summarize_timing


def _polish_rendered_step(step: str) -> str:
    replacements = (
        ("and keep the itinerary relaxed keep enough room for rest between activities", "and keep the itinerary relaxed while leaving room for rest between activities"),
        ("and align bookings and align premium bookings", "and align premium bookings"),
        ("and align team logistics efficiently confirm the shared schedule for the group", "and align team logistics efficiently while keeping the shared schedule coordinated"),
        ("with family-friendly and comfortable options; safe and practical choices", "with family-friendly, comfortable options"),
        ("with practical and safe movement; while keeping transfers easy and low-strain", "with safe, low-friction movement while keeping transfers easy and low-strain"),
        ("with practical and safe movement; using practical and cost-conscious routing", "with safe, cost-conscious routing"),
        ("with safe and practical choices", "with safety and comfort in mind"),
    )
    updated = step
    for old, new in replacements:
        updated = updated.replace(old, new)
    return updated


def _readiness_block_label(reason: str) -> str:
    labels = {
        "missing_destination": "Destination is required before execution actions are allowed.",
        "missing_traveller_count": "Traveller count is required before execution actions are allowed.",
        "execution_timing_missing_date_range": "Exact start and end dates are required before execution actions are allowed.",
    }
    if reason.startswith("execution_timing_not_exact:"):
        timing_state = reason.split(":", 1)[1]
        return f"Exact timing is required before execution actions are allowed; current timing is {timing_state}."
    return reason


def format_output(final_output: dict) -> str:
    lines = []
    lines.append("Slate808 Output")
    lines.append("==============================")
    lines.append("")
    lines.append(f"Status: {final_output.get('status', 'unknown')}")
    lines.append("")

    errors = final_output.get("errors", [])
    if errors:
        lines.append("Errors:")
        for error in errors:
            lines.append(f"- {error}")
        lines.append("")

    goal = final_output.get("goal")
    if goal:
        lines.append("Goal:")
        lines.append(str(goal))
        lines.append("")

    clarification_needed = final_output.get("clarification_needed")
    clarification_response = final_output.get("clarification_response")

    brief = final_output.get("brief")
    if brief:
        lines.append("Travel Brief:")
        lines.append(f"- Destination: {brief.get('destination')}")
        lines.append(f"- Traveller Count: {brief.get('traveller_count')}")
        lines.append(f"- Timing: {summarize_timing(brief.get('timing'))}")
        budget_amount = brief.get("budget_amount")
        budget_level = brief.get("budget_level")

        if budget_amount is not None:
            lines.append(f"- Budget: {budget_amount} ({budget_level})")
        else:
            lines.append(f"- Budget Level: {budget_level}")
        if brief.get("trip_mood"):
            lines.append(f"- Trip Mood: {brief.get('trip_mood')}")
        lines.append("")

        gaps = []
        if brief.get("budget_level") == "unspecified":
            gaps.append("Budget Level is unspecified")

        if gaps:
            lines.append("Brief Gaps:")
            for gap in gaps:
                lines.append(f"- {gap}")
            lines.append("")

    steps = final_output.get("steps", [])
    if steps:
        lines.append("Steps:")
        for index, step in enumerate(steps, start=1):
            lines.append(f"{index}. {_polish_rendered_step(step)}")
        lines.append("")

    checks = final_output.get("checks", [])
    if checks:
        lines.append("Checks:")
        for check in checks:
            lines.append(f"- {check}")
        lines.append("")

    risks = final_output.get("risks", [])
    if risks:
        lines.append("Risks:")
        for risk in risks:
            lines.append(f"- {risk}")
        lines.append("")

    execution_readiness = final_output.get("execution_readiness")
    if execution_readiness:
        lines.append("Execution Readiness:")
        lines.append(f"- Level: {execution_readiness.get('readiness_level')}")
        lines.append(f"- Plan Ready: {execution_readiness.get('plan_ready')}")
        lines.append(f"- Execution Ready: {execution_readiness.get('execution_ready')}")
        if execution_readiness.get("plan_ready") and not execution_readiness.get("execution_ready"):
            lines.append("- Readiness Note: Plan output is available, but execution actions are blocked.")
        requested_action = execution_readiness.get("requested_action")
        if requested_action:
            lines.append(f"- Requested Action: {requested_action}")
            lines.append(f"- Action Allowed: {execution_readiness.get('action_allowed')}")
        blocking_reasons = execution_readiness.get("blocking_reasons") or []
        if blocking_reasons:
            lines.append("Execution Block Details:")
            for reason in blocking_reasons:
                lines.append(f"- {_readiness_block_label(reason)}")
            lines.append("Execution Blocks:")
            for reason in blocking_reasons:
                lines.append(f"- {reason}")
        lines.append("")

    if clarification_needed and clarification_response:
        if lines:
            lines.append("")
        lines.append("==============================")
        lines.append(clarification_response.strip())
        lines.append("==============================")
        return "\n".join(lines)

    lines.append("==============================")
    return "\n".join(lines)
