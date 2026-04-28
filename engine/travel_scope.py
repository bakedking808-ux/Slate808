"""
Travel scope classifier for Slate808.

This module classifies broad travel scope only.
It must not provide live visa, health, safety, or entry-rule advice.
"""

from engine.destination_profiles import get_destination_profile


REGIONAL_DESTINATIONS = {
    "rwanda",
    "kigali",
    "uganda",
    "kampala",
    "tanzania",
    "arusha",
    "dar es salaam",
    "zanzibar",
    "ethiopia",
    "addis ababa",
}

INTERNATIONAL_DESTINATIONS = {
    "dubai",
    "bali",
    "paris",
    "london",
    "singapore",
    "thailand",
    "maldives",
    "seychelles",
    "mauritius",
    "south africa",
    "cape town",
}


def classify_travel_scope(destination: str | None) -> str:
    if not isinstance(destination, str) or not destination.strip():
        return "unknown"

    normalized = destination.strip().lower()

    _resolved, profile = get_destination_profile(normalized)
    if profile:
        return "domestic_kenya"

    if normalized in REGIONAL_DESTINATIONS:
        return "regional_cross_border"

    if normalized in INTERNATIONAL_DESTINATIONS:
        return "international"

    return "unknown"
