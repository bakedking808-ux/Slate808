import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from contracts.timing_parsing_contract import parse_timing_text


TimingState = Literal[
    "exact_timing",
    "relative_timing",
    "duration_only",
    "month_only",
    "vague_timing",
    "missing_timing",
]
TimingFlexibility = Literal["fixed", "flexible", "unknown"]
TimingConfidence = Literal["low", "medium", "high"]
BudgetLevel = Literal["low", "medium", "high", "unspecified"]
TripMood = Literal["relaxed", "adventure", "luxury", "romantic", "family", "corporate"]

TIMING_USABLE_STATES = frozenset(
    {"exact_timing"}
)


class TimingModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    raw_text: str = Field(default="")
    start_date: Optional[str] = Field(default=None)
    end_date: Optional[str] = Field(default=None)
    duration_days: Optional[int] = Field(default=None, gt=0)
    duration_nights: Optional[int] = Field(default=None, gt=0)
    date_flexibility: TimingFlexibility = Field(default="unknown")
    state: TimingState = Field(default="missing_timing")
    confidence: TimingConfidence = Field(default="low")

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("raw_text", mode="before")
    @classmethod
    def _normalize_raw_text(cls, value: Optional[str]) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            return value
        return value.strip()

    @model_validator(mode="after")
    def _validate_timing_contract(self) -> "TimingModel":
        if self.end_date and not self.start_date:
            raise ValueError("end_date requires start_date")

        if self.state == "missing_timing":
            return self

        if self.state == "exact_timing" and not (self.start_date or self.end_date):
            raise ValueError("exact_timing requires at least one exact date signal")

        if self.state == "duration_only" and self.duration_days is None and self.duration_nights is None:
            raise ValueError("duration_only requires duration_days or duration_nights")

        if self.state in {"month_only", "vague_timing", "relative_timing"} and not self.raw_text:
            raise ValueError(f"{self.state} requires raw_text")

        return self


class TravelBriefModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    destination: Optional[str] = Field(default=None)
    traveller_count: Optional[int] = Field(default=None, gt=0)
    timing: TimingModel = Field(default_factory=TimingModel)
    budget_amount: Optional[int] = Field(default=None, ge=0)
    budget_level: BudgetLevel = Field(default="unspecified")
    trip_mood: Optional[TripMood] = Field(default=None)

    @field_validator("destination", "trip_mood", mode="before")
    @classmethod
    def _normalize_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        return cleaned or None

    @field_validator("timing", mode="before")
    @classmethod
    def _ensure_timing_payload(cls, value: Any) -> Any:
        if value is None:
            return TimingModel()
        return value


def normalize_travel_text(text: str) -> str:
    text = text.lower().strip()

    repairs = {
        "formy": "for my",
        "fora": "for a",
        "tomy": "to my",
        "toa": "to a",
        "plana": "plan a",
        "nextweekend": "next weekend",
        "thisweekend": "this weekend",
        "onthe": "on the",
        "anescape": "an escape",
        "towatamu": "to watamu",
        "tomara": "to mara",
        "tokajiado": "to kajiado",
        "tokisumu": "to kisumu",
        "tolamu": "to lamu",
        "2kids": "2 kids",
        "2adults": "2 adults",
        "40guys": "40 guys",
        "5couples": "5 couples",
        "3oth": "30th",
        "kshs": "ksh",
        "ksh.": "ksh",
        "kes.": "kes",
        "febuary": "february",
        "feburary": "february",
    }

    for bad, good in repairs.items():
        text = re.sub(rf"\b{re.escape(bad)}\b", good, text)

    text = re.sub(
        r"(\d+)(guys|ladies|friends|colleagues|coworkers|staff|employees|delegates|members|participants|guests|travellers|travelers|adults|kids|children|couples)\b",
        r"\1 \2",
        text,
    )
    text = re.sub(r"\s+", " ", text)
    return text


DESTINATION_STOP_WORDS = {
    "for",
    "with",
    "my",
    "our",
    "their",
    "his",
    "her",
    "next",
    "this",
    "tomorrow",
    "today",
    "weekend",
    "week",
    "month",
    "budget",
    "cheap",
    "luxury",
    "premium",
    "affordable",
    "comfortable",
    "people",
    "persons",
    "guests",
    "travellers",
    "travelers",
    "adults",
    "adult",
    "kids",
    "kid",
    "children",
    "child",
    "couple",
    "couples",
    "duo",
    "trio",
    "group",
    "party",
    "team",
    "crew",
    "friends",
    "colleagues",
    "coworkers",
    "staff",
    "employees",
    "delegates",
    "members",
    "participants",
    "guys",
    "ladies",
    "dogs",
    "dog",
    "cats",
    "cat",
    "pets",
    "pet",
    "ksh",
    "kes",
    "sh",
}

WEAK_DESTINATION_VALUES = {
    "",
    "the destination",
    "a destination",
    "specific destination",
    "a specific destination",
    "destination",
    "place",
    "somewhere",
    "location",
}

SUPPORTED_FLEXIBLE_DESTINATION_PATTERNS = (
    r"^(?:the\s+)?coast$",
    r"^somewhere\s+\w+$",
    r"^outside\s+kenya$",
    r"^near\s+nairobi$",
)
DESTINATION_PREFIX_TOKENS = {
    "maybe",
    "perhaps",
    "around",
    "somewhere",
    "someplace",
}
DESTINATION_TRAILING_TIMING_TOKENS = {
    "sometime",
    "soon",
    "later",
    "next",
    "this",
}

CONTAMINATED_DESTINATION_VALUES = {
    "help me",
    "i need a",
    "i need an",
    "i want a",
    "me and",
    "me on",
    "need a",
    "new request",
    "plan",
    "we need a",
}

CONTAMINATED_DESTINATION_PATTERNS = (
    r"^(?:could|can|would)\s+you\b",
    r"\bhelp\s+me\b",
    r"^(?:set\s+up|book|plan|make|create|organize|arrange|sort\s+out|do)"
    r"\b.*\b(?:trip|travel|getaway|retreat|vacation|holiday|journey|escape)\b",
    r"^i\s+want\b.*\b"
    r"(?:trip|travel|getaway|retreat|vacation|holiday|journey|escape)\b",
    r"^i\s+need\s+an?\s+(?:escape|weekend\s+away)\b",
    r"^i\s+need\s+a\s+break\b",
    r"^travel\s+from\b",
    r"^me\s+(?:and|on)\b",
)


def _strip_malformed_destination_prefix(candidate: str) -> str:
    candidate = re.sub(r"^(?:(?:travel|trip|journey|getaway|holiday|retreat|vacation|escape)to\s+)+", "", candidate)
    return re.sub(
        r"^(?:(?:plan|curate|organize|arrange|help me plan|make|design|execute|prepare|create|schedule)\s+(?:a\s+)?(?:trip|travel plan|travel|holiday|getaway|retreat|vacation|escape|journey)\s+(?:to|for)\s+)+",
        "",
        candidate,
    )


def _clean_destination_candidate(candidate: str) -> Optional[str]:
    candidate = candidate.lower().strip()
    candidate = _strip_malformed_destination_prefix(candidate)
    candidate = re.sub(r"\s+", " ", candidate)

    words = candidate.split()
    while (
        words
        and words[0].strip(" ,.-") in DESTINATION_PREFIX_TOKENS
        and not (
            words[0].strip(" ,.-") == "somewhere"
            and len(words) > 1
            and words[1].strip(" ,.-") not in DESTINATION_TRAILING_TIMING_TOKENS
        )
        and not _is_supported_flexible_destination(" ".join(words))
    ):
        words.pop(0)

    cleaned_words: List[str] = []

    for word in words:
        stripped = word.strip(" ,.-")
        if not stripped:
            continue

        if stripped in DESTINATION_TRAILING_TIMING_TOKENS:
            break

        if stripped in DESTINATION_STOP_WORDS:
            break

        if stripped.isdigit():
            break

        if re.fullmatch(r"\d+(st|nd|rd|th)?", stripped):
            break

        cleaned_words.append(stripped)

    cleaned = " ".join(cleaned_words).strip()
    return cleaned or None


def _is_supported_flexible_destination(candidate: str) -> bool:
    return any(
        re.fullmatch(pattern, candidate)
        for pattern in SUPPORTED_FLEXIBLE_DESTINATION_PATTERNS
    )


def is_contaminated_destination(candidate: Optional[str]) -> bool:
    if not candidate:
        return False

    candidate = re.sub(r"\s+", " ", candidate.strip().lower())
    if _is_supported_flexible_destination(candidate):
        return False

    if candidate in CONTAMINATED_DESTINATION_VALUES:
        return True

    return any(
        re.search(pattern, candidate)
        for pattern in CONTAMINATED_DESTINATION_PATTERNS
    )


def _is_valid_destination(candidate: Optional[str]) -> bool:
    if not candidate:
        return False

    candidate = candidate.strip().lower()

    if candidate in WEAK_DESTINATION_VALUES:
        return False

    if is_contaminated_destination(candidate):
        return False

    if candidate in {
        "next weekend",
        "this weekend",
        "next week",
        "next month",
        "this month",
        "tomorrow",
        "today",
        "fortnight",
    }:
        return False

    if candidate in {"family", "group", "team", "crew"}:
        return False

    if len(candidate) < 2:
        return False

    return True


def extract_destination(text: str, decision_log=None) -> Optional[str]:
    text = normalize_travel_text(text)

    patterns = [
        (
            r"\b(?:plan|curate|organize|arrange|help me plan|make|design|execute|prepare|create|schedule)\s+(?:a\s+)?(?:trip|travel plan|travel|holiday|getaway|retreat|escape|journey)\s+to\s+([a-zA-Z][a-zA-Z\s\-'\/]{1,60})",
            "trip_to",
        ),
        (
            r"\b(?:plan|curate|organize|arrange|help me plan|make|design|execute|prepare|create|schedule)\s+(?:a\s+)?(?:trip|travel plan|travel|holiday|getaway|retreat|escape|journey)\b.*?\bfor\s+([a-zA-Z][a-zA-Z\s\-'\/]{1,60})",
            "trip_for_after_context",
        ),
        (
            r"\b(?:weekend|holiday|relaxed|family|short|corporate)?\s*(?:trip|travel|getaway|retreat|journey|escape)\s+to\s+([a-zA-Z][a-zA-Z\s\-'\/]{1,60})",
            "travel_to",
        ),
        (
            r"\b(?:make|plan|curate|design)\s+(?:a\s+)?(?:trip|travel plan|journey|escape)\s+for\s+([a-zA-Z][a-zA-Z\s\-'\/]{1,60})",
            "travel_for_destination",
        ),
        (
            r"\bto\s+([a-zA-Z][a-zA-Z\s\-'\/]{1,60})",
            "generic_to",
        ),
    ]

    for pattern, label in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue

        raw_candidate = match.group(1).strip()
        cleaned_candidate = _clean_destination_candidate(raw_candidate)

        if decision_log:
            decision_log(
                f"DESTINATION_PATTERN_MATCH: label={label}, raw='{raw_candidate}', cleaned='{cleaned_candidate}'"
            )

        if _is_valid_destination(cleaned_candidate):
            if decision_log:
                decision_log(f"DESTINATION_ACCEPTED: '{cleaned_candidate}'")
            return cleaned_candidate

    shorthand_match = re.match(
        r"^\s*([a-zA-Z][a-zA-Z\s\-'\/]{1,60}?)(?=\s+(?:for|with|budget|next|this|tomorrow|today|in|at)\b)",
        text,
        re.IGNORECASE,
    )
    if shorthand_match and not re.match(
        r"^\s*(?:plan|curate|organize|arrange|help me plan|make|design|schedule|prepare|create|execute)\b",
        text,
        re.IGNORECASE,
    ):
        raw_candidate = shorthand_match.group(1).strip()
        cleaned_candidate = _clean_destination_candidate(raw_candidate)

        if decision_log:
            decision_log(
                f"DESTINATION_PATTERN_MATCH: label=leading_shorthand, raw='{raw_candidate}', cleaned='{cleaned_candidate}'"
            )

        if _is_valid_destination(cleaned_candidate):
            if decision_log:
                decision_log(f"DESTINATION_ACCEPTED: '{cleaned_candidate}'")
            return cleaned_candidate

    if decision_log:
        decision_log("DESTINATION_ACCEPTED: None")

    return None


HUMAN_LABELS = (
    "people|persons|guests|travellers|travelers|adults?|men|women|guys|"
    "ladies|friends|colleagues|coworkers|staff|employees|delegates|members|"
    "participants|kids?|children|grownups?"
)

ANIMAL_LABELS = "dogs?|cats?|pets?"


def _safe_for_number(text: str) -> Optional[int]:
    match = re.search(r"\bfor\s+(\d+)\b", text)
    if not match:
        return None

    value = int(match.group(1))
    tail = text[match.end(): match.end() + 25]

    if re.search(r"\s*(k\b|kes\b|ksh\b|sh\b|budget\b)", tail):
        return None

    if re.search(r"\s*(days?\b|nights?\b|weeks?\b|month\b|weekend\b|fortnight\b)", tail):
        return None

    if value > 100:
        return None

    return value


def _parse_number_word(word: str) -> Optional[int]:
    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
    }
    return number_words.get(word.lower())


def _safe_for_number_word(text: str) -> Optional[int]:
    match = re.search(
        r"\bfor\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b",
        text,
    )
    if not match:
        return None

    tail = text[match.end(): match.end() + 25]
    if re.search(r"\s*(k\b|kes\b|ksh\b|sh\b|budget\b)", tail):
        return None

    if re.search(r"\s*(days?\b|nights?\b|weeks?\b|month\b|weekend\b|fortnight\b)", tail):
        return None

    return _parse_number_word(match.group(1))


def extract_traveller_count(text: str, decision_log=None) -> Optional[int]:
    text = normalize_travel_text(text)

    animal_hits = re.findall(rf"(\d+)\s*({ANIMAL_LABELS})\b", text)
    if animal_hits and decision_log:
        decision_log(f"ANIMAL_DETECTED_IGNORED: {animal_hits}")

    compact_human = re.findall(
        rf"(\d+)\s*(couples|{HUMAN_LABELS})\b",
        text,
    )
    if compact_human:
        total = 0
        for num, label in compact_human:
            value = int(num)
            if label == "couples":
                value *= 2
            total += value

        if decision_log:
            decision_log(f"TRAVELLER_COUNT_EXTRACTED: {total} (compact_human)")
        return total

    composite = re.search(
        rf"\b(\d+)\s+(adults?|grownups?|people|persons?)\s+and\s+(\d+)\s+(kids?|children|child)\b",
        text,
    )
    if composite:
        value = int(composite.group(1)) + int(composite.group(3))
        if decision_log:
            decision_log(f"TRAVELLER_COUNT_EXTRACTED: {value} (composite)")
        return value

    grouped = re.search(r"\b(group|party|team|crew)\s+of\s+(\d+)\b", text)
    if grouped:
        value = int(grouped.group(2))
        if decision_log:
            decision_log(f"TRAVELLER_COUNT_EXTRACTED: {value} (group_of)")
        return value

    couples = re.search(r"\b(\d+)\s+couples\b", text)
    if couples:
        value = int(couples.group(1)) * 2
        if decision_log:
            decision_log(f"TRAVELLER_COUNT_EXTRACTED: {value} (couples)")
        return value

    direct = re.search(
        rf"\b(\d+)\s+({HUMAN_LABELS})\b",
        text,
    )
    if direct:
        value = int(direct.group(1))
        if decision_log:
            decision_log(f"TRAVELLER_COUNT_EXTRACTED: {value} (direct)")
        return value

    safe_for_number = _safe_for_number(text)
    if safe_for_number is not None:
        if decision_log:
            decision_log(f"TRAVELLER_COUNT_EXTRACTED: {safe_for_number} (for_number)")
        return safe_for_number

    bare_number = re.fullmatch(r"\d+", text.strip())
    if bare_number:
        value = int(bare_number.group(0))
        if decision_log:
            decision_log(f"TRAVELLER_COUNT_EXTRACTED: {value} (bare_number)")
        return value

    safe_word_number = _safe_for_number_word(text)
    if safe_word_number is not None:
        if decision_log:
            decision_log(f"TRAVELLER_COUNT_EXTRACTED: {safe_word_number} (safe_word_number)")
        return safe_word_number

    relationship_map = {
        "solo": 1,
        "couple": 2,
        "duo": 2,
        "trio": 3,
        "quartet": 4,
        "quintet": 5,
    }
    for key, value in relationship_map.items():
        if re.search(rf"\b{key}\b", text):
            if decision_log:
                decision_log(f"TRAVELLER_COUNT_EXTRACTED: {value} ({key})")
            return value

    number_words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
    }

    for word, number in number_words.items():
        pattern = rf"\b{word}\s+({HUMAN_LABELS})\b"
        if re.search(pattern, text):
            if decision_log:
                decision_log(f"TRAVELLER_COUNT_EXTRACTED: {number} ({word})")
            return number

    bare_word = text.strip().lower()
    if bare_word in number_words:
        value = number_words[bare_word]
        if decision_log:
            decision_log(f"TRAVELLER_COUNT_EXTRACTED: {value} (bare_word)")
        return value

    return None


def _infer_budget_level_from_amount(amount: int) -> str:
    if amount <= 45000:
        return "low"
    if amount <= 85000:
        return "medium"
    return "high"


CANONICAL_MONTH_TO_NUMBER = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

MONTH_TOKEN_TO_NAME = {
    "jan": "january",
    "january": "january",
    "feb": "february",
    "february": "february",
    "mar": "march",
    "march": "march",
    "apr": "april",
    "april": "april",
    "may": "may",
    "jun": "june",
    "june": "june",
    "jul": "july",
    "july": "july",
    "aug": "august",
    "august": "august",
    "sep": "september",
    "sept": "september",
    "september": "september",
    "oct": "october",
    "october": "october",
    "nov": "november",
    "november": "november",
    "dec": "december",
    "december": "december",
}

MONTH_NAME_TO_NUMBER = {
    token: CANONICAL_MONTH_TO_NUMBER[canonical]
    for token, canonical in MONTH_TOKEN_TO_NAME.items()
}

MONTH_NUMBER_TO_NAME = {
    value: key for key, value in CANONICAL_MONTH_TO_NUMBER.items()
}

MONTHS = "|".join(
    sorted(MONTH_TOKEN_TO_NAME.keys(), key=len, reverse=True)
)

MONTH_MAX_DAYS = {
    "january": 31,
    "february": 29,
    "march": 31,
    "april": 30,
    "may": 31,
    "june": 30,
    "july": 31,
    "august": 31,
    "september": 30,
    "october": 31,
    "november": 30,
    "december": 31,
}


def _canonicalize_month_token(month_name: str) -> Optional[str]:
    return MONTH_TOKEN_TO_NAME.get(month_name.strip().lower())


def _previous_month_name(month_name: str) -> Optional[str]:
    canonical_month = _canonicalize_month_token(month_name)
    if canonical_month is None:
        return None

    month_number = CANONICAL_MONTH_TO_NUMBER.get(canonical_month)
    if month_number is None:
        return None

    previous_month_number = 12 if month_number == 1 else month_number - 1
    return MONTH_NUMBER_TO_NAME.get(previous_month_number)


def _extract_day_from_token(day_text: str) -> int:
    return int(re.match(r"\d{1,2}", day_text).group(0))


def _is_valid_day_month(day: int, month_name: str) -> bool:
    if day < 1:
        return False
    max_days = MONTH_MAX_DAYS.get(month_name)
    if max_days is None:
        return False
    return day <= max_days


def _normalize_day_month(day_text: str, month_text: str) -> Optional[str]:
    canonical_month = _canonicalize_month_token(month_text)
    if canonical_month is None:
        return None

    day = _extract_day_from_token(day_text)
    if not _is_valid_day_month(day, canonical_month):
        return None

    return f"{day_text.lower()} {canonical_month}"


def _parse_date_component(value: str) -> Optional[tuple[int, int]]:
    value = value.strip().lower()
    day_match = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)", value)
    if day_match:
        day = int(day_match.group(1))
        canonical_month = _canonicalize_month_token(day_match.group(2))
        month = CANONICAL_MONTH_TO_NUMBER.get(canonical_month) if canonical_month else None
        if month and _is_valid_day_month(day, canonical_month):
            return day, month

    month_match = re.fullmatch(r"([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?", value)
    if month_match:
        canonical_month = _canonicalize_month_token(month_match.group(1))
        month = CANONICAL_MONTH_TO_NUMBER.get(canonical_month) if canonical_month else None
        day = int(month_match.group(2))
        if month and _is_valid_day_month(day, canonical_month):
            return day, month

    return None


def _normalize_exact_range(start_date: str, end_date: str, raw_text: str) -> tuple[str, str, str]:
    start_normalized = _normalize_day_month(*start_date.split(maxsplit=1))
    end_normalized = _normalize_day_month(*end_date.split(maxsplit=1))

    if not start_normalized or not end_normalized:
        return "", "", ""

    return start_normalized, end_normalized, f"{start_normalized} to {end_normalized}"


def _resolve_single_month_dash_range(
    start_day_text: str, end_day_text: str, month_name: str
) -> tuple[str, str, str]:
    start_day = _extract_day_from_token(start_day_text)
    end_day = _extract_day_from_token(end_day_text)
    normalized_month = _canonicalize_month_token(month_name)

    if normalized_month is None:
        return "", "", ""

    if start_day > end_day:
        previous_month = _previous_month_name(normalized_month)
        if not previous_month:
            return "", "", ""

        start = _normalize_day_month(str(start_day), previous_month)
        end = _normalize_day_month(str(end_day), normalized_month)
        if not start or not end:
            return "", "", ""
        return start, end, f"{start} to {end}"

    start = _normalize_day_month(start_day_text, normalized_month)
    end = _normalize_day_month(end_day_text, normalized_month)
    if not start or not end:
        return "", "", ""
    return start, end, f"{start} to {end}"


def extract_budget_info(text: str, decision_log=None) -> Dict[str, Any]:
    text = normalize_travel_text(text)
    text_lower = text.lower()

    if re.search(r"\b(?:no\s+budget\s+(?:yet|for\s+now)|budget\s+not\s+decided)\b", text_lower):
        return {"budget_amount": None, "budget_level": "unspecified"}

    amount_patterns = [
        r"\bbudget(?:\s+is|\s+of|\s+for)?\s+(?:kes|ksh|sh)?\s*([\d,]+)\b",
        r"\bwith\s+(?:a\s+budget\s+(?:of|is)\s+)?(?:kes|ksh|sh)\s*([\d,]+)\b",
        r"\b(?:kes|ksh|sh)\s*([\d,]+)\b",
        r"\b([\d,]+)\s*(?:kes|ksh|sh)\b",
        r"\bunder\s+([\d,]+)\b",
        r"\b([\d,]+)\s+budget\b",
        r"\b([\d,]+)k\b",
    ]

    for pattern in amount_patterns:
        match = re.search(pattern, text_lower)
        if match:
            raw = match.group(1).replace(",", "")
            amount = int(raw)

            if pattern == r"\b([\d,]+)k\b":
                amount *= 1000

            level = _infer_budget_level_from_amount(amount)

            if decision_log:
                decision_log(f"BUDGET_EXTRACTED: amount={amount}, level={level}")

            return {
                "budget_amount": amount,
                "budget_level": level,
            }

    if re.search(r"\b(?:luxury|premium|high-end|high\s+budget)\b", text_lower):
        return {"budget_amount": None, "budget_level": "high"}

    if re.search(r"\b(?:comfortable|mid-range|moderate|medium\s+budget)\b", text_lower):
        return {"budget_amount": None, "budget_level": "medium"}

    if re.search(r"\b(?:cheap|low\s+budget|affordable)\b", text_lower):
        return {"budget_amount": None, "budget_level": "low"}

    return {"budget_amount": None, "budget_level": "unspecified"}

WEEKDAYS = "monday|tuesday|wednesday|thursday|friday|saturday|sunday"


def build_timing(
    raw_text: str = "",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    duration_days: Optional[int] = None,
    duration_nights: Optional[int] = None,
    date_flexibility: str = "unknown",
    state: str = "missing_timing",
    confidence: str = "low",
) -> Dict[str, Any]:
    timing = TimingModel(
        raw_text=raw_text,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        duration_nights=duration_nights,
        date_flexibility=date_flexibility,
        state=state,
        confidence=confidence,
    )
    return timing.model_dump()


def _timing_from_parsed_contract(text: str) -> Optional[Dict[str, Any]]:
    parse_result = parse_timing_text(text)
    if not parse_result.matched or parse_result.parsed is None:
        return None

    parsed = parse_result.parsed
    raw_text = parsed.normalized_text or parsed.raw_text

    if parsed.category in {"exact_date", "date_range"}:
        return build_timing(
            raw_text=raw_text,
            start_date=parsed.start_date,
            end_date=parsed.end_date,
            duration_days=parsed.duration_days,
            duration_nights=parsed.duration_nights,
            date_flexibility="fixed",
            state="exact_timing",
            confidence=parsed.confidence,
        )

    if parsed.category == "composite_timing" and (parsed.start_date or parsed.end_date):
        return build_timing(
            raw_text=raw_text,
            start_date=parsed.start_date,
            end_date=parsed.end_date,
            duration_days=parsed.duration_days,
            duration_nights=parsed.duration_nights,
            date_flexibility="fixed",
            state="exact_timing",
            confidence=parsed.confidence,
        )

    if parsed.category == "month_year":
        return build_timing(
            raw_text=raw_text,
            date_flexibility="flexible",
            state="month_only",
            confidence=parsed.confidence,
        )

    if parsed.category == "composite_timing":
        return None

    return None


def is_timing_usable(timing: Optional[Dict[str, Any]]) -> bool:
    if not timing:
        return False

    return timing.get("state") in TIMING_USABLE_STATES


def summarize_timing(timing: Optional[Dict[str, Any]]) -> str:
    if not timing:
        return "timing not specified"

    state = timing.get("state", "missing_timing")
    raw_text = timing.get("raw_text", "").strip()

    if state == "missing_timing":
        return "timing not specified"

    if raw_text:
        return raw_text

    start_date = timing.get("start_date")
    end_date = timing.get("end_date")

    if start_date and end_date and start_date != end_date:
        return f"{start_date} to {end_date}"

    if start_date:
        return start_date

    return "timing not specified"


def _looks_like_date_range_attempt(text: str) -> bool:
    return bool(
        re.search(
            rf"\b(?:{MONTHS}\s+)?\d{{1,2}}(?:st|nd|rd|th)?(?:\s+{MONTHS})?\s*(?:-|to)\s*(?:{MONTHS}\s+)?\d{{1,2}}(?:st|nd|rd|th)?(?:\s+{MONTHS})?\b",
            text,
        )
    )


def _looks_like_incomplete_date_range_attempt(text: str) -> bool:
    if not re.search(r"\bto\b", text):
        return False

    parts = re.split(r"\bto\b", text)
    left = parts[0].strip()
    left_is_full_date = bool(
        re.search(
            rf"\b(?:{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?|\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS})\b",
            left,
        )
    )
    if not left_is_full_date:
        return False

    if len(parts) != 2:
        return True

    _, right = parts
    right = right.strip()
    if not right:
        return True
    if re.match(r"^\d{1,2}(?:st|nd|rd|th)?$", right):
        return True
    if re.match(r"^[a-z]+$", right):
        return True

    return False


def _exact_timing_from_range(
    start_day_text: str,
    start_month_text: str,
    end_day_text: str,
    end_month_text: str,
) -> Dict[str, Any]:
    start = _normalize_day_month(start_day_text, start_month_text)
    end = _normalize_day_month(end_day_text, end_month_text)
    if not start or not end:
        return build_timing()

    normalized_start, normalized_end, normalized_text = _normalize_exact_range(
        start,
        end,
        f"{start} to {end}",
    )
    if not normalized_start or not normalized_end:
        return build_timing()

    return build_timing(
        raw_text=normalized_text,
        start_date=normalized_start,
        end_date=normalized_end,
        date_flexibility="fixed",
        state="exact_timing",
        confidence="high",
    )


def _exact_timing_from_single_date(day_text: str, month_text: str) -> Dict[str, Any]:
    normalized_value = _normalize_day_month(day_text, month_text)
    if not normalized_value:
        return build_timing()

    return build_timing(
        raw_text=normalized_value,
        start_date=normalized_value,
        end_date=normalized_value,
        date_flexibility="fixed",
        state="exact_timing",
        confidence="high",
    )


def _detect_exact_timing(text: str, decision_log=None) -> Optional[Dict[str, Any]]:
    match = re.search(
        rf"\b({MONTHS})\s+(\d{{1,2}}(?:st|nd|rd|th)?)\s+to\s+({MONTHS})\s+(\d{{1,2}}(?:st|nd|rd|th)?)\b",
        text,
    )
    if match:
        return _exact_timing_from_range(
            match.group(2),
            match.group(1),
            match.group(4),
            match.group(3),
        )

    match = re.search(
        rf"\b(\d{{1,2}}(?:st|nd|rd|th)?)\s+({MONTHS})\s+to\s+(\d{{1,2}}(?:st|nd|rd|th)?)\s+({MONTHS})\b",
        text,
    )
    if match:
        return _exact_timing_from_range(
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4),
        )

    match = re.search(
        rf"\b({MONTHS})\s+(\d{{1,2}}(?:st|nd|rd|th)?)\s*-\s*({MONTHS})\s+(\d{{1,2}}(?:st|nd|rd|th)?)\b",
        text,
    )
    if match:
        return _exact_timing_from_range(
            match.group(2),
            match.group(1),
            match.group(4),
            match.group(3),
        )

    match = re.search(
        rf"\b(\d{{1,2}}(?:st|nd|rd|th)?)\s+({MONTHS})\s*-\s*(\d{{1,2}}(?:st|nd|rd|th)?)\s+({MONTHS})\b",
        text,
    )
    if match:
        return _exact_timing_from_range(
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4),
        )

    match = re.search(
        rf"\b(\d{{1,2}}(?:st|nd|rd|th)?)\s*-\s*(\d{{1,2}}(?:st|nd|rd|th)?)\s+({MONTHS})\b",
        text,
    )
    if match:
        start, end, raw_text = _resolve_single_month_dash_range(
            match.group(1), match.group(2), match.group(3)
        )
        if not start or not end:
            return build_timing()
        return build_timing(
            raw_text=raw_text,
            start_date=start,
            end_date=end,
            date_flexibility="fixed",
            state="exact_timing",
            confidence="high",
        )

    match = re.search(
        rf"\b(\d{{1,2}}(?:st|nd|rd|th)?)\s+to\s+(\d{{1,2}}(?:st|nd|rd|th)?)\s+({MONTHS})\b",
        text,
    )
    if match:
        return _exact_timing_from_range(
            match.group(1),
            match.group(3),
            match.group(2),
            match.group(3),
        )

    if " to " in text:
        return None

    if _looks_like_date_range_attempt(text):
        return build_timing()

    match = re.search(
        rf"\b(\d{{1,2}}(?:st|nd|rd|th)?)\s+of\s+({MONTHS})\b",
        text,
    )
    if match:
        return _exact_timing_from_single_date(match.group(1), match.group(2))

    match = re.search(
        rf"\b(?:on\s+)?({MONTHS})\s+(\d{{1,2}}(?:st|nd|rd|th)?)\b",
        text,
    )
    if match:
        return _exact_timing_from_single_date(match.group(2), match.group(1))

    match = re.search(
        rf"\b(\d{{1,2}}(?:st|nd|rd|th)?)\s+({MONTHS})\b",
        text,
    )
    if match:
        return _exact_timing_from_single_date(match.group(1), match.group(2))

    return None


def _detect_relative_timing(text: str, decision_log=None) -> Optional[Dict[str, Any]]:
    relative_patterns = [
        r"\bnext weekend\b",
        r"\bthis weekend\b",
        r"\btomorrow\b",
        r"\bnext week\b",
        r"\bnext month\b",
        r"\bthis month\b",
        r"\bfortnight\b",
        rf"\bthis ({WEEKDAYS})\b",
        rf"\bnext ({WEEKDAYS})\b",
    ]

    for pattern in relative_patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(0).strip()
            return build_timing(
                raw_text=value,
                date_flexibility="fixed",
                state="relative_timing",
                confidence="medium",
            )

    return None


def _detect_duration_only_timing(text: str, decision_log=None) -> Optional[Dict[str, Any]]:
    days_match = re.search(r"\b(?:for\s+)?(\d+)\s+days?\b", text)
    nights_match = re.search(r"\b(\d+)\s+nights?\b", text)

    if days_match and nights_match:
        days_value = int(days_match.group(1))
        nights_value = int(nights_match.group(1))

        if days_value == nights_value + 1:
            return build_timing(
                raw_text=f"for {days_value} days",
                duration_days=days_value,
                date_flexibility="unknown",
                state="duration_only",
                confidence="medium",
            )

        return build_timing()

    if days_match:
        value = int(days_match.group(1))
        return build_timing(
            raw_text=f"for {value} days",
            duration_days=value,
            date_flexibility="unknown",
            state="duration_only",
            confidence="medium",
        )

    if nights_match:
        value = int(nights_match.group(1))
        return build_timing(
            raw_text=f"{value} nights",
            duration_nights=value,
            date_flexibility="unknown",
            state="duration_only",
            confidence="medium",
        )

    weeks_match = re.search(r"\b(?:for\s+)?(\d+)\s*weeks?\b", text)
    if weeks_match:
        value = int(weeks_match.group(1))
        return build_timing(
            raw_text=f"for {value} weeks",
            duration_days=value * 7,
            date_flexibility="unknown",
            state="duration_only",
            confidence="medium",
        )

    if re.search(r"\b(?:for\s+)?a?\s*fortnight\b", text):
        return build_timing(
            raw_text="fortnight",
            duration_days=14,
            date_flexibility="unknown",
            state="duration_only",
            confidence="medium",
        )

    return None


def _detect_month_only_timing(text: str, decision_log=None) -> Optional[Dict[str, Any]]:
    if re.search(rf"\b({MONTHS})\b\s+to\b|\bto\s+({MONTHS})\b", text):
        return None

    stripped_text = re.sub(r"\b(?:in|at|on)\s+", "", text)
    match = re.search(rf"\b({MONTHS})\b", stripped_text)
    if match:
        value = match.group(1).strip()
        return build_timing(
            raw_text=value,
            date_flexibility="flexible",
            state="month_only",
            confidence="low",
        )

    return None


def _detect_partial_or_ambiguous_timing(text: str, decision_log=None) -> Optional[Dict[str, Any]]:
    month_only = _detect_month_only_timing(text, decision_log=decision_log)
    if month_only:
        return month_only

    ambiguous_patterns = [
        r"\bsoon\b",
        r"\blater\b",
        r"\bsometime\b",
        r"\bone day\b",
    ]

    for pattern in ambiguous_patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(0).strip()
            return build_timing(
                raw_text=value,
                date_flexibility="unknown",
                state="vague_timing",
                confidence="low",
            )

    return None


def extract_timing(text: str, decision_log=None) -> Dict[str, Any]:
    text = normalize_travel_text(text)

    if _looks_like_incomplete_date_range_attempt(text):
        return build_timing()

    exact_result = _detect_exact_timing(text, decision_log=decision_log)
    if exact_result is not None:
        return exact_result

    for detector in (
        _detect_duration_only_timing,
        _detect_relative_timing,
    ):
        result = detector(text, decision_log=decision_log)
        if result:
            return result

    parsed_timing = _timing_from_parsed_contract(text)
    if parsed_timing is not None:
        return parsed_timing

    month_only = _detect_month_only_timing(text, decision_log=decision_log)
    if month_only:
        return month_only

    vague_timing = _detect_partial_or_ambiguous_timing(text, decision_log=decision_log)
    if vague_timing:
        return vague_timing

    return build_timing()


MOOD_KEYWORDS = {
    "relaxed": [
        r"\brelaxed\b",
        r"\bcalm\b",
        r"\bpeaceful\b",
        r"\bquiet\b",
        r"\blow-key\b",
        r"\blow\s+key\b",
        r"\blay-back\b",
        r"\beasy-going\b",
        r"\bslowpaced\b",
        r"\bslow-paced\b",
    ],
    "adventure": [
        r"\badventure\b",
        r"\bthrill\b",
        r"\bexciting\b",
        r"\bhiking\b",
        r"\bexploration\b",
        r"\baction\b",
        r"\bsport\b",
    ],
    "luxury": [
        r"\bluxury\b",
        r"\bpremium\b",
        r"\bhigh-end\b",
        r"\bupscale\b",
        r"\bsophisticated\b",
    ],
    "romantic": [
        r"\bromantic\b",
        r"\bhoneymoon\b",
        r"\bromantic.*couples\b",
        r"\bcouples.*romantic\b",
    ],
    "family": [
        r"\bfamily\b",
        r"\bkids\b",
        r"\bchildren\b",
        r"\bfamily-friendly\b",
        r"\bfamily-oriented\b",
    ],
    "corporate": [
        r"\bcorporate\b",
        r"\bteam.*(?:trip|retreat|getaway|escape)",
        r"\bstaff\b",
        r"\bbusiness\b",
        r"\bconference\b",
    ],
}


MOOD_PRIORITY = ["romantic", "corporate", "luxury", "adventure", "family", "relaxed"]


def extract_trip_mood(text: str, decision_log=None) -> Optional[str]:
    text = normalize_travel_text(text)
    text_lower = text.lower()

    found_moods = []

    for mood, patterns in MOOD_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                found_moods.append(mood)
                if decision_log:
                    decision_log(f"MOOD_DETECTED: {mood} (pattern: {pattern})")
                break

    if not found_moods:
        if decision_log:
            decision_log("MOOD_DETECTED: None")
        return None

    found_moods = list(dict.fromkeys(found_moods))

    if len(found_moods) == 1:
        return found_moods[0]

    for priority_mood in MOOD_PRIORITY:
        if priority_mood in found_moods:
            if decision_log:
                decision_log(
                    f"MOOD_PRIORITY_APPLIED: {priority_mood} chosen from {found_moods}"
                )
            return priority_mood

    return found_moods[0]


def build_travel_brief(text: str, decision_log=None) -> Dict[str, Any]:
    normalized = normalize_travel_text(text)
    budget_info = extract_budget_info(normalized, decision_log=decision_log)

    brief = TravelBriefModel(
        destination=extract_destination(normalized, decision_log=decision_log),
        traveller_count=extract_traveller_count(normalized, decision_log=decision_log),
        timing=extract_timing(normalized, decision_log=decision_log),
        budget_amount=budget_info["budget_amount"],
        budget_level=budget_info["budget_level"],
        trip_mood=extract_trip_mood(normalized, decision_log=decision_log),
    )

    return brief.model_dump()


def get_missing_critical_fields(brief: Dict[str, Any]) -> List[str]:
    missing = []

    if not brief.get("destination"):
        missing.append("destination")

    if not brief.get("traveller_count"):
        missing.append("traveller_count")

    if not is_timing_usable(brief.get("timing")):
        missing.append("timing")

    return missing
