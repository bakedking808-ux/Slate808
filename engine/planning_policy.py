from __future__ import annotations

from typing import Any, Dict, List

from engine.constraints import ConstraintPolicy
from engine.planning_constraints import PlanningConstraints
from engine.logger import append_log
from engine.travel_brief import is_timing_usable, summarize_timing


SUPPORTED_MOODS = {
    "relaxed",
    "adventure",
    "luxury",
    "romantic",
    "family",
    "corporate",
}

DESTINATION_ALIASES: dict[str, str] = {
    "mount kenya": "mt kenya",
    "mt kenya": "mt kenya",
    "masai mara": "maasai mara",
    "mara": "maasai mara",
    "lake naivasha": "naivasha",
    "lake nakuru": "nakuru",
    "ngare dare": "ngare ndare",
}

DESTINATION_PROFILES: dict[str, dict[str, Any]] = {
    "diani": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "relaxation"],
        "transport_bias": "road_or_air_connection",
        "accommodation_bias": "resort_or_beachfront",
        "pace_bias": "relaxed",
        "risk_flags": ["heat", "weekend_crowds"],
    },
    "mombasa": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "culture"],
        "transport_bias": "road_or_air_connection",
        "accommodation_bias": "resort_or_city_hotel",
        "pace_bias": "balanced",
        "risk_flags": ["traffic", "heat"],
    },
    "watamu": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "relaxation"],
        "transport_bias": "road_or_air_connection",
        "accommodation_bias": "resort_or_beachfront",
        "pace_bias": "relaxed",
        "risk_flags": ["heat"],
    },
    "malindi": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "culture"],
        "transport_bias": "road_or_air_connection",
        "accommodation_bias": "resort_or_beachfront",
        "pace_bias": "balanced",
        "risk_flags": ["heat"],
    },
    "lamu": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "culture", "relaxation"],
        "transport_bias": "air_or_boat_connection",
        "accommodation_bias": "boutique_or_beachfront",
        "pace_bias": "slow",
        "risk_flags": ["boat_transfer", "heat"],
    },
    "kilifi": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "relaxation"],
        "transport_bias": "road_connection",
        "accommodation_bias": "resort_or_beachfront",
        "pace_bias": "relaxed",
        "risk_flags": ["heat"],
    },
    "vipingo": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "relaxation", "scenic"],
        "transport_bias": "road_connection",
        "accommodation_bias": "villa_or_resort",
        "pace_bias": "relaxed",
        "risk_flags": ["heat"],
    },
    "tiwi": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "quiet"],
        "transport_bias": "road_connection",
        "accommodation_bias": "beachfront",
        "pace_bias": "slow",
        "risk_flags": ["heat"],
    },
    "nyali": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "urban"],
        "transport_bias": "road_connection",
        "accommodation_bias": "resort_or_city_hotel",
        "pace_bias": "balanced",
        "risk_flags": ["traffic", "heat"],
    },
    "shanzu": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "relaxation"],
        "transport_bias": "road_connection",
        "accommodation_bias": "resort_or_beachfront",
        "pace_bias": "relaxed",
        "risk_flags": ["heat"],
    },
    "bamburi": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "urban"],
        "transport_bias": "road_connection",
        "accommodation_bias": "resort_or_city_hotel",
        "pace_bias": "balanced",
        "risk_flags": ["traffic", "heat"],
    },
    "mtwapa": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "urban"],
        "transport_bias": "road_connection",
        "accommodation_bias": "hotel_or_apartment",
        "pace_bias": "balanced",
        "risk_flags": ["traffic", "heat"],
    },
    "ukunda": {
        "destination_type": "coastal",
        "activity_bias": ["beach", "water", "relaxation"],
        "transport_bias": "road_or_air_connection",
        "accommodation_bias": "resort_or_beachfront",
        "pace_bias": "relaxed",
        "risk_flags": ["heat"],
    },
    "mt kenya": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "lodge_or_cabin",
        "pace_bias": "active",
        "risk_flags": ["altitude", "cold_nights"],
    },
    "aberdare": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "lodge_or_cabin",
        "pace_bias": "active",
        "risk_flags": ["cold_nights", "rain"],
    },
    "aberdares": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "lodge_or_cabin",
        "pace_bias": "active",
        "risk_flags": ["cold_nights", "rain"],
    },
    "longonot": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "active",
        "risk_flags": ["steep_trails", "heat"],
    },
    "mt longonot": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "active",
        "risk_flags": ["steep_trails", "heat"],
    },
    "suswa": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "active",
        "risk_flags": ["rough_access", "heat"],
    },
    "mt suswa": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "active",
        "risk_flags": ["rough_access", "heat"],
    },
    "ngong hills": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "day_trip_or_lodge",
        "pace_bias": "active",
        "risk_flags": ["wind", "exposure"],
    },
    "mt elgon": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "lodge_or_cabin",
        "pace_bias": "active",
        "risk_flags": ["altitude", "distance"],
    },
    "cherangani": {
        "destination_type": "mountain",
        "activity_bias": ["hiking", "nature", "outdoor"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "active",
        "risk_flags": ["distance", "cold_nights"],
    },
    "nairobi": {
        "destination_type": "city",
        "activity_bias": ["urban", "dining", "culture", "logistics"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "fast",
        "risk_flags": ["traffic"],
    },
    "kisumu": {
        "destination_type": "city",
        "activity_bias": ["urban", "dining", "culture", "logistics"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "balanced",
        "risk_flags": ["traffic"],
    },
    "nakuru": {
        "destination_type": "city",
        "activity_bias": ["urban", "dining", "culture", "logistics"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "balanced",
        "risk_flags": ["traffic"],
    },
    "eldoret": {
        "destination_type": "city",
        "activity_bias": ["urban", "dining", "culture", "logistics"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "balanced",
        "risk_flags": [],
    },
    "thika": {
        "destination_type": "city",
        "activity_bias": ["urban", "dining", "culture", "logistics"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "balanced",
        "risk_flags": ["traffic"],
    },
    "nyeri": {
        "destination_type": "city",
        "activity_bias": ["urban", "culture", "logistics"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "balanced",
        "risk_flags": [],
    },
    "meru": {
        "destination_type": "city",
        "activity_bias": ["urban", "culture", "logistics"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "balanced",
        "risk_flags": [],
    },
    "nanyuki": {
        "destination_type": "city",
        "activity_bias": ["urban", "dining", "logistics"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "balanced",
        "risk_flags": [],
    },
    "kitale": {
        "destination_type": "city",
        "activity_bias": ["urban", "dining", "logistics"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "balanced",
        "risk_flags": [],
    },
    "maasai mara": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "airstrip_or_4x4",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "early_start",
        "risk_flags": ["distance", "rough_access"],
    },
    "amboseli": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "early_start",
        "risk_flags": ["dust", "distance"],
    },
    "tsavo": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "early_start",
        "risk_flags": ["distance", "heat"],
    },
    "tsavo east": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "early_start",
        "risk_flags": ["distance", "heat"],
    },
    "tsavo west": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "early_start",
        "risk_flags": ["distance", "heat"],
    },
    "samburu": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "airstrip_or_4x4",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "early_start",
        "risk_flags": ["distance", "heat"],
    },
    "shaba": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "airstrip_or_4x4",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "early_start",
        "risk_flags": ["distance", "heat"],
    },
    "meru national park": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "early_start",
        "risk_flags": ["distance", "rough_access"],
    },
    "nairobi national park": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "city_hotel",
        "pace_bias": "balanced",
        "risk_flags": ["traffic"],
    },
    "ol pejeta": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "early_start",
        "risk_flags": ["distance"],
    },
    "solio": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "lodge",
        "pace_bias": "balanced",
        "risk_flags": ["distance"],
    },
    "lake nakuru national park": {
        "destination_type": "safari",
        "activity_bias": ["wildlife", "game_drive", "photography"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "lodge",
        "pace_bias": "balanced",
        "risk_flags": ["park_hours"],
    },
    "naivasha": {
        "destination_type": "lake",
        "activity_bias": ["boat", "nature", "relaxation"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "lodge_or_lakeside",
        "pace_bias": "relaxed",
        "risk_flags": ["weekend_crowds"],
    },
    "lake victoria": {
        "destination_type": "lake",
        "activity_bias": ["boat", "nature", "relaxation"],
        "transport_bias": "road_or_air_connection",
        "accommodation_bias": "hotel_or_lakeside",
        "pace_bias": "balanced",
        "risk_flags": ["weather_exposure"],
    },
    "baringo": {
        "destination_type": "lake",
        "activity_bias": ["boat", "nature", "relaxation"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "lodge_or_lakeside",
        "pace_bias": "relaxed",
        "risk_flags": ["distance", "heat"],
    },
    "elementaita": {
        "destination_type": "lake",
        "activity_bias": ["nature", "relaxation", "scenic"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "lodge_or_lakeside",
        "pace_bias": "relaxed",
        "risk_flags": [],
    },
    "bogoria": {
        "destination_type": "lake",
        "activity_bias": ["nature", "scenic", "relaxation"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "lodge",
        "pace_bias": "balanced",
        "risk_flags": ["heat", "distance"],
    },
    "karura": {
        "destination_type": "forest",
        "activity_bias": ["trail", "nature", "quiet"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "day_trip_or_city_hotel",
        "pace_bias": "slow",
        "risk_flags": [],
    },
    "karura forest": {
        "destination_type": "forest",
        "activity_bias": ["trail", "nature", "quiet"],
        "transport_bias": "urban_road_transfer",
        "accommodation_bias": "day_trip_or_city_hotel",
        "pace_bias": "slow",
        "risk_flags": [],
    },
    "arabuko sokoke": {
        "destination_type": "forest",
        "activity_bias": ["trail", "nature", "quiet"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "eco_lodge",
        "pace_bias": "slow",
        "risk_flags": ["heat"],
    },
    "kakamega forest": {
        "destination_type": "forest",
        "activity_bias": ["trail", "nature", "quiet"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "eco_lodge",
        "pace_bias": "slow",
        "risk_flags": ["rain"],
    },
    "ngare ndare": {
        "destination_type": "forest",
        "activity_bias": ["trail", "nature", "quiet"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "camp_or_lodge",
        "pace_bias": "balanced",
        "risk_flags": ["distance"],
    },
    "aberdare forest": {
        "destination_type": "forest",
        "activity_bias": ["trail", "nature", "quiet"],
        "transport_bias": "road_transfer",
        "accommodation_bias": "lodge_or_cabin",
        "pace_bias": "balanced",
        "risk_flags": ["rain", "cold_nights"],
    },
    "isiolo": {
        "destination_type": "arid",
        "activity_bias": ["rugged", "remote", "scenic"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "basic_lodge",
        "pace_bias": "steady",
        "risk_flags": ["heat", "distance"],
    },
    "marsabit": {
        "destination_type": "arid",
        "activity_bias": ["rugged", "remote", "scenic"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "basic_lodge",
        "pace_bias": "steady",
        "risk_flags": ["heat", "distance"],
    },
    "turkana": {
        "destination_type": "arid",
        "activity_bias": ["rugged", "remote", "scenic"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "basic_lodge",
        "pace_bias": "steady",
        "risk_flags": ["heat", "distance"],
    },
    "lodwar": {
        "destination_type": "arid",
        "activity_bias": ["rugged", "remote", "scenic"],
        "transport_bias": "road_or_4x4",
        "accommodation_bias": "basic_lodge",
        "pace_bias": "steady",
        "risk_flags": ["heat", "distance"],
    },
    "chalbi": {
        "destination_type": "arid",
        "activity_bias": ["rugged", "remote", "scenic"],
        "transport_bias": "4x4_required",
        "accommodation_bias": "camp",
        "pace_bias": "steady",
        "risk_flags": ["heat", "remote_access"],
    },
    "chalbi desert": {
        "destination_type": "arid",
        "activity_bias": ["rugged", "remote", "scenic"],
        "transport_bias": "4x4_required",
        "accommodation_bias": "camp",
        "pace_bias": "steady",
        "risk_flags": ["heat", "remote_access"],
    },
}


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def normalize_destination_name(destination: str | None) -> str | None:
    cleaned = _normalize_text(destination)
    if not cleaned:
        return None
    return DESTINATION_ALIASES.get(cleaned, cleaned)


def _budget_amount_band(amount: int | None) -> str:
    if amount is None:
        return "unknown"
    if amount <= 30000:
        return "low"
    if amount <= 100000:
        return "medium"
    return "high"


def _derive_budget_posture(budget_level: str, budget_amount: int | None) -> str:
    if budget_amount is not None:
        if budget_amount <= 30000:
            return "cost_sensitive"
        if budget_amount <= 100000:
            return "balanced"
        return "premium"

    if budget_level == "low":
        return "cost_sensitive"
    if budget_level == "medium":
        return "balanced"
    if budget_level == "high":
        return "premium"

    return "unknown"


def derive_budget_policy(brief: Dict[str, Any]) -> Dict[str, Any]:
    budget_amount = _safe_int(brief.get("budget_amount"))
    budget_level = _normalize_text(brief.get("budget_level")) or "unspecified"
    posture = _derive_budget_posture(budget_level, budget_amount)

    is_budget_known = budget_amount is not None or budget_level != "unspecified"

    should_avoid_premium = posture in {"cost_sensitive", "balanced"}
    should_require_cost_check = posture in {"cost_sensitive", "balanced", "unknown"}
    should_prioritize_value = posture == "cost_sensitive"
    should_allow_premium = posture == "premium"

    return {
        "is_budget_known": is_budget_known,
        "budget_amount": budget_amount,
        "budget_level": budget_level,
        "budget_amount_band": _budget_amount_band(budget_amount),
        "budget_posture": posture,
        "should_avoid_premium": should_avoid_premium,
        "should_require_cost_check": should_require_cost_check,
        "should_prioritize_value": should_prioritize_value,
        "should_allow_premium": should_allow_premium,
    }


def derive_destination_policy(brief: Dict[str, Any]) -> Dict[str, Any]:
    resolved_destination = normalize_destination_name(brief.get("destination"))
    profile = DESTINATION_PROFILES.get(resolved_destination)

    if not profile and resolved_destination:
        for key in DESTINATION_PROFILES:
            if key in resolved_destination:
                profile = DESTINATION_PROFILES[key]
                resolved_destination = key
                break

    if not profile:
        return {
            "resolved_destination": resolved_destination,
            "destination_type": "mixed_or_unknown",
            "activity_bias": ["general"],
            "transport_bias": "standard",
            "accommodation_bias": "standard",
            "pace_bias": "balanced",
            "risk_flags": [],
        }

    return {
        "resolved_destination": resolved_destination,
        "destination_type": profile["destination_type"],
        "activity_bias": list(profile["activity_bias"]),
        "transport_bias": profile["transport_bias"],
        "accommodation_bias": profile["accommodation_bias"],
        "pace_bias": profile["pace_bias"],
        "risk_flags": list(profile["risk_flags"]),
    }


def _infer_group_type(traveller_count: int | None, trip_mood: str | None) -> str:
    if trip_mood == "family":
        return "family"
    if trip_mood == "corporate":
        return "team"
    if traveller_count is None:
        return "unknown"
    if traveller_count == 1:
        return "solo"
    if traveller_count == 2:
        return "pair"
    if 3 <= traveller_count <= 5:
        return "small_group"
    return "large_group"


def _infer_activity_intensity(trip_mood: str | None, group_type: str) -> str:
    if trip_mood == "adventure":
        return "high"
    if trip_mood == "relaxed":
        return "low"
    if trip_mood == "family":
        return "moderate"
    if trip_mood == "corporate":
        return "moderate"
    if trip_mood == "luxury":
        return "low"
    if trip_mood == "romantic":
        return "low"

    if group_type in {"large_group", "team", "family"}:
        return "moderate"
    return "moderate"


def derive_traveller_policy(brief: Dict[str, Any]) -> Dict[str, Any]:
    traveller_count = _safe_int(brief.get("traveller_count"))
    trip_mood = _normalize_text(brief.get("trip_mood"))
    group_type = _infer_group_type(traveller_count, trip_mood)

    has_children = trip_mood == "family"
    needs_family_safe_planning = has_children or group_type == "family"
    needs_group_coordination = group_type in {"small_group", "large_group", "team", "family"}
    should_reduce_complexity = group_type in {"large_group", "family", "team"}

    return {
        "traveller_count": traveller_count,
        "group_type": group_type,
        "has_children": has_children,
        "needs_family_safe_planning": needs_family_safe_planning,
        "needs_group_coordination": needs_group_coordination,
        "should_reduce_complexity": should_reduce_complexity,
        "activity_intensity": _infer_activity_intensity(trip_mood, group_type),
    }


def _default_mood_policy() -> Dict[str, Any]:
    return {
        "trip_mood": None,
        "preferred_activity_tags": [],
        "avoid_activity_tags": [],
        "transport_style": "standard",
        "pace": "balanced",
        "experience_style": "general",
    }


def derive_mood_policy(brief: Dict[str, Any]) -> Dict[str, Any]:
    trip_mood = _normalize_text(brief.get("trip_mood"))

    if not trip_mood or trip_mood not in SUPPORTED_MOODS:
        return _default_mood_policy()

    if trip_mood == "relaxed":
        return {
            "trip_mood": trip_mood,
            "preferred_activity_tags": ["scenic", "calm", "nature", "restful"],
            "avoid_activity_tags": ["extreme", "rushed", "crowded"],
            "transport_style": "smooth",
            "pace": "slow",
            "experience_style": "restorative",
        }

    if trip_mood == "adventure":
        return {
            "trip_mood": trip_mood,
            "preferred_activity_tags": ["outdoor", "active", "exploration", "adventure"],
            "avoid_activity_tags": ["sedentary", "passive"],
            "transport_style": "mobile",
            "pace": "active",
            "experience_style": "exploratory",
        }

    if trip_mood == "luxury":
        return {
            "trip_mood": trip_mood,
            "preferred_activity_tags": ["premium", "curated", "comfort", "exclusive"],
            "avoid_activity_tags": ["basic", "crowded", "rough"],
            "transport_style": "premium",
            "pace": "smooth",
            "experience_style": "elevated",
        }

    if trip_mood == "romantic":
        return {
            "trip_mood": trip_mood,
            "preferred_activity_tags": ["intimate", "scenic", "private", "shared"],
            "avoid_activity_tags": ["noisy", "crowded", "rushed"],
            "transport_style": "comfortable",
            "pace": "slow",
            "experience_style": "shared",
        }

    if trip_mood == "family":
        return {
            "trip_mood": trip_mood,
            "preferred_activity_tags": ["family_friendly", "comfortable", "practical", "safe"],
            "avoid_activity_tags": ["extreme", "late_night", "complex"],
            "transport_style": "practical",
            "pace": "moderate",
            "experience_style": "family_safe",
        }

    if trip_mood == "corporate":
        return {
            "trip_mood": trip_mood,
            "preferred_activity_tags": ["structured", "coordinated", "team", "efficient"],
            "avoid_activity_tags": ["chaotic", "unstructured", "high_friction"],
            "transport_style": "coordinated",
            "pace": "efficient",
            "experience_style": "organized",
        }

    return _default_mood_policy()


def _derive_timing_specificity(timing: Dict[str, Any]) -> str:
    state = _normalize_text(timing.get("state")) or "missing_timing"

    if state == "exact_timing":
        return "high"
    if state in {"relative_timing", "duration_only"}:
        return "medium"
    if state == "month_only":
        return "low"
    return "unknown"


def _derive_planning_confidence(timing: Dict[str, Any]) -> str:
    raw_confidence = _normalize_text(timing.get("confidence"))
    if raw_confidence in {"low", "medium", "high"}:
        return raw_confidence
    return "low"


def derive_timing_policy(brief: Dict[str, Any]) -> Dict[str, Any]:
    timing = brief.get("timing") or {}
    state = _normalize_text(timing.get("state")) or "missing_timing"
    usable = is_timing_usable(timing)
    timing_summary = summarize_timing(timing)

    is_exact = state == "exact_timing"
    is_relative = state == "relative_timing"
    is_duration_only = state == "duration_only"
    is_month_only = state == "month_only"

    should_generate_concrete_plan = usable
    should_request_dates_within_month = is_month_only
    should_treat_as_provisional = state in {"month_only", "vague_timing", "missing_timing"}
    should_anchor_to_duration = is_duration_only

    return {
        "timing_state": state,
        "timing_summary": timing_summary,
        "is_timing_usable": usable,
        "is_exact_timing": is_exact,
        "is_relative_timing": is_relative,
        "is_duration_only": is_duration_only,
        "is_month_only": is_month_only,
        "timing_specificity": _derive_timing_specificity(timing),
        "planning_confidence": _derive_planning_confidence(timing),
        "should_generate_concrete_plan": should_generate_concrete_plan,
        "should_treat_as_provisional": should_treat_as_provisional,
        "should_request_dates_within_month": should_request_dates_within_month,
        "should_anchor_to_duration": should_anchor_to_duration,
    }


def derive_constraint_policy(brief: Dict[str, Any]) -> Dict[str, Any]:
    traveller_count = _safe_int(brief.get("traveller_count"))
    trip_mood = _normalize_text(brief.get("trip_mood"))
    budget_amount = _safe_int(brief.get("budget_amount"))
    budget_level = _normalize_text(brief.get("budget_level")) or "unspecified"
    budget_posture = _derive_budget_posture(budget_level, budget_amount)
    timing = brief.get("timing") or {}
    timing_state = _normalize_text(timing.get("state")) or "missing_timing"

    policy = ConstraintPolicy(
        family_safe=trip_mood == "family",
        low_risk=trip_mood in {"family", "relaxed"} or timing_state == "month_only",
        avoid_premium=budget_posture in {"cost_sensitive", "balanced"},
        value_focused=budget_posture == "cost_sensitive",
        group_coordination=traveller_count is not None and traveller_count >= 4,
        kids_present=trip_mood == "family",
        low_mobility=trip_mood == "relaxed",
        quiet_preferred=trip_mood in {"relaxed", "romantic", "family"},
        slow_pace=trip_mood in {"relaxed", "romantic", "family"},
        high_activity=trip_mood == "adventure",
    )
    return policy.model_dump()


def refine_constraints_by_destination(
    constraint_policy: Dict[str, Any],
    destination_policy: Dict[str, Any],
    mood_policy: Dict[str, Any],
    budget_policy: Dict[str, Any],
    timing_policy: Dict[str, Any],
) -> Dict[str, Any]:
    refined = dict(constraint_policy)
    destination_type = destination_policy.get("destination_type")
    refinement_flags: List[str] = []

    if destination_type == "mountain":
        if refined.get("low_mobility"):
            refined["low_risk"] = True
            refined["slow_pace"] = True
            refined["high_activity"] = False
            refinement_flags.append("mountain_low_mobility_safety_bias")
        if refined.get("family_safe"):
            refined["low_risk"] = True
            refined["high_activity"] = False
            refinement_flags.append("mountain_family_safe_filter")

    elif destination_type == "safari":
        if refined.get("group_coordination"):
            refined["low_risk"] = True
            refinement_flags.append("safari_group_coordination_bias")
        if refined.get("quiet_preferred"):
            refined["low_risk"] = True
            refinement_flags.append("safari_quiet_viewing_bias")

    elif destination_type == "coastal":
        if refined.get("slow_pace"):
            refined["quiet_preferred"] = True
            refined["low_risk"] = True
            refinement_flags.append("coastal_slow_pace_bias")
        if refined.get("value_focused"):
            refined["avoid_premium"] = True
            refinement_flags.append("coastal_value_focus_bias")

    elif destination_type == "city":
        if refined.get("quiet_preferred"):
            refined["low_risk"] = True
            refined["high_activity"] = False
            refinement_flags.append("city_quiet_preference_bias")
        if refined.get("group_coordination"):
            refined["low_risk"] = True
            refinement_flags.append("city_group_coordination_bias")

    elif destination_type in {"arid", "mixed_or_unknown"}:
        if refined.get("low_risk"):
            refinement_flags.append("remote_transport_practical_bias")
        if refined.get("family_safe"):
            refined["high_activity"] = False
            refinement_flags.append("remote_family_safe_filter")

    return {
        "constraint_policy": refined,
        "refinement_flags": refinement_flags,
    }


def resolve_constraint_conflicts(
    constraint_policy: Dict[str, Any],
    brief: Dict[str, Any],
    destination_policy: Dict[str, Any],
    mood_policy: Dict[str, Any],
    budget_policy: Dict[str, Any],
    timing_policy: Dict[str, Any],
) -> Dict[str, Any]:
    resolved = dict(constraint_policy)
    trip_mood = _normalize_text(brief.get("trip_mood"))
    budget_level = _normalize_text(brief.get("budget_level")) or "unspecified"
    destination_type = destination_policy.get("destination_type")

    conflict_flags: List[str] = []
    resolved_constraints: List[str] = []

    if resolved.get("slow_pace") and resolved.get("high_activity"):
        conflict_flags.append("slow_pace_vs_high_activity")
        if trip_mood == "adventure":
            resolved["slow_pace"] = False
            resolved_constraints.append("kept_high_activity_for_adventure")
        else:
            resolved["high_activity"] = False
            resolved_constraints.append("kept_slow_pace_over_high_activity")

    if resolved.get("avoid_premium") and mood_policy.get("experience_style") == "elevated":
        conflict_flags.append("avoid_premium_vs_premium_experience")
        if budget_level in {"low", "medium"} or budget_policy.get("budget_posture") in {"cost_sensitive", "balanced"}:
            resolved["avoid_premium"] = True
            resolved_constraints.append("avoid_premium_preserved")

    if resolved.get("low_mobility") and destination_type == "mountain":
        conflict_flags.append("low_mobility_vs_mountain_bias")
        resolved["low_mobility"] = True
        resolved_constraints.append("low_mobility_preserved")

    if resolved.get("quiet_preferred") and destination_type == "city":
        conflict_flags.append("quiet_preferred_vs_city_bias")
        resolved["quiet_preferred"] = True
        resolved_constraints.append("quiet_preference_preserved")

    if timing_policy.get("is_month_only") and resolved.get("high_activity"):
        conflict_flags.append("high_activity_vs_low_timing_specificity")
        if trip_mood != "adventure":
            resolved["high_activity"] = False
            resolved_constraints.append("reduced_activity_for_month_only_timing")

    return {
        "constraint_policy": resolved,
        "conflict_flags": conflict_flags,
        "resolved_constraints": resolved_constraints,
    }


def _derive_global_flags(
    constraint_policy: Dict[str, Any],
    budget_policy: Dict[str, Any],
    traveller_policy: Dict[str, Any],
    mood_policy: Dict[str, Any],
    timing_policy: Dict[str, Any],
    conflict_flags: List[str],
    resolved_constraints: List[str],
    refinement_flags: List[str],
) -> Dict[str, Any]:
    constraints: List[str] = [
        name for name, enabled in constraint_policy.items() if enabled
    ]

    if timing_policy["should_treat_as_provisional"]:
        constraints.append("provisional_timing")
    if timing_policy["should_anchor_to_duration"]:
        constraints.append("duration_anchored")
    if mood_policy["trip_mood"] == "luxury":
        constraints.append("premium_experience")
    if mood_policy["trip_mood"] == "corporate":
        constraints.append("team_structure")

    return {
        "constraints": constraints,
        "is_budget_constrained": budget_policy["budget_posture"] in {"cost_sensitive", "balanced"},
        "is_group_sensitive": traveller_policy["needs_group_coordination"],
        "is_timing_strong": timing_policy["is_timing_usable"],
        "requires_safe_activity_filter": traveller_policy["needs_family_safe_planning"],
        "requires_coordination_bias": traveller_policy["needs_group_coordination"]
        or mood_policy["trip_mood"] == "corporate",
        "conflict_flags": list(conflict_flags),
        "resolved_constraints": list(resolved_constraints),
        "refinement_flags": list(refinement_flags),
    }


def validate_planning_constraints(planning_constraints: Dict[str, Any]) -> PlanningConstraints:
    return PlanningConstraints(**planning_constraints)


def build_planning_constraints(
    brief: Dict[str, Any],
    trace_id: str | None = None,
) -> Dict[str, Any]:
    destination_policy = derive_destination_policy(brief)
    budget_policy = derive_budget_policy(brief)
    traveller_policy = derive_traveller_policy(brief)
    mood_policy = derive_mood_policy(brief)
    timing_policy = derive_timing_policy(brief)
    refinement = refine_constraints_by_destination(
        constraint_policy=derive_constraint_policy(brief),
        destination_policy=destination_policy,
        mood_policy=mood_policy,
        budget_policy=budget_policy,
        timing_policy=timing_policy,
    )
    constraint_resolution = resolve_constraint_conflicts(
        constraint_policy=refinement["constraint_policy"],
        brief=brief,
        destination_policy=destination_policy,
        mood_policy=mood_policy,
        budget_policy=budget_policy,
        timing_policy=timing_policy,
    )
    constraint_policy = constraint_resolution["constraint_policy"]
    global_flags = _derive_global_flags(
        constraint_policy=constraint_policy,
        budget_policy=budget_policy,
        traveller_policy=traveller_policy,
        mood_policy=mood_policy,
        timing_policy=timing_policy,
        conflict_flags=constraint_resolution["conflict_flags"],
        resolved_constraints=constraint_resolution["resolved_constraints"],
        refinement_flags=refinement["refinement_flags"],
    )

    planning_constraints = {
        "destination_policy": destination_policy,
        "budget_policy": budget_policy,
        "traveller_policy": traveller_policy,
        "mood_policy": mood_policy,
        "timing_policy": timing_policy,
        "constraint_policy": constraint_policy,
        "global_flags": global_flags,
    }

    validated = validate_planning_constraints(planning_constraints)
    planning_constraints_dict = validated.model_dump()

    append_log(
        "decisions.log",
        str(
            {
                "trace_id": trace_id,
                "constraint_policy": planning_constraints_dict["constraint_policy"],
                "conflict_flags": planning_constraints_dict["global_flags"]["conflict_flags"],
                "resolved_constraints": planning_constraints_dict["global_flags"]["resolved_constraints"],
                "refinement_flags": planning_constraints_dict["global_flags"]["refinement_flags"],
            }
        ),
    )
    return planning_constraints_dict


def derive_planning_constraints(
    brief: Dict[str, Any],
    trace_id: str | None = None,
) -> Dict[str, Any]:
    return build_planning_constraints(brief, trace_id=trace_id)
