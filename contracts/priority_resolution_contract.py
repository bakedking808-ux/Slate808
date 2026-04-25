from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field


SOURCE_PRIORITY = {
    "explicit_user_input": 5,
    "clarification_answer": 4,
    "normalized_recovery": 3,
    "inferred_value": 2,
    "default_fallback": 1,
}


CONSTRAINT_PRIORITY = {
    "execution_readiness": 60,
    "traveller_safety": 50,
    "budget_safety": 40,
    "destination_semantics": 30,
    "mood_shaping": 20,
    "generic_fallback": 10,
}


LAYER_OWNERSHIP = {
    "extraction": "resolve field truth from user, clarification, recovery, inference, and fallback sources",
    "policy": "resolve competing constraint truth and emit conflict/resolution flags",
    "planner": "consume resolved policy without restoring weaker conflicting signals",
    "refiner": "strengthen and compact wording without changing resolved constraint truth",
    "readiness": "gate execution actions without weakening ordinary plan usefulness",
    "formatter": "render labels and polish wording without making planning decisions",
}


class ResolvedField(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    field_name: str
    value: str | int | None
    source: str
    priority: int
    resolved: bool


class PriorityResolutionResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    resolved_fields: list[ResolvedField] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class _FieldCandidate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    field_name: str
    value: str | int | None
    source: str
    precision: int = 0

    @property
    def priority(self) -> int:
        try:
            return SOURCE_PRIORITY[self.source]
        except KeyError as exc:
            raise ValueError(f"Unsupported priority source: {self.source}") from exc


def _normalize_candidates(
    field_candidates: dict[str, list[dict[str, object]]] | list[dict[str, object]],
) -> list[_FieldCandidate]:
    if isinstance(field_candidates, dict):
        normalized: list[_FieldCandidate] = []
        for field_name, candidates in field_candidates.items():
            for candidate in candidates:
                normalized.append(_FieldCandidate(field_name=field_name, **candidate))
        return normalized

    return [_FieldCandidate(**candidate) for candidate in field_candidates]


def _group_by_field(
    candidates: Iterable[_FieldCandidate],
) -> dict[str, list[_FieldCandidate]]:
    grouped: dict[str, list[_FieldCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.field_name, []).append(candidate)
    return grouped


def _choose_stronger_candidate(
    current: _FieldCandidate,
    challenger: _FieldCandidate,
) -> _FieldCandidate:
    if challenger.priority > current.priority:
        return challenger
    if challenger.priority < current.priority:
        return current
    if challenger.precision > current.precision:
        return challenger
    if challenger.precision < current.precision:
        return current
    if current.value is None and challenger.value is not None:
        return challenger
    return current


def resolve_field_priorities(
    field_candidates: dict[str, list[dict[str, object]]] | list[dict[str, object]],
) -> PriorityResolutionResult:
    normalized_candidates = _normalize_candidates(field_candidates)
    grouped_candidates = _group_by_field(normalized_candidates)
    conflicts: list[str] = []
    warnings: list[str] = []
    resolved_fields: list[ResolvedField] = []

    for field_name, candidates in grouped_candidates.items():
        winner = candidates[0]
        for challenger in candidates[1:]:
            stronger = _choose_stronger_candidate(winner, challenger)
            if stronger is challenger:
                if winner.value not in {None, challenger.value}:
                    warnings.append(
                        f"{field_name}: replaced weaker {winner.source} value "
                        f"{winner.value!r} with {challenger.source} value {challenger.value!r}"
                    )
                winner = challenger
                continue

            if challenger.value in {None, winner.value}:
                continue

            if challenger.priority < winner.priority or challenger.precision < winner.precision:
                warnings.append(
                    f"{field_name}: ignored weaker {challenger.source} value "
                    f"{challenger.value!r} in favor of {winner.source} value {winner.value!r}"
                )
            else:
                conflicts.append(
                    f"{field_name}: conflicting equal-priority values "
                    f"{winner.value!r} and {challenger.value!r}; kept first"
                )

        resolved_fields.append(
            ResolvedField(
                field_name=field_name,
                value=winner.value,
                source=winner.source,
                priority=winner.priority,
                resolved=winner.value is not None,
            )
        )

    return PriorityResolutionResult(
        resolved_fields=resolved_fields,
        conflicts=conflicts,
        warnings=warnings,
    )
