
"""
availability_intent_service.py

Responsibilities
-----------------
1. Extract candidate availability from conversational transcripts.
2. Identify immediate availability.
3. Extract notice period in days.
4. Identify whether the candidate is serving a notice period.
5. Extract explicit joining dates.
6. Interpret relative joining timelines.
7. Identify missing and vague availability answers.
8. Preserve evidence for recruiter review.
9. Return structured semantic availability objects.

Important
---------
This service processes conversational transcript answers.
It does not modify the resume extraction pipeline.
"""

import re
from datetime import date, timedelta
from typing import Optional, Any


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

INTENT = "AVAILABILITY"

AVAILABILITY_STATUSES = {
    "IMMEDIATE",
    "AFTER_NOTICE_PERIOD",
    "AVAILABLE_FROM_DATE",
    "NOT_AVAILABLE",
    "UNKNOWN",
}

NOTICE_PERIOD_STATUSES = {
    "SERVING",
    "NOT_STARTED",
    "NOT_REQUIRED",
    "UNKNOWN",
}

NUMBER_WORDS = {
    "a": 1,
    "an": 1,
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
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "forty-five": 45,
    "sixty": 60,
    "ninety": 90,
}

NUMBER_PATTERN = (
    r"(?:\d+(?:\.\d+)?|"
    + "|".join(
        re.escape(word)
        for word in sorted(NUMBER_WORDS, key=len, reverse=True)
    )
    + r")"
)

# ---------------------------------------------------------
# Availability Patterns
# ---------------------------------------------------------

IMMEDIATE_PATTERN = re.compile(
    r"\b(?:"
    r"available immediately|"
    r"immediately available|"
    r"can join immediately|"
    r"join immediately|"
    r"ready to join immediately|"
    r"available right away|"
    r"can start immediately|"
    r"ready to start immediately|"
    r"no notice period|"
    r"don't have a notice period|"
    r"do not have a notice period|"
    r"notice period is zero|"
    r"zero notice period"
    r")\b",
    re.IGNORECASE,
)

SERVING_NOTICE_PATTERN = re.compile(
    r"\b(?:"
    r"serving my notice|"
    r"serving notice period|"
    r"currently serving notice|"
    r"currently serving my notice period|"
    r"on my notice period|"
    r"serving the notice period"
    r")\b",
    re.IGNORECASE,
)

NOT_STARTED_NOTICE_PATTERN = re.compile(
    r"\b(?:"
    r"notice period of|"
    r"notice period is|"
    r"have a notice period|"
    r"my notice period is|"
    r"need to serve"
    r")\b",
    re.IGNORECASE,
)

NOT_AVAILABLE_PATTERN = re.compile(
    r"\b(?:"
    r"not available|"
    r"cannot join|"
    r"can't join|"
    r"unable to join|"
    r"not ready to join|"
    r"not looking to join|"
    r"not interested in joining"
    r")\b",
    re.IGNORECASE,
)

VAGUE_AVAILABILITY_PATTERN = re.compile(
    r"\b(?:"
    r"soon|"
    r"later|"
    r"after some time|"
    r"after a while|"
    r"not sure yet|"
    r"not decided|"
    r"depending on the situation|"
    r"as soon as possible"
    r")\b",
    re.IGNORECASE,
)

DURATION_PATTERN = re.compile(
    rf"\b(?P<number>{NUMBER_PATTERN})\s*"
    r"(?P<unit>days?|weeks?|months?)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------
# Date Patterns
# ---------------------------------------------------------

MONTHS = {
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

MONTH_PATTERN = "|".join(MONTHS.keys())

EXPLICIT_DATE_PATTERNS = [
    re.compile(
        r"\b(?P<day>\d{1,2})[-/](?P<month>\d{1,2})[-/](?P<year>\d{4})\b"
    ),
    re.compile(
        rf"\b(?P<day>\d{{1,2}})\s+"
        rf"(?P<month_name>{MONTH_PATTERN})"
        rf"(?:\s+(?P<year>\d{{4}}))?\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<month_name>{MONTH_PATTERN})\s+"
        rf"(?P<day>\d{{1,2}})"
        rf"(?:,?\s+(?P<year>\d{{4}}))?\b",
        re.IGNORECASE,
    ),
]


# ---------------------------------------------------------
# Number Conversion
# ---------------------------------------------------------

def _number_to_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None

    value = value.strip().lower()

    try:
        number = float(value)

        if number.is_integer():
            return int(number)

        return None

    except ValueError:
        return NUMBER_WORDS.get(value)


# ---------------------------------------------------------
# Duration Conversion
# ---------------------------------------------------------

def _duration_to_days(
    number: int,
    unit: str,
) -> int:
    """
    Convert spoken duration into approximate days.

    Conversion:
        1 day   = 1 day
        1 week  = 7 days
        1 month = 30 days

    Month conversion is approximate.
    """

    unit = unit.lower()

    if unit.startswith("day"):
        return number

    if unit.startswith("week"):
        return number * 7

    if unit.startswith("month"):
        return number * 30

    return number


def _extract_durations(text: str) -> list[dict]:
    if not text:
        return []

    durations = []

    for match in DURATION_PATTERN.finditer(text):

        number = _number_to_int(
            match.group("number")
        )

        if number is None:
            continue

        unit = match.group("unit").lower()

        durations.append({
            "raw_text": match.group(0),
            "value": number,
            "unit": unit,
            "days": _duration_to_days(number, unit),
            "start": match.start(),
            "end": match.end(),
        })

    return durations


# ---------------------------------------------------------
# Sentence Splitting
# ---------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    if not text:
        return []

    return [
        part.strip()
        for part in re.split(
            r"(?<=[.!?])\s+|[\n;]+",
            text,
        )
        if part.strip()
    ]


# ---------------------------------------------------------
# Explicit Joining Date Extraction
# ---------------------------------------------------------

def _extract_explicit_date(
    text: str,
    reference_date: date,
) -> tuple[Optional[str], Optional[str]]:
    """
    Extract explicit dates such as:

        15/11/2026
        15 November 2026
        November 15, 2026
        15 November

    If the year is omitted, the reference year is used.
    If that date has already passed, the next year is used.
    """

    if not text:
        return None, None

    for pattern in EXPLICIT_DATE_PATTERNS:

        match = pattern.search(text)

        if not match:
            continue

        try:
            day = int(match.group("day"))

            if match.groupdict().get("month_name"):
                month = MONTHS[
                    match.group("month_name").lower()
                ]
            else:
                month = int(match.group("month"))

            year_text = match.groupdict().get("year")

            year = (
                int(year_text)
                if year_text
                else reference_date.year
            )

            parsed_date = date(year, month, day)

            if not year_text and parsed_date < reference_date:
                parsed_date = date(
                    year + 1,
                    month,
                    day,
                )

            return (
                parsed_date.isoformat(),
                match.group(0),
            )

        except (ValueError, TypeError):
            continue

    return None, None


# ---------------------------------------------------------
# Relative Joining Timeline
# ---------------------------------------------------------

def _extract_relative_joining_days(
    text: str,
) -> tuple[Optional[int], Optional[str]]:
    """
    Extract relative joining timelines.

    Examples:
        I can join in 2 weeks.
        I can start after 15 days.
        I will be available in one month.
    """

    if not text:
        return None, None

    patterns = [
        re.compile(
            rf"\b(?:join|start|available|joining)\s+"
            rf"(?:in|after|within)\s+"
            rf"(?P<number>{NUMBER_PATTERN})\s*"
            r"(?P<unit>days?|weeks?|months?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\b(?:in|after|within)\s+"
            rf"(?P<number>{NUMBER_PATTERN})\s*"
            r"(?P<unit>days?|weeks?|months?)\b"
            r".{0,35}\b(?:join|start|available|joining)\b",
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:

        match = pattern.search(text)

        if not match:
            continue

        number = _number_to_int(
            match.group("number")
        )

        if number is None:
            continue

        days = _duration_to_days(
            number,
            match.group("unit"),
        )

        return days, match.group(0)

    return None, None


# ---------------------------------------------------------
# Notice Period Extraction
# ---------------------------------------------------------

def _extract_notice_period(
    text: str,
) -> tuple[Optional[int], Optional[int], str, Optional[str]]:
    """
    Extract notice period information.

    Returns:
        notice_period_days
        remaining_notice_period_days
        notice_period_status
        evidence
    """

    if not text:
        return None, None, "UNKNOWN", None

    serving_match = SERVING_NOTICE_PATTERN.search(text)

    # Detect explicitly stated notice duration.
    notice_context = re.search(
        r"\b(?:notice period|notice|serve my notice)\b",
        text,
        re.IGNORECASE,
    )

    notice_period_days = None
    remaining_days = None
    evidence = None

    if notice_context:

        # Look for duration in the same sentence as notice context.
        for sentence in _split_sentences(text):

            if not re.search(
                r"\b(?:notice period|notice|serve my notice)\b",
                sentence,
                re.IGNORECASE,
            ):
                continue

            durations = _extract_durations(sentence)

            if durations:
                notice_period_days = durations[0]["days"]
                evidence = sentence
                break

    # Remaining notice duration is a separate concept.
    remaining_pattern = re.compile(
        rf"\b(?:remaining|left|only)\s+"
        rf"(?P<number>{NUMBER_PATTERN})\s*"
        r"(?P<unit>days?|weeks?|months?)\b",
        re.IGNORECASE,
    )

    remaining_match = remaining_pattern.search(text)

    if serving_match:

        if remaining_match:
            number = _number_to_int(
                remaining_match.group("number")
            )

            if number is not None:
                remaining_days = _duration_to_days(
                    number,
                    remaining_match.group("unit"),
                )

        return (
            notice_period_days,
            remaining_days,
            "SERVING",
            evidence or serving_match.group(0),
        )

    if IMMEDIATE_PATTERN.search(text):
        return (
            0,
            0,
            "NOT_REQUIRED",
            IMMEDIATE_PATTERN.search(text).group(0),
        )

    if notice_period_days is not None:
        return (
            notice_period_days,
            None,
            "NOT_STARTED",
            evidence,
        )

    return None, None, "UNKNOWN", None


# ---------------------------------------------------------
# Availability Status
# ---------------------------------------------------------

def _extract_availability_status(
    text: str,
    notice_period_days: Optional[int],
    notice_period_status: str,
    joining_date: Optional[str],
    relative_joining_days: Optional[int],
) -> tuple[str, Optional[str]]:
    """
    Identify the candidate's availability status.
    """

    if not text:
        return "UNKNOWN", None

    not_available_match = NOT_AVAILABLE_PATTERN.search(text)

    immediate_match = IMMEDIATE_PATTERN.search(text)

    # Explicitly contradictory availability statements.
    if not_available_match and (
        immediate_match or joining_date or relative_joining_days is not None
    ):
        return "UNKNOWN", "Conflicting availability statements"

    if not_available_match:
        return (
            "NOT_AVAILABLE",
            not_available_match.group(0),
        )

    if immediate_match:
        return (
            "IMMEDIATE",
            immediate_match.group(0),
        )

    if notice_period_status == "SERVING":
        return (
            "AFTER_NOTICE_PERIOD",
            "Candidate is currently serving a notice period.",
        )

    if notice_period_days is not None and notice_period_days > 0:
        return (
            "AFTER_NOTICE_PERIOD",
            "Candidate has a stated notice period.",
        )

    if joining_date:
        return (
            "AVAILABLE_FROM_DATE",
            joining_date,
        )

    if relative_joining_days is not None:
        return (
            "AVAILABLE_FROM_DATE",
            f"Candidate can join in {relative_joining_days} days.",
        )

    return "UNKNOWN", None


# ---------------------------------------------------------
# Missing and Vague Fields
# ---------------------------------------------------------

def _identify_missing_and_vague_fields(
    text: str,
    availability_status: str,
    notice_period_days: Optional[int],
    joining_date: Optional[str],
    relative_joining_days: Optional[int],
) -> tuple[list[str], list[str]]:

    missing_fields = []
    vague_fields = []

    if not text:
        return (
            [
                "availability_status",
                "notice_period",
                "joining_date",
            ],
            [],
        )

    vague_match = VAGUE_AVAILABILITY_PATTERN.search(text)

    if availability_status == "UNKNOWN":

        if vague_match:
            vague_fields.append(
                "availability_status"
            )
        else:
            missing_fields.append(
                "availability_status"
            )

    if (
        notice_period_days is None
        and availability_status not in {
            "IMMEDIATE",
            "NOT_AVAILABLE",
        }
    ):
        if vague_match:
            vague_fields.append(
                "notice_period"
            )
        else:
            missing_fields.append(
                "notice_period"
            )

    if (
        joining_date is None
        and relative_joining_days is None
        and availability_status not in {
            "IMMEDIATE",
            "NOT_AVAILABLE",
        }
    ):
        if vague_match:
            vague_fields.append(
                "joining_date"
            )
        else:
            missing_fields.append(
                "joining_date"
            )

    return (
        list(dict.fromkeys(missing_fields)),
        list(dict.fromkeys(vague_fields)),
    )


# ---------------------------------------------------------
# Confidence
# ---------------------------------------------------------

def _calculate_confidence(
    availability_status: str,
    notice_period_days: Optional[int],
    joining_date: Optional[str],
    relative_joining_days: Optional[int],
    vague_fields: list[str],
) -> str:

    score = 0

    if availability_status != "UNKNOWN":
        score += 2

    if notice_period_days is not None:
        score += 1

    if joining_date or relative_joining_days is not None:
        score += 1

    if vague_fields:
        score -= 1

    if score >= 3:
        return "HIGH"

    if score >= 1:
        return "MEDIUM"

    return "LOW"


# ---------------------------------------------------------
# Main Service
# ---------------------------------------------------------

def extract_availability_intent(
    transcript_text: str,
    reference_date: Optional[date] = None,
) -> dict[str, Any]:
    """
    Extract availability-related semantic information.

    Parameters
    ----------
    transcript_text:
        Normalized candidate transcript answer.

    reference_date:
        Optional reference date for relative and year-less
        date interpretation. Defaults to today's date.

    Returns
    -------
    dict:
        Structured availability intent object.
    """

    if not isinstance(transcript_text, str):
        transcript_text = ""

    original_text = transcript_text.strip()

    if reference_date is None:
        reference_date = date.today()

    # Empty answer.
    if not original_text:
        return {
            "intent": INTENT,
            "status": "MISSING",
            "availability_status": "UNKNOWN",
            "notice_period_days": None,
            "remaining_notice_period_days": None,
            "notice_period_status": "UNKNOWN",
            "earliest_joining_date": None,
            "earliest_joining_in_days": None,
            "missing_fields": [
                "availability_status",
                "notice_period",
                "joining_date",
            ],
            "vague_fields": [],
            "evidence": {},
            "confidence": "LOW",
        }

    # Extract duration mentions.
    duration_mentions = _extract_durations(
        original_text
    )

    # Extract notice information.
    (
        notice_period_days,
        remaining_notice_period_days,
        notice_period_status,
        notice_evidence,
    ) = _extract_notice_period(
        original_text
    )

    # Extract explicit joining date.
    joining_date, date_evidence = _extract_explicit_date(
        original_text,
        reference_date,
    )

    # Extract relative joining timeline.
    relative_joining_days, relative_evidence = (
        _extract_relative_joining_days(
            original_text
        )
    )

    # Calculate earliest joining date for relative timelines.
    if (
        joining_date is None
        and relative_joining_days is not None
    ):
        joining_date = (
            reference_date
            + timedelta(days=relative_joining_days)
        ).isoformat()

    # Extract availability status.
    availability_status, availability_evidence = (
        _extract_availability_status(
            original_text,
            notice_period_days,
            notice_period_status,
            joining_date,
            relative_joining_days,
        )
    )

    # An explicit immediate availability statement
    # overrides an unrelated date interpretation.
    if availability_status == "IMMEDIATE":
        joining_date = None
        relative_joining_days = 0

    # Identify vague and missing fields.
    missing_fields, vague_fields = (
        _identify_missing_and_vague_fields(
            original_text,
            availability_status,
            notice_period_days,
            joining_date,
            relative_joining_days,
        )
    )

    # Determine overall extraction status.
    if availability_status == "UNKNOWN":

        status = (
            "VAGUE"
            if vague_fields
            else "MISSING"
        )

    elif vague_fields:
        status = "PARTIAL"

    else:
        status = "EXTRACTED"

    # Calculate extraction confidence.
    confidence = _calculate_confidence(
        availability_status,
        notice_period_days,
        joining_date,
        relative_joining_days,
        vague_fields,
    )

    return {
        "intent": INTENT,
        "status": status,
        "availability_status": availability_status,
        "notice_period_days": notice_period_days,
        "remaining_notice_period_days": remaining_notice_period_days,
        "notice_period_status": notice_period_status,
        "earliest_joining_date": joining_date,
        "earliest_joining_in_days": relative_joining_days,
        "duration_mentions": duration_mentions,
        "missing_fields": missing_fields,
        "vague_fields": vague_fields,
        "evidence": {
            "availability": availability_evidence,
            "notice_period": notice_evidence,
            "joining_date": date_evidence,
            "relative_joining": relative_evidence,
        },
        "confidence": confidence,
    }


# ---------------------------------------------------------
# Compatibility Alias
# ---------------------------------------------------------

def process_availability_intent(
    transcript_text: str,
    reference_date: Optional[date] = None,
) -> dict[str, Any]:

    return extract_availability_intent(
        transcript_text,
        reference_date=reference_date,
    )
