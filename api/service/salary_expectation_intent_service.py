
"""
salary_expectation_intent_service.py

Responsibilities
-----------------
1. Extract expected salary from conversational transcripts.
2. Support salary amounts and ranges.
3. Recognize Indian salary formats such as LPA and lakhs.
4. Identify currency and pay frequency.
5. Detect negotiable or flexible salary expectations.
6. Distinguish expected salary from current salary.
7. Identify missing and vague salary answers.
8. Preserve evidence for recruiter review.
9. Return structured semantic salary objects.

Important
---------
This service extracts salary expectations from interview answers.
It does not calculate candidate compensation or make salary recommendations.
"""

import re
from typing import Optional, Any


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

INTENT = "SALARY_EXPECTATION"

SALARY_STATUSES = {
    "MISSING",
    "VAGUE",
    "PARTIAL",
    "EXTRACTED",
}

PAY_FREQUENCIES = {
    "ANNUAL",
    "MONTHLY",
    "WEEKLY",
    "HOURLY",
    "UNKNOWN",
}

CURRENCIES = {
    "INR",
    "USD",
    "EUR",
    "GBP",
    "UNKNOWN",
}

NUMBER_WORDS = {
    "a": 1.0,
    "an": 1.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    "eleven": 11.0,
    "twelve": 12.0,
    "fifteen": 15.0,
    "twenty": 20.0,
    "twenty-five": 25.0,
    "thirty": 30.0,
    "forty": 40.0,
    "fifty": 50.0,
    "sixty": 60.0,
    "seventy": 70.0,
    "eighty": 80.0,
    "ninety": 90.0,
}

NUMBER_PATTERN = (
    r"(?<![A-Za-z0-9])"
    r"(?:"
    r"\d{1,3}(?:,\d{2,3})+(?:\.\d+)?"
    r"|\d+(?:\.\d+)?"
    r"|(?:"
    + "|".join(
        re.escape(word)
        for word in sorted(NUMBER_WORDS, key=len, reverse=True)
    )
    + r")\b"
    r")"
)

SCALE_PATTERN = (
    r"(?:"
    r"lpa|"
    r"lakhs?\s*(?:per\s+annum|per\s+year)?|"
    r"lacs?\s*(?:per\s+annum|per\s+year)?|"
    r"crores?\s*(?:per\s+annum|per\s+year)?|"
    r"cr|"
    r"k|"
    r"thousands?"
    r")"
)

# A range can be written as:
# 8-10 LPA
# 8 to 10 lakhs per annum
# 50000-60000 per month

SALARY_AMOUNT_PATTERN = re.compile(
    rf"(?P<currency>₹|rs\.?|inr|usd|eur|gbp|\$|€|£)?\s*"
    rf"(?P<amount1>{NUMBER_PATTERN})"
    rf"\s*(?P<scale1>{SCALE_PATTERN})?"
    rf"(?:\s*(?:-|–|—|\bto\b)\s*"
    rf"(?P<currency2>₹|rs\.?|inr|usd|eur|gbp|\$|€|£)?\s*"
    rf"(?P<amount2>{NUMBER_PATTERN})"
    rf"\s*(?P<scale2>{SCALE_PATTERN})?"
    rf")?"
    rf"\s*(?P<frequency>"
    rf"per\s+annum|per\s+year|annually|annual|yearly|"
    rf"per\s+month|monthly|per\s+week|weekly|"
    rf"per\s+hour|hourly"
    rf")?",
    re.IGNORECASE,
)

# ---------------------------------------------------------
# Context Patterns
# ---------------------------------------------------------

EXPECTED_SALARY_CONTEXT = re.compile(
    r"\b(?:"
    r"expected salary|"
    r"salary expectation|"
    r"salary expected|"
    r"expect(?:ing)?\s+(?:a\s+)?salary|"
    r"my expectation|"
    r"i expect|"
    r"i am expecting|"
    r"i would expect|"
    r"looking for|"
    r"salary requirement|"
    r"desired salary|"
    r"desired compensation|"
    r"expected compensation|"
    r"expected ctc|"
    r"ctc expectation|"
    r"salary package|"
    r"compensation expectation|"
    r"remuneration"
    r")\b",
    re.IGNORECASE,
)

GENERAL_SALARY_CONTEXT = re.compile(
    r"\b(?:"
    r"salary|"
    r"ctc|"
    r"package|"
    r"compensation|"
    r"remuneration|"
    r"pay"
    r")\b",
    re.IGNORECASE,
)

CURRENT_SALARY_CONTEXT = re.compile(
    r"\b(?:"
    r"current salary|"
    r"currently earning|"
    r"currently earn|"
    r"present salary|"
    r"present ctc|"
    r"current ctc|"
    r"my existing salary|"
    r"my current package|"
    r"earning at present"
    r")\b",
    re.IGNORECASE,
)

NEGOTIABLE_PATTERN = re.compile(
    r"\b(?:"
    r"negotiable|"
    r"open to negotiation|"
    r"open for negotiation|"
    r"flexible|"
    r"open to discussion|"
    r"as per company standards|"
    r"as per company norms|"
    r"as per industry standards|"
    r"depending on the role"
    r")\b",
    re.IGNORECASE,
)

VAGUE_SALARY_PATTERN = re.compile(
    r"\b(?:"
    r"not sure|"
    r"anything reasonable|"
    r"whatever the company offers|"
    r"as per company standards|"
    r"as per company norms|"
    r"industry standard|"
    r"market standard|"
    r"good package|"
    r"decent salary|"
    r"open to discussion|"
    r"negotiable|"
    r"flexible"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------
# Number Conversion
# ---------------------------------------------------------

def _number_to_float(
    value: Optional[str],
) -> Optional[float]:
    if not value:
        return None

    value = value.strip().lower()

    try:
        return float(value.replace(",", ""))
    except ValueError:
        return NUMBER_WORDS.get(value)


# ---------------------------------------------------------
# Scale Conversion
# ---------------------------------------------------------

def _get_scale_multiplier(
    scale: Optional[str],
) -> float:
    if not scale:
        return 1.0

    normalized = re.sub(
        r"\s+",
        " ",
        scale.lower().strip(),
    )

    if normalized in {"lpa"}:
        return 100000.0

    if normalized.startswith(("lakh", "lac")):
        return 100000.0

    if normalized.startswith("crore") or normalized == "cr":
        return 10000000.0

    if normalized == "k" or normalized.startswith("thousand"):
        return 1000.0

    return 1.0


def _normalize_amount(
    amount: Optional[str],
    scale: Optional[str],
) -> Optional[float]:
    number = _number_to_float(amount)

    if number is None:
        return None

    multiplier = _get_scale_multiplier(scale)

    return round(number * multiplier, 2)


# ---------------------------------------------------------
# Currency Extraction
# ---------------------------------------------------------

def _normalize_currency(
    currency_text: Optional[str],
    scale_text: Optional[str],
) -> str:

    if currency_text:
        value = currency_text.lower().strip()
        value = value.replace(".", "").replace(" ", "")

        if value in {"₹", "rs", "inr"}:
            return "INR"

        if value in {"$", "usd"}:
            return "USD"

        if value in {"€", "eur"}:
            return "EUR"

        if value in {"£", "gbp"}:
            return "GBP"

    if scale_text:
        normalized = scale_text.lower().strip()

        if (
            "lpa" in normalized
            or "lakh" in normalized
            or "lac" in normalized
            or "crore" in normalized
            or normalized == "cr"
        ):
            return "INR"

    return "UNKNOWN"

# ---------------------------------------------------------
# Pay Frequency
# ---------------------------------------------------------

def _normalize_frequency(
    frequency_text: Optional[str],
    scale_text: Optional[str],
) -> str:
    if frequency_text:
        value = frequency_text.lower().strip()

        if any(
            word in value
            for word in (
                "annum",
                "year",
                "annual",
                "yearly",
            )
        ):
            return "ANNUAL"

        if "month" in value:
            return "MONTHLY"

        if "week" in value:
            return "WEEKLY"

        if "hour" in value:
            return "HOURLY"

    if scale_text:
        normalized = scale_text.lower()

        if (
            "lpa" in normalized
            or "per annum" in normalized
            or "per year" in normalized
            or "lakh" in normalized
            or "lac" in normalized
            or "crore" in normalized
            or normalized == "cr"
        ):
            return "ANNUAL"

    return "UNKNOWN"


# ---------------------------------------------------------
# Sentence Splitting
# ---------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    if not text:
        return []

    # Protect the period in the Indian currency abbreviation Rs.
    placeholder = "__RS_PERIOD__"

    protected_text = re.sub(
        r"\bRs\.(?=\s*\d)",
        f"Rs{placeholder}",
        text,
        flags=re.IGNORECASE,
    )

    sentences = re.split(
        r"(?<=[.!?])\s+|[\n;]+",
        protected_text,
    )

    return [
        sentence.replace(f"Rs{placeholder}", "Rs.").strip()
        for sentence in sentences
        if sentence.strip()
    ]


def _extract_salary_from_sentence(
    sentence: str,
) -> Optional[dict[str, Any]]:

    if not sentence:
        return None

    match = SALARY_AMOUNT_PATTERN.search(sentence)

    if not match:
        return None

    groups = match.groupdict()

    amount1 = groups.get("amount1")
    amount2 = groups.get("amount2")

    scale1 = groups.get("scale1")
    scale2 = groups.get("scale2")

    currency1 = groups.get("currency")
    currency2 = groups.get("currency2")

    frequency_text = groups.get("frequency")

    # Apply a shared scale to both range values.
    if scale1 and not scale2:
        scale2 = scale1
    elif scale2 and not scale1:
        scale1 = scale2

    minimum = _normalize_amount(amount1, scale1)

    maximum = (
        _normalize_amount(amount2, scale2)
        if amount2
        else minimum
    )

    if minimum is None or maximum is None:
        return None

    # Reject reversed ranges.
    if amount2 is not None and maximum < minimum:
        return None

    # -----------------------------------------------------
    # Currency Detection
    # -----------------------------------------------------

    # Detect explicit currency markers from the full sentence.
    # This takes priority over the regex-captured currency.
    currency_match = re.search(
        r"(?<![A-Za-z])(?:Rs\.?|INR|USD|EUR|GBP|₹|\$|€|£)(?![A-Za-z])",
        sentence,
        re.IGNORECASE,
    )

    if currency_match:
        currency_text = currency_match.group(0)
    else:
        currency_text = currency1 or currency2
        
        
    currency = _normalize_currency(
        currency_text,
        scale1 or scale2,
    )
    
    pay_frequency = _normalize_frequency(
        frequency_text,
        scale1 or scale2,
    )

    return {
        "minimum": minimum,
        "maximum": maximum,
        "currency": currency,
        "pay_frequency": pay_frequency,
        "is_range": amount2 is not None,
        "raw_text": match.group(0).strip(),
    }
    
# ---------------------------------------------------------
# Salary Extraction
# ---------------------------------------------------------

def _extract_expected_salary(
    text: str,
) -> tuple[Optional[dict], Optional[str]]:

    if not text:
        return None, None

    sentences = _split_sentences(text)

    # Prefer explicit expected-salary statements.
    for sentence in sentences:

        expected_match = EXPECTED_SALARY_CONTEXT.search(
            sentence
        )

        if not expected_match:
            continue

        # If current and expected salary occur in the same
        # sentence, extract only the expected-salary portion.
        candidate_sentence = sentence[
            expected_match.start():
        ]

        extracted = _extract_salary_from_sentence(
            candidate_sentence
        )

        if extracted:
            return extracted, sentence

    # Accept direct salary answers such as:
    # "8 LPA."
    # "₹50,000 per month."
    for sentence in sentences:

        if CURRENT_SALARY_CONTEXT.search(sentence):
            continue

        if not GENERAL_SALARY_CONTEXT.search(sentence):

            has_salary_unit = bool(
                re.search(
                    r"\b(?:lpa|lakhs?|lacs?|crores?|"
                    r"per\s+annum|per\s+year|"
                    r"per\s+month|monthly)\b",
                    sentence,
                    re.IGNORECASE,
                )
                or re.search(r"[₹$€£]", sentence)
            )

            if not has_salary_unit:
                continue

        extracted = _extract_salary_from_sentence(
            sentence
        )

        if extracted:
            return extracted, sentence

    return None, None
# ---------------------------------------------------------
# Negotiability
# ---------------------------------------------------------

def _extract_negotiability(
    text: str,
) -> tuple[Optional[bool], Optional[str]]:
    if not text:
        return None, None

    match = NEGOTIABLE_PATTERN.search(text)

    if match:
        return True, match.group(0)

    return None, None


# ---------------------------------------------------------
# Missing and Vague Fields
# ---------------------------------------------------------

def _identify_missing_and_vague_fields(
    text: str,
    salary_data: Optional[dict],
    negotiable: Optional[bool],
) -> tuple[list[str], list[str]]:

    missing_fields = []
    vague_fields = []

    if not text:
        return (
            [
                "expected_salary",
                "currency",
                "pay_frequency",
            ],
            [],
        )

    vague_match = VAGUE_SALARY_PATTERN.search(text)

    if salary_data is None:

        if vague_match:
            vague_fields.append("expected_salary")
        else:
            missing_fields.append("expected_salary")

        if vague_match:
            vague_fields.append("salary_amount")
        else:
            missing_fields.append("salary_amount")

        return (
            list(dict.fromkeys(missing_fields)),
            list(dict.fromkeys(vague_fields)),
        )

    if salary_data["currency"] == "UNKNOWN":
        missing_fields.append("currency")

    if salary_data["pay_frequency"] == "UNKNOWN":
        missing_fields.append("pay_frequency")

    return (
        list(dict.fromkeys(missing_fields)),
        list(dict.fromkeys(vague_fields)),
    )


# ---------------------------------------------------------
# Confidence
# ---------------------------------------------------------

def _calculate_confidence(
    salary_data: Optional[dict],
    vague_fields: list[str],
) -> str:

    if salary_data is None:
        return "LOW"

    score = 1

    if salary_data["currency"] != "UNKNOWN":
        score += 1

    if salary_data["pay_frequency"] != "UNKNOWN":
        score += 1

    if salary_data["is_range"]:
        score += 1

    if vague_fields:
        score -= 1

    if score >= 3:
        return "HIGH"

    if score >= 2:
        return "MEDIUM"

    return "LOW"


# ---------------------------------------------------------
# Main Service
# ---------------------------------------------------------

def extract_salary_expectation_intent(
    transcript_text: str,
) -> dict[str, Any]:
    """
    Extract expected salary information from a candidate's
    conversational transcript.

    Expected salary values are normalized to actual numeric
    amounts in the stated currency and pay frequency.

    Examples:
        6 LPA -> 600000 INR annually
        50000 per month -> 50000 INR monthly, if INR is stated
        8-10 LPA -> 800000-1000000 INR annually
    """

    if not isinstance(transcript_text, str):
        transcript_text = ""

    original_text = transcript_text.strip()

    if not original_text:
        return {
            "intent": INTENT,
            "status": "MISSING",
            "expected_salary_min": None,
            "expected_salary_max": None,
            "currency": "UNKNOWN",
            "pay_frequency": "UNKNOWN",
            "is_salary_range": False,
            "negotiable": None,
            "missing_fields": [
                "expected_salary",
                "currency",
                "pay_frequency",
            ],
            "vague_fields": [],
            "evidence": {},
            "confidence": "LOW",
        }

    salary_data, salary_evidence = _extract_expected_salary(
        original_text
    )

    negotiable, negotiability_evidence = (
        _extract_negotiability(original_text)
    )

    missing_fields, vague_fields = (
        _identify_missing_and_vague_fields(
            original_text,
            salary_data,
            negotiable,
        )
    )

    if salary_data is None:

        if vague_fields:
            status = "VAGUE"
        else:
            status = "MISSING"

    elif missing_fields:
        status = "PARTIAL"

    else:
        status = "EXTRACTED"

    confidence = _calculate_confidence(
        salary_data,
        vague_fields,
    )

    return {
        "intent": INTENT,
        "status": status,

        "expected_salary_min": (
            salary_data["minimum"]
            if salary_data
            else None
        ),

        "expected_salary_max": (
            salary_data["maximum"]
            if salary_data
            else None
        ),

        "currency": (
            salary_data["currency"]
            if salary_data
            else "UNKNOWN"
        ),

        "pay_frequency": (
            salary_data["pay_frequency"]
            if salary_data
            else "UNKNOWN"
        ),

        "is_salary_range": (
            salary_data["is_range"]
            if salary_data
            else False
        ),

        "negotiable": negotiable,

        "missing_fields": missing_fields,

        "vague_fields": vague_fields,

        "evidence": {
            "salary": salary_evidence,
            "salary_amount": (
                salary_data["raw_text"]
                if salary_data
                else None
            ),
            "negotiability": negotiability_evidence,
        },

        "confidence": confidence,
    }


# ---------------------------------------------------------
# Compatibility Alias
# ---------------------------------------------------------

def process_salary_expectation_intent(
    transcript_text: str,
) -> dict[str, Any]:
    return extract_salary_expectation_intent(
        transcript_text
    )
