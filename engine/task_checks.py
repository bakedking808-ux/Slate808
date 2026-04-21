"""
engine/task_checks.py
Task-aware checks layer for Slate808
"""


def apply_task_checks(plan: dict) -> dict:
    """
    Replace generic checks with task-relevant checks.
    """

    task_type = plan.get("task_type", "")

    if task_type == "trip":
        plan["checks"] = [
            "The journey should include a clear destination and smooth arrival",
            "Budget and travel arrangements should remain realistic and low-friction",
            "The trip should feel well-paced, with space for both experience and rest",
            "The ending should feel calm, complete, and memorable"
        ]

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
