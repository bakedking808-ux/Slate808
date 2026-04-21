from timing_parsing_contract import parse_timing_text


def _parsed(text):
    result = parse_timing_text(text)
    assert result.matched is True
    assert result.parsed is not None
    return result.parsed


def test_exact_date_parsing_day_month_ordinal():
    parsed = _parsed("21st april")

    assert parsed.category == "exact_date"
    assert parsed.start_date == "21 april"
    assert parsed.end_date is None
    assert parsed.month == "april"
    assert parsed.confidence == "high"


def test_exact_date_parsing_month_day():
    parsed = _parsed("Jan 1")

    assert parsed.category == "exact_date"
    assert parsed.normalized_text == "1 january"
    assert parsed.start_date == "1 january"


def test_exact_date_parsing_month_day_year():
    parsed = _parsed("January 1, 2025")

    assert parsed.category == "exact_date"
    assert parsed.normalized_text == "1 january 2025"
    assert parsed.start_date == "1 january 2025"
    assert parsed.year == 2025


def test_date_range_parsing_same_month_day_first():
    parsed = _parsed("1-2 Jan")

    assert parsed.category == "date_range"
    assert parsed.start_date == "1 january"
    assert parsed.end_date == "2 january"
    assert parsed.normalized_text == "1 january to 2 january"


def test_date_range_parsing_cross_month_month_first():
    parsed = _parsed("Dec 30 - Jan 2")

    assert parsed.category == "date_range"
    assert parsed.start_date == "30 december"
    assert parsed.end_date == "2 january"


def test_date_range_parsing_cross_month_day_first():
    parsed = _parsed("13 May to 3 June")

    assert parsed.category == "date_range"
    assert parsed.start_date == "13 may"
    assert parsed.end_date == "3 june"


def test_month_only_parsing_bare_month():
    parsed = _parsed("January")

    assert parsed.category == "month_only"
    assert parsed.month == "january"
    assert parsed.year is None
    assert parsed.confidence == "medium"


def test_month_only_parsing_with_prefix():
    parsed = _parsed("in January")

    assert parsed.category == "month_only"
    assert parsed.normalized_text == "january"


def test_month_year_parsing_short_month():
    parsed = _parsed("Jan 2025")

    assert parsed.category == "month_year"
    assert parsed.month == "january"
    assert parsed.year == 2025
    assert parsed.confidence == "high"


def test_month_year_parsing_with_prefix():
    parsed = _parsed("in January 2025")

    assert parsed.category == "month_year"
    assert parsed.normalized_text == "january 2025"


def test_relative_timing_next_week():
    parsed = _parsed("next week")

    assert parsed.category == "relative_timing"
    assert parsed.relative_label == "next week"


def test_relative_timing_this_weekend():
    parsed = _parsed("this weekend")

    assert parsed.category == "relative_timing"
    assert parsed.relative_label == "this weekend"


def test_relative_timing_later_this_month():
    parsed = _parsed("later this month")

    assert parsed.category == "relative_timing"
    assert parsed.relative_label == "later this month"


def test_duration_parsing_days():
    parsed = _parsed("3 days")

    assert parsed.category == "duration"
    assert parsed.duration_days == 3
    assert parsed.normalized_text == "3 days"


def test_duration_parsing_nights():
    parsed = _parsed("2 nights")

    assert parsed.category == "duration"
    assert parsed.duration_nights == 2
    assert parsed.normalized_text == "2 nights"


def test_duration_parsing_days_and_nights():
    parsed = _parsed("4 days 3 nights")

    assert parsed.category == "duration"
    assert parsed.duration_days == 4
    assert parsed.duration_nights == 3
    assert parsed.normalized_text == "4 days 3 nights"


def test_duration_parsing_week():
    parsed = _parsed("a week")

    assert parsed.category == "duration"
    assert parsed.duration_days == 7
    assert parsed.warnings == []


def test_duration_parsing_long_weekend_warning():
    parsed = _parsed("a long weekend")

    assert parsed.category == "duration"
    assert parsed.duration_nights == 3
    assert parsed.warnings == ["long weekend approximated as 3 nights"]


def test_season_period_parsing():
    parsed = _parsed("in summer")

    assert parsed.category == "season_period"
    assert parsed.season_label == "summer"


def test_high_season_period_parsing():
    parsed = _parsed("during high season")

    assert parsed.category == "season_period"
    assert parsed.season_label == "high season"


def test_named_period_christmas_parsing():
    parsed = _parsed("over Christmas")

    assert parsed.category == "named_period"
    assert parsed.named_period_label == "christmas"


def test_named_period_holidays_parsing():
    parsed = _parsed("during the holidays")

    assert parsed.category == "named_period"
    assert parsed.named_period_label == "holidays"


def test_composite_duration_and_relative_timing():
    parsed = _parsed("a 3-day trip next month")

    assert parsed.category == "composite_timing"
    assert parsed.duration_days == 3
    assert parsed.relative_label == "next month"
    assert parsed.normalized_text == "3 days next month"
    assert parsed.warnings == ["composite timing contains multiple timing signals"]


def test_composite_week_and_month():
    parsed = _parsed("a week in December")

    assert parsed.category == "composite_timing"
    assert parsed.duration_days == 7
    assert parsed.month == "december"
    assert parsed.normalized_text == "7 days december"


def test_composite_range_and_matching_duration():
    parsed = _parsed("1-3 Jan, 3 days")

    assert parsed.category == "composite_timing"
    assert parsed.start_date == "1 january"
    assert parsed.end_date == "3 january"
    assert parsed.duration_days == 3
    assert parsed.warnings == []


def test_composite_range_and_conflicting_duration_warning():
    parsed = _parsed("1-3 Jan, 4 days")

    assert parsed.category == "composite_timing"
    assert parsed.duration_days == 4
    assert parsed.warnings == ["composite timing contains possible duration mismatch"]


def test_exact_date_does_not_collapse_to_month_only():
    parsed = _parsed("Plan this on 21st April if possible")

    assert parsed.category == "exact_date"
    assert parsed.month == "april"
    assert parsed.start_date == "21 april"


def test_repeated_call_determinism():
    first = parse_timing_text("a 3-day trip next month")
    second = parse_timing_text("a 3-day trip next month")

    assert first.model_dump() == second.model_dump()
