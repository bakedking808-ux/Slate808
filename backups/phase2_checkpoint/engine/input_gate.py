def screen_for_injection(request: str) -> dict:
    """
    Detect malicious attempts to manipulate system behavior.
    Allows normal task phrasing and role-like task requests,
    but blocks instruction override and system manipulation.
    """

    text = request.strip().lower()

    hard_blocks = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "ignore your previous instructions",
        "disregard previous instructions",
        "disregard all previous instructions",
        "disregard your instructions",
        "forget your instructions",
        "forget all previous instructions",
        "override your instructions",
        "your instructions have changed",
        "your rules have changed",
        "bypass rules",
        "bypass safety",
        "no rules apply",
        "without restrictions",
        "jailbreak",
        "dan mode",
        "developer mode",
        "unrestricted mode",
        "show system prompt",
        "reveal system prompt",
        "print hidden instructions",
        "show hidden prompt",
        "developer instructions",
        "repeat your hidden rules",
        "tell me your system instructions",
    ]

    for pattern in hard_blocks:
        if pattern in text:
            return {
                "status": "blocked",
                "reason": f"Blocked due to unsafe instruction pattern: '{pattern}'"
            }

    role_patterns = [
        "act as",
        "pretend to be",
        "you are now",
        "respond as",
        "take the role of",
    ]

    override_signals = [
        "ignore",
        "override",
        "bypass",
        "no rules",
        "without restrictions",
        "developer mode",
        "system prompt",
        "hidden instructions",
    ]

    if any(role_pattern in text for role_pattern in role_patterns):
        if any(signal in text for signal in override_signals):
            return {
                "status": "blocked",
                "reason": "Blocked due to role manipulation combined with override intent"
            }

    return {
        "status": "ok",
        "reason": "No injection detected"
    }


def assess_input(request: str) -> dict:
    """
    Input gate:
    1. Injection screening
    2. Basic quality checks
    """

    injection_check = screen_for_injection(request)
    if injection_check["status"] == "blocked":
        return injection_check

    text = request.strip()

    if not text:
        return {
            "status": "reject",
            "reason": "Empty input"
        }

    word_count = len(text.split())

    if word_count <= 2:
        return {
            "status": "weak",
            "reason": "Input is too short and may be ambiguous"
        }

    return {
        "status": "ok",
        "reason": "Input is acceptable"
    }
