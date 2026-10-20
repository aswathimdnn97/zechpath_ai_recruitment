"""Extract and validate locations from resume experience blocks."""

import json
import re
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]

LOCATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "locations"
    / "location_dictionary.json"
)

WORK_ARRANGEMENTS = {
    "remote": "Remote",
    "hybrid": "Hybrid",
    "onsite": "On-site",
    "on-site": "On-site",
    "on site": "On-site",
}

# ------------------------------------------------------------------
# LOCATION DICTIONARY
# ------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_locations_cached():
    """Load and cache locations once per process."""
    if not LOCATION_FILE.exists():
        return ()

    try:
        with open(LOCATION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return ()

    if isinstance(data, dict):
        locations = data.get("locations", [])
        return tuple(locations) if isinstance(locations, list) else ()

    if isinstance(data, list):
        return tuple(data)

    return ()


def load_locations():
    """Return the cached location dictionary as a list."""
    return list(_load_locations_cached())


LOCATION_LOOKUP = frozenset(
    item.strip().casefold()
    for item in _load_locations_cached()
    if isinstance(item, str) and item.strip()
)


# ------------------------------------------------------------------
# PATTERNS
# ------------------------------------------------------------------

MONTH_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
    r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

DATE_PATTERN = re.compile(
    rf"\b{MONTH_PATTERN}\s+\d{{4}}\b",
    re.IGNORECASE,
)

YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")

DATE_RANGE_PATTERN = re.compile(
    rf"""
    \b
    (?:{MONTH_PATTERN}\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}})
    \s*
    (?:-|–|—|to|\uFFFD)
    \s*
    (?:
        {MONTH_PATTERN}\s+\d{{4}}
        |\d{{1,2}}/\d{{4}}
        |\d{{4}}
        |Present
        |Current
        |Now
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

WHITESPACE_PATTERN = re.compile(r"\s+")
SEPARATOR_PATTERN = re.compile(r"\s*\|\s*")
DASH_SEPARATOR_PATTERN = re.compile(r"\s+[-–—\uFFFD]\s+")

CITY_STATE_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z .'-]*,\s*[A-Za-z][A-Za-z .'-]*$"
)

COMPANY_INDICATOR_PATTERN = re.compile(
    r"\b(?:"
    r"llp|ltd|limited|pvt|private|"
    r"inc|incorporated|corporation|corp|"
    r"technologies|solutions|industries|"
    r"learning hub|business|digital"
    r")\b",
    re.IGNORECASE,
)

LOCATION_LABEL_PATTERN = re.compile(
    r"^\s*(?:"
    r"location|based in|based at|city|address|"
    r"work location|current location"
    r")\s*[:\-]\s*",
    re.IGNORECASE,
)

LOCATION_STOP_WORDS = {
    "experience", "responsibilities", "responsibility",
    "description", "developed", "working", "worked",
    "project", "projects", "skills", "technologies",
    "technology", "using", "management", "developer",
    "engineer", "intern", "internship", "team", "client",
    "clients", "company", "organization", "organisation",
    "created", "implemented", "practiced", "practice",
    "tested", "testing", "built", "designed", "application",
    "applications", "backend", "frontend", "features",
    "responsible", "collaborated", "maintained",
}

LOCATION_LABELS = {"remote", "hybrid", "onsite", "on-site"}


# ------------------------------------------------------------------
# COMMON HELPERS
# ------------------------------------------------------------------

def remove_date_text(text):
    """Remove date ranges, month-year expressions, and years."""
    if not text:
        return ""

    text = DATE_RANGE_PATTERN.sub(" ", text)
    text = DATE_PATTERN.sub(" ", text)
    text = YEAR_PATTERN.sub(" ", text)

    return WHITESPACE_PATTERN.sub(" ", text).strip()


def contains_company_indicator(text):
    """Identify common company-name terms."""
    return bool(text and COMPANY_INDICATOR_PATTERN.search(text))


def looks_like_description(text):
    """Reject sentence-like content that is unlikely to be a location."""
    if not text:
        return True

    lower_text = text.casefold().strip()
    words = re.findall(r"[A-Za-z]+", lower_text)

    if not words or len(words) > 6:
        return True

    if any(word in LOCATION_STOP_WORDS for word in words):
        return True

    if lower_text.startswith((
        "responsible for", "worked on", "developed", "built ",
        "designed ", "managed ", "implemented ", "using ",
        "created ", "practiced ", "tested ", "collaborated ",
        "maintained ", "and ",
    )):
        return True

    return bool(re.search(r"[.!?;]", text))


def clean_location_candidate(candidate):
    """Clean a candidate without automatically accepting it."""
    if not isinstance(candidate, str) or not candidate.strip():
        return ""

    candidate = LOCATION_LABEL_PATTERN.sub("", candidate)
    candidate = candidate.strip(" \t,;|:-–—\uFFFD")
    candidate = WHITESPACE_PATTERN.sub(" ", candidate).strip()

    if not candidate or looks_like_description(candidate):
        return ""

    return candidate


# ------------------------------------------------------------------
# LOCATION VALIDATION
# ------------------------------------------------------------------

def validate_location(value):
    """
    Validate a location from a dictionary, explicit location field,
    or generic city/state pair.

    Unknown single-word locations are not accepted here. Inline
    experience locations are handled separately below.
    """
    if not isinstance(value, str):
        return None

    candidate = clean_location_candidate(value)
    if not candidate:
        return None

    normalized = candidate.casefold()
    
    # Recognize work arrangements without requiring dictionary entries.
    if normalized in WORK_ARRANGEMENTS:
        return WORK_ARRANGEMENTS[normalized]

    if normalized in LOCATION_LOOKUP:
        return candidate

    if normalized in LOCATION_LABELS:
        return candidate if normalized in LOCATION_LOOKUP else None

    if YEAR_PATTERN.search(candidate):
        return None

    if contains_company_indicator(candidate):
        return None

    if CITY_STATE_PATTERN.fullmatch(candidate):
        parts = [part.strip() for part in candidate.split(",")]

        if len(parts) == 2 and all(parts):
            if not any(
                word.casefold() in LOCATION_STOP_WORDS
                for word in re.findall(r"[A-Za-z]+", candidate)
            ):
                return candidate

    return None


def _validate_inline_city(value):
    """
    Validate a city taken from the company/location portion of an
    experience heading. A single-word city need not be in the
    dictionary, because the explicit header structure provides context.
    """
    if not isinstance(value, str):
        return None

    candidate = WHITESPACE_PATTERN.sub(" ", value.strip()).strip(" ,")

    if not candidate:
        return None

    if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", candidate):
        return None

    if looks_like_description(candidate):
        return None

    if contains_company_indicator(candidate):
        return None

    # Prefer dictionary spelling when an exact entry exists.
    for known_location in load_locations():
        if (
            isinstance(known_location, str)
            and known_location.casefold() == candidate.casefold()
        ):
            return known_location

    return candidate


# ------------------------------------------------------------------
# EXPERIENCE BLOCK NORMALIZATION
# ------------------------------------------------------------------

def _get_lines(block):
    """Convert a string, list, or dictionary into lines."""
    if isinstance(block, str):
        values = block.splitlines()

    elif isinstance(block, list):
        values = []
        for item in block:
            if isinstance(item, str):
                values.extend(item.splitlines())
            elif isinstance(item, list):
                values.extend(
                    line
                    for line in item
                    if isinstance(line, str)
                )

    elif isinstance(block, dict):
        values = []
        for value in block.values():
            if isinstance(value, str):
                values.extend(value.splitlines())
            elif isinstance(value, list):
                values.extend(
                    item
                    for item in value
                    if isinstance(item, str)
                )
    else:
        return []

    return [
        line.strip()
        for line in values
        if isinstance(line, str) and line.strip()
    ]


# ------------------------------------------------------------------
# INLINE COMPANY / LOCATION HEADINGS
# ------------------------------------------------------------------

def extract_inline_location(block):
    """
    Extract the location before '|' in an inline experience heading.

    Example:
        "Sorice Solutions Private Limited, Palarivattom | Java Developer Trainee July 2022 – July 2023"

    Returns:
        "Palarivattom"
    """
    for line in _get_lines(block):
        if "|" not in line:
            continue

        # Only inspect the left side, which contains company and location.
        company_location = SEPARATOR_PATTERN.split(
            line,
            maxsplit=1,
        )[0].strip()

        # Expected structure: company, location
        if "," not in company_location:
            continue

        parts = [
            part.strip()
            for part in company_location.split(",")
            if part.strip()
        ]

        if len(parts) < 2:
            continue

        location = _validate_inline_city(parts[-1])

        if location:
            return location

    return None


# ------------------------------------------------------------------
# LOCATION EXTRACTION FROM DICTIONARY
# ------------------------------------------------------------------

def extract_location_from_dictionary(line, locations=None):
    """Find the longest known location contained in a line."""
    if not isinstance(line, str) or not line.strip():
        return None

    if locations is None:
        locations = load_locations()

    matches = []

    for location in locations:
        if not isinstance(location, str) or not location.strip():
            continue

        pattern = rf"(?<!\w){re.escape(location.strip())}(?!\w)"

        if re.search(pattern, line, re.IGNORECASE):
            matches.append(location.strip())

    matches.sort(key=len, reverse=True)

    for location in matches:
        validated = validate_location(location)
        if validated:
            return validated

    return None


# ------------------------------------------------------------------
# LOCATION EXTRACTION FROM SEPARATORS
# ------------------------------------------------------------------

def extract_location_from_separator(line):
    """Extract a location from pipe- or dash-separated text."""
    if not isinstance(line, str) or not line.strip():
        return None

    inline_location = extract_inline_location(line)
    if inline_location:
        return inline_location

    text = remove_date_text(line.strip())
    if not text:
        return None

    if "|" in text:
        parts = SEPARATOR_PATTERN.split(text)
        for part in reversed(parts):
            candidate = validate_location(part)
            if candidate:
                return candidate

    parts = DASH_SEPARATOR_PATTERN.split(text)
    if len(parts) > 1:
        for part in reversed(parts):
            candidate = validate_location(part)
            if candidate:
                return candidate

    return validate_location(text)


# ------------------------------------------------------------------
# GENERIC CITY / STATE EXTRACTION
# ------------------------------------------------------------------

def extract_city_state(line):
    """Extract a plausible city/state pair from a line."""
    if not isinstance(line, str) or not line.strip():
        return None

    text = remove_date_text(line)
    if not text:
        return None

    text = SEPARATOR_PATTERN.split(text, maxsplit=1)[0].strip()

    comma_parts = [
        part.strip()
        for part in text.split(",")
        if part.strip()
    ]

    if len(comma_parts) > 1:
        for part in reversed(comma_parts):
            candidate = validate_location(part)
            if candidate:
                return candidate

    return validate_location(text)


# ------------------------------------------------------------------
# MAIN EXPERIENCE LOCATION EXTRACTION
# ------------------------------------------------------------------

def extract_location(experience_block):
    """
    Extract a location from an experience block.

    Priority:
        1. Explicit inline company/location heading
        2. Explicit separator patterns
        3. Known location dictionary
        4. Generic city/state patterns

    Returns:
        A location string or None.
    """
    lines = _get_lines(experience_block)

    if not lines:
        return None

    # Pass 1: process the entire block so list inputs are handled
    # consistently and inline headers are checked before other rules.
    location = extract_inline_location(lines)
    if location:
        return location

    # Pass 2: explicit separator patterns.
    for line in lines:
        location = extract_location_from_separator(line)
        if location:
            return location

    # Pass 3: dictionary-based matching.
    locations = load_locations()
    for line in lines:
        location = extract_location_from_dictionary(line, locations)
        if location:
            return location

    # Pass 4: generic city/state patterns.
    for line in lines:
        location = extract_city_state(line)
        if location:
            return location

    return None
