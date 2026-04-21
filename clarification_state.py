from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4


_ALLOWED_FIELDS = {
    "destination",
    "traveller_count",
    "timing",
    "budget_amount",
    "budget_level",
    "trip_mood",
}


class ClarificationStateManager:
    def __init__(self) -> None:
        self._state: Optional[Dict[str, Any]] = None

    def has_active_state(self) -> bool:
        return self._state is not None and self._state.get("active") is True

    def get_state(self) -> Optional[Dict[str, Any]]:
        if not self._state:
            return None
        return dict(self._state)

    def start(
        self,
        task_type: str,
        original_input: str,
        missing_fields: list[str],
        collected_fields: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not missing_fields:
            raise ValueError("Cannot start clarification state without missing fields.")

        self._validate_fields(missing_fields)

        cleaned_collected = self._coalesce_fields(collected_fields or {})
        self._validate_collected_fields(cleaned_collected)

        session_trace_id = trace_id or str(uuid4())

        self._state = {
            "active": True,
            "trace_id": session_trace_id,
            "task_type": task_type,
            "original_input": original_input,
            "collected_fields": dict(cleaned_collected),
            "missing_fields": list(missing_fields),
            "current_field": missing_fields[0],
            "status": "awaiting_clarification",
            "retry_count": 0,
        }
        return dict(self._state)

    def increment_retry(self) -> Dict[str, Any]:
        if not self.has_active_state():
            raise ValueError("No active clarification state to retry.")

        self._state["retry_count"] += 1
        return dict(self._state)

    def update_with_field(self, field_name: str, value: Any) -> Dict[str, Any]:
        if not self.has_active_state():
            raise ValueError("No active clarification state to update.")

        self._validate_fields([field_name])

        current_field = self._state["current_field"]
        if field_name != current_field:
            raise ValueError(
                f"Field mismatch. Expected '{current_field}', got '{field_name}'."
            )

        self._state["collected_fields"][field_name] = value
        self._state["retry_count"] = 0

        remaining_fields = [
            field for field in self._state["missing_fields"]
            if field != field_name
        ]
        self._state["missing_fields"] = remaining_fields

        if remaining_fields:
            self._state["current_field"] = remaining_fields[0]
            self._state["status"] = "awaiting_clarification"
        else:
            self._state["current_field"] = None
            self._state["status"] = "complete"
            self._state["active"] = False

        return dict(self._state)

    def merge_fields(self, values: Dict[str, Any]) -> Dict[str, Any]:
        if not self.has_active_state():
            raise ValueError("No active clarification state to merge into.")

        self._validate_collected_fields(values)
        self._state["collected_fields"] = self._coalesce_fields(
            self._state["collected_fields"], values
        )
        return dict(self._state)

    def clear(self) -> None:
        self._state = None

    def _validate_fields(self, fields: list[str]) -> None:
        for field in fields:
            if field not in _ALLOWED_FIELDS:
                raise ValueError(f"Unsupported field: {field}")

    def _validate_collected_fields(self, collected_fields: Dict[str, Any]) -> None:
        for key in collected_fields:
            if key not in _ALLOWED_FIELDS:
                raise ValueError(f"Unsupported collected field: {key}")

    def _coalesce_fields(self, *field_sets: Dict[str, Any]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for field_set in field_sets:
            for key, value in field_set.items():
                if value is not None:
                    merged[key] = value
                elif key not in merged:
                    merged[key] = value
        return merged
