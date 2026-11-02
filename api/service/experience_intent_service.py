"""
experience_intent_service.py

Responsibilities
-----------------
1. Extract experience information from conversational transcripts.
2. Identify total and relevant experience when explicitly stated.
3. Extract job roles and validate them using existing resume title modules.
4. Extract spoken duration expressions.
5. Identify employment status.
6. Detect fresher, experienced, missing, and vague answers.
7. Preserve evidence for recruiter review.
8. Return structured semantic experience objects.

Important
---------
This service processes conversational transcript answers.
It does not replace or modify the resume experience extraction pipeline.
"""

import re
from typing import Optional, Any


# ---------------------------------------------------------
# Existing Job Title Resolver and Validator
# ---------------------------------------------------------

from document_processing.resume.entity_extracter.experience.title_alases_resolver import (
    resolve_title_alias,
)

from document_processing.resume.entity_extracter.experience.title_validator import (
    validate_title,
)


# ---------------------------------------------------------
# Constants
# ---------------------------------------------------------

INTENT = "EXPERIENCE"

EXPERIENCE_STATUSES = {
    "MISSING",
    "VAGUE",
    "PARTIAL",
    "EXTRACTED",
}

EXPERIENCE_LEVELS = {
    "FRESHER",
    "EXPERIENCED",
    "UNKNOWN",
}

EMPLOYMENT_STATUSES = {
    "CURRENTLY_WORKING",
    "NOT_WORKING",
    "FREELANCER",
    "STUDENT",
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
}

NUMBER_PATTERN = (
    r"(?:\d+(?:\.\d+)?|"
    r"a|an|one|two|three|four|five|six|seven|eight|"
    r"nine|ten|eleven|twelve)"
)

YEAR_DURATION_PATTERN = re.compile(
    rf"\b(?P<years>{NUMBER_PATTERN})\s*"
    rf"(?:years?|yrs?)\b"
    rf"(?:\s*(?:and|,)?\s*"
    rf"(?P<months>{NUMBER_PATTERN})\s*"
    rf"(?:months?|mos?)\b)?",
    re.IGNORECASE,
)

MONTH_DURATION_PATTERN = re.compile(
    rf"\b(?P<months>{NUMBER_PATTERN})\s*"
    rf"(?:months?|mos?)\b",
    re.IGNORECASE,
)

VAGUE_EXPERIENCE_PATTERN = re.compile(
    r"\b(?:"
    r"some experience|"
    r"few years|"
    r"several years|"
    r"many years|"
    r"long experience|"
    r"good experience|"
    r"quite experienced|"
    r"a lot of experience|"
    r"worked for some time|"
    r"short experience"
    r")\b",
    re.IGNORECASE,
)

FRESHER_PATTERN = re.compile(
    r"\b(?:"
    r"fresher|"
    r"fresh graduate|"
    r"recent graduate|"
    r"no work experience|"
    r"without work experience|"
    r"no professional experience|"
    r"never worked professionally"
    r")\b",
    re.IGNORECASE,
)

EXPERIENCED_PATTERN = re.compile(
    r"\b(?:"
    r"experienced professional|"
    r"working professional|"
    r"have experience|"
    r"years of experience|"
    r"months of experience|"
    r"previously worked|"
    r"worked as"
    r")\b",
    re.IGNORECASE,
)

CURRENTLY_WORKING_PATTERN = re.compile(
    r"\b(?:"
    r"currently working|"
    r"presently working|"
    r"currently employed|"
    r"working at present|"
    r"still working|"
    r"employed currently"
    r")\b",
    re.IGNORECASE,
)

NOT_WORKING_PATTERN = re.compile(
    r"\b(?:"
    r"not working|"
    r"currently unemployed|"
    r"unemployed|"
    r"not employed|"
    r"left my job|"
    r"resigned|"
    r"looking for a job|"
    r"currently seeking a job"
    r")\b",
    re.IGNORECASE,
)

FREELANCER_PATTERN = re.compile(
    r"\b(?:"
    r"freelancer|"
    r"freelancing|"
    r"self-employed|"
    r"independent consultant"
    r")\b",
    re.IGNORECASE,
)

STUDENT_PATTERN = re.compile(
    r"\b(?:"
    r"currently studying|"
    r"student|"
    r"pursuing my degree|"
    r"still studying"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------
# Number Conversion
# ---------------------------------------------------------

def _number_to_float(value: Optional[str]) -> Optional[float]:
    """
    Convert numeric text or supported number words into float.

    Examples:
        "2"       -> 2.0
        "1.5"     -> 1.5
        "two"     -> 2.0
        "a"       -> 1.0
    """

    if not value:
        return None

    value = value.strip().lower()

    try:
        return float(value)
    except ValueError:
        return NUMBER_WORDS.get(value)


# ---------------------------------------------------------
# Duration Extraction
# ---------------------------------------------------------

def _extract_duration_mentions(text: str) -> list[dict]:
    """
    Extract spoken duration expressions.

    Examples:
        two years
        18 months
        1.5 years
        one year and six months

    Returns:
        [
            {
                "raw_text": "two years",
                "duration_years": 2.0,
                "start": 10,
                "end": 19
            }
        ]
    """

    if not text:
        return []

    mentions = []
    occupied_ranges = []

    for match in YEAR_DURATION_PATTERN.finditer(text):

        years = _number_to_float(
            match.group("years")
        ) or 0.0

        months = _number_to_float(
            match.group("months")
        ) or 0.0

        duration_years = years + (months / 12)

        mentions.append({
            "raw_text": match.group(0),
            "duration_years": round(duration_years, 2),
            "start": match.start(),
            "end": match.end(),
        })

        occupied_ranges.append(
            (match.start(), match.end())
        )

    # Extract month-only expressions.
    for match in MONTH_DURATION_PATTERN.finditer(text):

        if any(
            match.start() >= start and match.end() <= end
            for start, end in occupied_ranges
        ):
            continue

        months = _number_to_float(
            match.group("months")
        )

        if months is None:
            continue

        mentions.append({
            "raw_text": match.group(0),
            "duration_years": round(months / 12, 2),
            "start": match.start(),
            "end": match.end(),
        })

    mentions.sort(
        key=lambda item: item["start"]
    )

    return mentions


# ---------------------------------------------------------
# Sentence Splitting
# ---------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """
    Split transcript text into simple sentence-like sections.
    """

    if not text:
        return []

    return [
        part.strip()
        for part in re.split(
            r"(?<=[.!?])\s+|[\n;]+",
            text
        )
        if part.strip()
    ]


# ---------------------------------------------------------
# Explicit Total Experience
# ---------------------------------------------------------

def _extract_total_experience(
    text: str,
    duration_mentions: list[dict],
) -> tuple[Optional[float], Optional[str]]:
    """
    Extract explicitly stated overall experience.

    Does not calculate total experience by adding job durations.
    """

    if not text or not duration_mentions:
        return None, None

    sentences = _split_sentences(text)

    total_label_pattern = re.compile(
        r"\b(?:total|overall|combined|altogether)\b",
        re.IGNORECASE,
    )

    for sentence in sentences:

        sentence_mentions = _extract_duration_mentions(
            sentence
        )

        if not sentence_mentions:
            continue

        has_experience = bool(
            re.search(r"\bexperience\b", sentence, re.IGNORECASE)
        )

        if not has_experience:
            continue

        if total_label_pattern.search(sentence):

            mention = sentence_mentions[0]

            return (
                mention["duration_years"],
                sentence,
            )

    # General statements such as:
    # "I have two years of experience."
    # "I have worked for 18 months."

    for sentence in sentences:

        sentence_mentions = _extract_duration_mentions(
            sentence
        )

        if not sentence_mentions:
            continue

        if re.search(
            r"\b(?:experience|experienced)\b",
            sentence,
            re.IGNORECASE,
        ):

            if re.search(
                r"\brelevant experience\b",
                sentence,
                re.IGNORECASE,
            ):
                continue

            mention = sentence_mentions[0]

            return (
                mention["duration_years"],
                sentence,
            )

    return None, None


# ---------------------------------------------------------
# Explicit Relevant Experience
# ---------------------------------------------------------

def _extract_relevant_experience(
    text: str,
) -> tuple[Optional[float], Optional[str]]:
    """
    Extract experience explicitly described as relevant.

    Example:
        "I have 2 years of relevant experience."
    """

    if not text:
        return None, None

    sentences = _split_sentences(text)

    relevant_pattern = re.compile(
        r"\b(?:relevant|related|directly related)\b",
        re.IGNORECASE,
    )

    for sentence in sentences:

        if not relevant_pattern.search(sentence):
            continue

        mentions = _extract_duration_mentions(
            sentence
        )

        if mentions:

            return (
                mentions[0]["duration_years"],
                sentence,
            )

    return None, None


# ---------------------------------------------------------
# Job Role Extraction
# ---------------------------------------------------------

ROLE_PATTERNS = [
    re.compile(
        r"\b(?:worked|work|working|employed)\s+"
        r"(?:as|like)\s+(?:a|an)?\s*"
        r"(?P<title>[^,.!?;\n]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:experience|experienced)\s+as\s+"
        r"(?:a|an)?\s*"
        r"(?P<title>[^,.!?;\n]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:my role was|my position was|"
        r"job role was)\s+(?:a|an)?\s*"
        r"(?P<title>[^,.!?;\n]+)",
        re.IGNORECASE,
    ),
]

ROLE_STOP_PATTERN = re.compile(
    r"\b(?:for|at|with|from|since|during|"
    r"between|in the company|currently)\b",
    re.IGNORECASE,
)


def _clean_role_candidate(candidate: str) -> str:
    """
    Remove trailing duration, employer and conversational text.
    """

    if not candidate:
        return ""

    candidate = candidate.strip(
        " \t-–—|,;:"
    )

    stop_match = ROLE_STOP_PATTERN.search(
        candidate
    )

    if stop_match:
        candidate = candidate[:stop_match.start()]

    candidate = re.sub(
        r"\s+",
        " ",
        candidate,
    )

    return candidate.strip()


def _validate_role(candidate: str) -> Optional[dict]:
    """
    Resolve aliases and validate a role using existing modules.
    """

    if not candidate:
        return None

    canonical_title = resolve_title_alias(
        candidate
    )

    if not canonical_title:
        return None

    validation = validate_title(
        canonical_title
    )

    if not validation:
        return None

    return validation


def _extract_job_roles(text: str) -> list[dict]:
    """
    Extract job roles from conversational statements.

    Each role preserves:
        - Original title phrase
        - Canonical validated title
        - Title ID
        - Category
        - Matching method
        - Confidence
        - Duration, when stated in the same sentence
        - Evidence
    """

    if not text:
        return []

    roles = []
    seen = set()

    for sentence in _split_sentences(text):

        for pattern in ROLE_PATTERNS:

            for match in pattern.finditer(sentence):

                raw_candidate = match.group(
                    "title"
                )

                candidate = _clean_role_candidate(
                    raw_candidate
                )

                if not candidate:
                    continue

                # Avoid accepting excessively long phrases.
                if len(candidate.split()) > 7:
                    continue

                validation = _validate_role(
                    candidate
                )

                if not validation:
                    continue

                canonical_title = validation.get(
                    "title"
                )

                if not canonical_title:
                    continue

                role_key = canonical_title.casefold()

                if role_key in seen:
                    continue

                seen.add(role_key)

                sentence_durations = (
                    _extract_duration_mentions(sentence)
                )

                role_duration = (
                    sentence_durations[0]["duration_years"]
                    if sentence_durations
                    else None
                )

                roles.append({
                    "original_title": candidate,
                    "title_id": validation.get("title_id"),
                    "title": canonical_title,
                    "category": validation.get(
                        "category",
                        "Unknown",
                    ),
                    "matched_by": validation.get(
                        "matched_by",
                        "none",
                    ),
                    "confidence": validation.get(
                        "confidence",
                        0,
                    ),
                    "duration_years": role_duration,
                    "evidence": sentence,
                })

    return roles


# ---------------------------------------------------------
# Employment Status
# ---------------------------------------------------------

def _extract_employment_status(text: str) -> tuple[str, Optional[str]]:
    """
    Identify the candidate's explicitly stated employment status.

    Conflicting statements are not automatically resolved.
    """

    if not text:
        return "UNKNOWN", None

    matches = []

    patterns = [
        (
            FREELANCER_PATTERN,
            "FREELANCER",
        ),
        (
            CURRENTLY_WORKING_PATTERN,
            "CURRENTLY_WORKING",
        ),
        (
            NOT_WORKING_PATTERN,
            "NOT_WORKING",
        ),
        (
            STUDENT_PATTERN,
            "STUDENT",
        ),
    ]

    for pattern, status in patterns:

        match = pattern.search(text)

        if match:
            matches.append({
                "status": status,
                "evidence": match.group(0),
            })

    unique_statuses = {
        item["status"]
        for item in matches
    }

    if len(unique_statuses) == 1:

        selected = matches[0]

        return (
            selected["status"],
            selected["evidence"],
        )

    # Multiple different statuses indicate ambiguity.
    if len(unique_statuses) > 1:
        return "UNKNOWN", "Conflicting employment status statements"

    return "UNKNOWN", None


# ---------------------------------------------------------
# Experience Level
# ---------------------------------------------------------

def _identify_experience_level(
    text: str,
    total_experience: Optional[float],
    job_roles: list[dict],
) -> str:
    """
    Identify fresher/experienced status without inventing experience.
    """

    if not text:
        return "UNKNOWN"

    if FRESHER_PATTERN.search(text):
        return "FRESHER"

    if (
        total_experience is not None
        or job_roles
        or EXPERIENCED_PATTERN.search(text)
    ):
        return "EXPERIENCED"

    return "UNKNOWN"


# ---------------------------------------------------------
# Missing and Vague Information
# ---------------------------------------------------------

def _identify_missing_and_vague_fields(
    text: str,
    total_experience: Optional[float],
    relevant_experience: Optional[float],
    job_roles: list[dict],
    employment_status: str,
) -> tuple[list[str], list[str]]:
    """
    Identify fields that are missing or vaguely expressed.

    A missing value is not automatically treated as zero.
    """

    missing_fields = []
    vague_fields = []

    if not text or not text.strip():
        return (
            [
                "total_experience",
                "job_roles",
                "employment_status",
            ],
            [],
        )

    vague_match = VAGUE_EXPERIENCE_PATTERN.search(
        text
    )

    if vague_match:
        vague_fields.append(
            "experience_duration"
        )

    if total_experience is None and not vague_match:
        missing_fields.append(
            "total_experience"
        )

    if relevant_experience is None:
        missing_fields.append(
            "relevant_experience"
        )

    if not job_roles:
        if vague_match:
            vague_fields.append(
                "job_roles"
            )
        else:
            missing_fields.append(
                "job_roles"
            )

    if employment_status == "UNKNOWN":
        missing_fields.append(
            "employment_status"
        )

    return (
        list(dict.fromkeys(missing_fields)),
        list(dict.fromkeys(vague_fields)),
    )


# ---------------------------------------------------------
# Confidence
# ---------------------------------------------------------

def _calculate_confidence(
    total_experience: Optional[float],
    relevant_experience: Optional[float],
    job_roles: list[dict],
    employment_status: str,
    vague_fields: list[str],
) -> str:
    """
    Estimate extraction completeness.

    This is extraction confidence, not a candidate quality score.
    """

    score = 0

    if total_experience is not None:
        score += 2

    if relevant_experience is not None:
        score += 1

    if job_roles:
        score += 2

    if employment_status != "UNKNOWN":
        score += 1

    if vague_fields:
        score -= 1

    if score >= 4:
        return "HIGH"

    if score >= 2:
        return "MEDIUM"

    return "LOW"


# ---------------------------------------------------------
# Main Service
# ---------------------------------------------------------


def extract_experience_intent(
    transcript_text: str,
) -> dict[str, Any]:
    """
    Extract experience-related semantic information
    from a candidate's conversational transcript.

    Parameters
    ----------
    transcript_text : str
        Normalized candidate transcript answer.

    Returns
    -------
    dict
        Structured experience intent object.
    """

    if not isinstance(transcript_text, str):
        transcript_text = ""

    original_text = transcript_text.strip()

    # -------------------------------------------------
    # Empty Answer
    # -------------------------------------------------

    if not original_text:
        return {
            "intent": INTENT,
            "status": "MISSING",
            "experience_level": "UNKNOWN",
            "total_experience_years": None,
            "relevant_experience_years": None,
            "employment_status": "UNKNOWN",
            "job_roles": [],
            "duration_mentions": [],
            "missing_fields": [
                "total_experience",
                "job_roles",
                "employment_status",
            ],
            "vague_fields": [],
            "evidence": {},
            "confidence": "LOW",
        }

    # -------------------------------------------------
    # Extract Duration Mentions
    # -------------------------------------------------

    duration_mentions = _extract_duration_mentions(
        original_text
    )

    # -------------------------------------------------
    # Extract Total Experience
    # -------------------------------------------------

    total_experience, total_evidence = (
        _extract_total_experience(
            original_text,
            duration_mentions,
        )
    )

    # -------------------------------------------------
    # Extract Relevant Experience
    # -------------------------------------------------

    relevant_experience, relevant_evidence = (
        _extract_relevant_experience(
            original_text
        )
    )

    # -------------------------------------------------
    # Extract Job Roles
    # -------------------------------------------------

    job_roles = _extract_job_roles(
        original_text
    )

    # -------------------------------------------------
    # Extract Employment Status
    # -------------------------------------------------

    employment_status, employment_evidence = (
        _extract_employment_status(
            original_text
        )
    )

    # -------------------------------------------------
    # Identify Experience Level
    # -------------------------------------------------

    experience_level = _identify_experience_level(
        original_text,
        total_experience,
        job_roles,
    )

    # An explicitly stated fresher answer means zero
    # professional experience, not an unknown duration.

    if (
        experience_level == "FRESHER"
        and total_experience is None
    ):
        total_experience = 0.0

        total_evidence = (
            "Candidate explicitly identified as a fresher."
        )

    # -------------------------------------------------
    # Identify Missing and Vague Fields
    # -------------------------------------------------

    missing_fields, vague_fields = (
        _identify_missing_and_vague_fields(
            original_text,
            total_experience,
            relevant_experience,
            job_roles,
            employment_status,
        )
    )

    # -------------------------------------------------
    # Determine Extraction Status
    # -------------------------------------------------

    has_experience_signal = (
        total_experience is not None
        or bool(job_roles)
        or experience_level == "FRESHER"
    )

    if not has_experience_signal and vague_fields:
        status = "VAGUE"

    elif not has_experience_signal:
        status = "MISSING"

    elif vague_fields:
        status = "PARTIAL"

    else:
        status = "EXTRACTED"

    # -------------------------------------------------
    # Calculate Extraction Confidence
    # -------------------------------------------------

    confidence = _calculate_confidence(
        total_experience,
        relevant_experience,
        job_roles,
        employment_status,
        vague_fields,
    )

    # -------------------------------------------------
    # Final Semantic Object
    # -------------------------------------------------

    return {
        "intent": INTENT,
        "status": status,
        "experience_level": experience_level,

        "total_experience_years": total_experience,

        "relevant_experience_years": relevant_experience,

        "employment_status": employment_status,

        "job_roles": job_roles,

        "duration_mentions": duration_mentions,

        "missing_fields": missing_fields,

        "vague_fields": vague_fields,

        "evidence": {
            "total_experience": total_evidence,
            "relevant_experience": relevant_evidence,
            "employment_status": employment_evidence,
        },

        "confidence": confidence,
    }

# ---------------------------------------------------------
# Compatibility Alias
# ---------------------------------------------------------

def process_experience_intent(
    transcript_text: str,
) -> dict[str, Any]:
    """
    Alternative service entry point.
    """

    return extract_experience_intent(
        transcript_text
    )