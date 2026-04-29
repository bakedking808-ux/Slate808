from engine.travel_brief import summarize_timing
from engine.itinerary_renderer import render_draft_itinerary, should_render_draft_itinerary
from engine.display_language import display_trip_mood, polish_display_text, title_label


def format_destination_for_display(destination) -> str:
    return title_label(destination)


def format_timing_for_display(timing_summary: str) -> str:
    month_names = {
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    }

    parts = []
    for token in str(timing_summary).split(" "):
        normalized = token.lower()
        if normalized in month_names:
            parts.append(normalized[:1].upper() + normalized[1:])
        else:
            parts.append(token)
    return " ".join(parts)


def _polish_rendered_step(step: str, destination=None) -> str:
    replacements = (
        ("and keep the itinerary relaxed keep enough room for rest between activities", "and keep the itinerary relaxed while leaving room for rest between activities"),
        ("and align bookings and align premium bookings", "and align premium bookings"),
        ("and align team logistics efficiently confirm the shared schedule for the group", "and align team logistics efficiently while keeping the shared schedule coordinated"),
        ("with family-friendly and comfortable options; safe and practical choices", "with family-friendly, comfortable options"),
        ("with family-friendly and comfortable options; calm, practical choices", "with family-friendly, comfortable, and practical options"),
        ("with practical and safe movement; while keeping transfers easy and low-strain", "with safe, low-friction movement while keeping transfers easy and low-strain"),
        ("with practical and safe movement; using practical and cost-conscious routing", "with safe, cost-conscious routing"),
        ("with safe and practical choices", "with calm, practical choices"),
        ("and keep the itinerary relaxed while leaving room for rest between activities with heat-aware pacing and rest windows", "with a relaxed rhythm and heat-aware buffers"),
        ("Choose transport and stay options with simple transfers and relaxed pacing with urban transfers and traffic-aware movement planned in advance; using practical and cost-conscious routing; keeping transfers easy and low-strain", "Choose transport and stay options with relaxed pacing, traffic-aware movement, and cost-conscious routing"),
        ("Select relaxed activities that leave room for light pacing, quiet breaks, and recovery with time for dining, culture, and urban experiences; calm, practical choices; using simple and good-value options; that keep physical effort light; in quieter settings; fewer activities and more recovery time; a lighter arrival-day pace", "Select relaxed dining, culture, and light activities with quiet breaks and simple good-value options"),
        ("with heat-aware booking buffers and a relaxed rhythm keep enough room for rest between activities; departure transfer margin with transfer buffers for traffic-aware movement", "with relaxed timing, rest buffers, and traffic-aware departure margins"),
    )
    updated = step
    if destination:
        display_destination = format_destination_for_display(destination)
        raw_destination = str(destination).strip()
        lower_destination = raw_destination.lower()
        if lower_destination:
            updated = updated.replace(
                f"destination to {lower_destination}",
                f"destination to {display_destination}",
            )
            updated = updated.replace(
                f"for {lower_destination}",
                f"for {display_destination}",
            )
            updated = updated.replace(
                f"in {lower_destination}",
                f"in {display_destination}",
            )

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


def _format_bool(value) -> str:
    if value is True:
        return "True"
    if value is False:
        return "False"
    return "unknown"


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
        lines.append(f"- Destination: {format_destination_for_display(brief.get('destination'))}")
        lines.append(f"- Traveller Count: {brief.get('traveller_count')}")
        lines.append(f"- Timing: {format_timing_for_display(summarize_timing(brief.get('timing')))}")
        budget_amount = brief.get("budget_amount")
        budget_level = brief.get("budget_level")

        if budget_amount is not None:
            lines.append(f"- Budget: {budget_amount} ({budget_level})")
        else:
            lines.append(f"- Budget Level: {budget_level}")
        if brief.get("trip_mood"):
            lines.append(f"- Trip Mood: {display_trip_mood(brief.get('trip_mood'))}")
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
        lines.append("Plan Steps:")
        for index, step in enumerate(steps, start=1):
            lines.append(f"{index}. {_polish_rendered_step(step, (brief or {}).get('destination'))}")
        lines.append("")

    checks = final_output.get("checks", [])
    if checks:
        lines.append("Checks:")
        for check in checks:
            lines.append(f"- {polish_display_text(check)}")
        lines.append("")

    risks = final_output.get("risks", [])
    if risks:
        lines.append("Risks:")
        for risk in risks:
            lines.append(f"- {polish_display_text(risk)}")
        lines.append("")

    if should_render_draft_itinerary(final_output):
        lines.append("Draft Itinerary:")
        for item in render_draft_itinerary(final_output):
            lines.append(polish_display_text(item))
        lines.append("")

    execution_readiness = final_output.get("execution_readiness")
    if execution_readiness:
        lines.append("Execution Readiness:")
        lines.append(f"- Level: {execution_readiness.get('readiness_level')}")
        lines.append(f"- Plan Ready: {execution_readiness.get('plan_ready')}")
        lines.append(f"- Execution Ready: {execution_readiness.get('execution_ready')}")
        requested_action = execution_readiness.get("requested_action")
        action_allowed = execution_readiness.get("action_allowed")
        if execution_readiness.get("plan_ready") and not execution_readiness.get("execution_ready"):
            if requested_action and action_allowed is True:
                lines.append("- Readiness Note: Requested action is allowed; execution-prep actions remain blocked.")
            else:
                lines.append("- Readiness Note: Plan output is available, but execution actions are blocked.")
        if requested_action:
            lines.append(f"- Requested Action: {requested_action}")
            lines.append(f"- Action Allowed: {action_allowed}")
        blocking_reasons = execution_readiness.get("blocking_reasons") or []
        if blocking_reasons:
            details_label = "Execution Limitation Details:" if action_allowed is True else "Execution Block Details:"
            blocks_label = "Execution Limitations:" if action_allowed is True else "Execution Blocks:"
            lines.append(details_label)
            for reason in blocking_reasons:
                lines.append(f"- {_readiness_block_label(reason)}")
            lines.append(blocks_label)
            for reason in blocking_reasons:
                lines.append(f"- {reason}")
        lines.append("")

    operator_workflow = final_output.get("operator_workflow")
    handoff_packet = final_output.get("handoff_packet") or {}
    if operator_workflow:
        lines.append("Operator Workflow:")
        lines.append(f"- State: {operator_workflow.get('state')}")
        lines.append(f"- Human Approval Required: {_format_bool(operator_workflow.get('requires_human_approval'))}")
        lines.append(f"- Execution Prep Eligible: {_format_bool(operator_workflow.get('execution_prep_eligible'))}")
        requested_action = handoff_packet.get("requested_action")
        if requested_action:
            lines.append(f"- Requested Action: {requested_action}")
            lines.append(f"- Action Allowed: {_format_bool(handoff_packet.get('action_allowed'))}")
        guidance = handoff_packet.get("recovery_guidance") or {}
        if guidance:
            lines.append(f"- Recovery Next Step: {guidance.get('next_operator_action')}")
            lines.append(f"- Recovery State: {guidance.get('return_state')}")
            lines.append(f"- Recovery Guidance: {guidance.get('message')}")
        lines.append("")

    if handoff_packet:
        lines.append("Handoff Summary:")
        lines.append(f"- Workflow State: {handoff_packet.get('operator_workflow_state')}")
        lines.append(f"- Blockers: {len(handoff_packet.get('blockers') or [])}")
        lines.append(f"- Plan Steps: {len(handoff_packet.get('steps') or [])}")
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
