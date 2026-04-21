from engine.travel_brief import summarize_timing


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
    if clarification_needed and clarification_response:
        lines.append(clarification_response.strip())
        lines.append("")
        lines.append("==============================")
        return "\n".join(lines)

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
            lines.append(f"{index}. {step}")
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

    lines.append("==============================")
    return "\n".join(lines)
