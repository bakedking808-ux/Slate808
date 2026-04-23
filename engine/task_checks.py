"""
engine/task_checks.py
Task-aware checks layer for Slate808
"""


def _trip_checks_and_risks(plan: dict) -> tuple[list[str], list[str]]:
    brief = plan.get("brief") or {}
    destination = brief.get("destination") or "the destination"
    budget_level = brief.get("budget_level")
    trip_mood = brief.get("trip_mood")
    timing_state = ((brief.get("timing") or {}).get("state")) or "missing_timing"

    checks = [
        f"Arrival and local movement should stay practical for {destination}",
        "Spending choices should stay realistic for the transport, stay, and activity mix",
        "The pace and activities should fit the group and the purpose of the trip",
        "Timing should support the plan without forcing rushed bookings or transfers",
    ]
    risks = [
        "Costs may drift if the main spending decisions are not confirmed early",
        "The plan can lose coherence if transport, stay, and activity timing are confirmed too late",
    ]

    if trip_mood == "family":
        checks[2] = "Activities and transfers should stay comfortable for the whole family"
        risks[1] = "Tight transfers or overpacked activities can wear out the family group"
    elif trip_mood == "corporate":
        checks[2] = "Group logistics and activities should stay coordinated for the team"
        risks[1] = "Group coordination can slip if meeting points and timing are not confirmed early"
    elif trip_mood == "relaxed":
        checks[2] = "The pace should stay calm enough for rest between movements and activities"
        risks[1] = "A packed schedule can undercut the slower pace the trip needs"
    elif trip_mood == "luxury":
        checks[2] = "Transport, stay, and experiences should feel consistent with a premium trip"
        risks[1] = "Premium experiences may lose quality if key bookings are confirmed too late"

    if budget_level == "low":
        checks[1] = "Lower-cost transport, stay, and activity choices should remain practical and consistent"
        risks[0] = "Lower-cost options may narrow quickly if bookings are left too late"
    elif budget_level == "high":
        checks[1] = "Premium spending should still map cleanly to the trip priorities and timing"
        risks[0] = "Premium bookings may need early confirmation to avoid last-minute compromises"
    elif budget_level == "unspecified":
        checks[1] = "Budget assumptions should be set before transport and stay decisions are locked in"
        risks[0] = "Costs may drift quickly while the budget remains unspecified"

    if timing_state != "exact_timing":
        checks[3] = "Timing should be confirmed clearly enough to support realistic booking decisions"
        risks[1] = "Bookings may remain provisional until the exact travel dates are confirmed"

    return checks, risks


def apply_task_checks(plan: dict) -> dict:
    """
    Replace generic checks with task-relevant checks.
    """

    task_type = plan.get("task_type", "")

    if task_type == "trip":
        plan["checks"], plan["risks"] = _trip_checks_and_risks(plan)

    elif task_type == "study":
        plan["checks"] = [
            "The study plan should include a clear subject and realistic duration",
            "Materials should be prepared before the study session begins",
            "The session should stay focused without feeling overloaded",
            "The ending should include a short review of what was learned"
        ]

    elif task_type == "meeting":
        plan["checks"] = [
            "The meeting should include the right participants and a clear purpose",
            "Timing should be realistic and easy to follow",
            "Discussion points should stay focused and relevant",
            "The meeting should close with clear next steps"
        ]

    elif task_type == "shopping":
        plan["checks"] = [
            "The shopping plan should include the needed items and a clear budget",
            "Store choices should be practical and easy to access",
            "The trip should avoid unnecessary back-and-forth movement",
            "The final list should feel complete without excess"
        ]

    elif task_type == "cleaning":
        plan["checks"] = [
            "The cleaning plan should clearly identify the target areas",
            "Tools and supplies should be ready before starting",
            "The work should move in a logical and efficient sequence",
            "The final result should feel complete and easy to maintain"
        ]

    else:
        plan["checks"] = [
            "The goal should be clear and easy to act on",
            "The steps should remain logical and manageable",
            "Resources and preparation should be considered before execution",
            "The ending should include a simple review or closing step"
        ]

    return plan
