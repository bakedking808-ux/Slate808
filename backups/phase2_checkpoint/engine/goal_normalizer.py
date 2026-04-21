import re


def normalize_goal(request: str) -> dict:
    """
    Clean the raw request into a simpler goal form before extraction/generation.

    Returns:
        {
            "raw_goal": original cleaned text,
            "goal_core": simplified version,
        }
    """
    text = request.strip().lower()

    # Remove soft helper phrasing that should not become the actual goal
    patterns_to_remove = [
        r"^guide me on\s+",
        r"^help me with\s+",
        r"^help me\s+",
        r"^show me how to\s+",
        r"^can you help me\s+",
        r"^can you\s+",
        r"^please\s+",
    ]

    for pattern in patterns_to_remove:
        text = re.sub(pattern, "", text).strip()

    # Normalize extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return {
        "raw_goal": request.strip(),
        "goal_core": text
    }
