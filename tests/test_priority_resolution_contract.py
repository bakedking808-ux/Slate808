from priority_resolution_contract import resolve_field_priorities


def test_explicit_beats_inferred():
    result = resolve_field_priorities(
        {
            "trip_mood": [
                {"value": "luxury", "source": "explicit_user_input"},
                {"value": "family", "source": "inferred_value"},
            ]
        }
    )

    assert result.resolved_fields[0].value == "luxury"
    assert result.resolved_fields[0].source == "explicit_user_input"
    assert result.warnings


def test_clarification_beats_inferred():
    result = resolve_field_priorities(
        {
            "destination": [
                {"value": "naivasha", "source": "clarification_answer"},
                {"value": "nakuru", "source": "inferred_value"},
            ]
        }
    )

    assert result.resolved_fields[0].value == "naivasha"
    assert result.resolved_fields[0].priority == 4


def test_normalized_recovery_beats_inferred():
    result = resolve_field_priorities(
        {
            "destination": [
                {"value": "amboseli", "source": "normalized_recovery"},
                {"value": "mombasa", "source": "inferred_value"},
            ]
        }
    )

    assert result.resolved_fields[0].value == "amboseli"
    assert result.resolved_fields[0].source == "normalized_recovery"


def test_exact_date_beats_month_only():
    result = resolve_field_priorities(
        {
            "timing": [
                {
                    "value": "april",
                    "source": "explicit_user_input",
                    "precision": 1,
                },
                {
                    "value": "10 april to 14 april",
                    "source": "explicit_user_input",
                    "precision": 2,
                },
            ]
        }
    )

    assert result.resolved_fields[0].value == "10 april to 14 april"
    assert result.warnings


def test_high_budget_stays_high_when_weaker_fallback_appears():
    result = resolve_field_priorities(
        {
            "budget_level": [
                {"value": "high", "source": "explicit_user_input"},
                {"value": "low", "source": "default_fallback"},
            ]
        }
    )

    assert result.resolved_fields[0].value == "high"
    assert result.resolved_fields[0].source == "explicit_user_input"


def test_repeated_call_determinism():
    candidates = {
        "budget_level": [
            {"value": "high", "source": "explicit_user_input"},
            {"value": "low", "source": "default_fallback"},
        ],
        "timing": [
            {"value": "april", "source": "explicit_user_input", "precision": 1},
            {
                "value": "10 april to 14 april",
                "source": "explicit_user_input",
                "precision": 2,
            },
        ],
    }

    first = resolve_field_priorities(candidates)
    second = resolve_field_priorities(candidates)

    assert first.model_dump() == second.model_dump()
