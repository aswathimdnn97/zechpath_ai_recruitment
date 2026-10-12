
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
    item.lower()
    for item in _load_locations_cached()
    if isinstance(item, str)
)


# ------------------------------------------------------------------
# COMPILED PATTERNS
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

CITY_STATE_PATTERN = re.compile(
    r"^[A-Za-z][A-Za-z .'-]*,\s*[A-Za-z][A-Za-z .'-]*$"
)

CITY_COUNTRY_PATTERN = CITY_STATE_PATTERN

SEPARATOR_PATTERN = re.compile(r"\s*\|\s*")

DASH_SEPARATOR_PATTERN = re.compile(r"\s+[-–—\uFFFD]\s+")

# Company-name suffixes and terms used to identify company text.
COMPANY_INDICATOR_PATTERN = re.compile(
    r"\b(?:"
    r"llp|ltd|limited|pvt|private|"
    r"inc|incorporated|corporation|corp|"
    r"technologies|solutions|industries"
    r")\b",
    re.IGNORECASE,
)


# ------------------------------------------------------------------
# TEXT CLEANING
# ------------------------------------------------------------------

LOCATION_STOP_WORDS = {
    "experience", "responsibilities", "responsibility",
    "description", "developed", "working", "worked",
    "project", "projects", "skills", "technologies",
    "technology", "using", "management", "developer",
    "engineer", "intern", "internship", "team",
    "client", "clients", "company", "organization",
    "organisation", "remote", "hybrid", "onsite", "on-site",
}


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
    """Reject description-like text as a location."""
    if not text:
        return True

    lower_text = text.lower()
    words = lower_text.split()

    if len(words) > 8:
        return True

    if any(word in LOCATION_STOP_WORDS for word in words):
        return True

    if lower_text.startswith((
        "responsible for",
        "worked on",
        "developed",
        "built ",
        "designed ",
        "managed ",
        "implemented ",
        "using ",
    )):
        return True

    return False


def clean_location_candidate(candidate):
    """Clean and validate a location candidate."""
    if not candidate:
        return ""

    candidate = remove_date_text(candidate)
    candidate = candidate.strip(" \t,;|:-–—\uFFFD")
    candidate = WHITESPACE_PATTERN.sub(" ", candidate).strip()

    if not candidate or looks_like_description(candidate):
        return ""

    return candidate


def extract_inline_location(line, locations=None):
    """
    Extract the location from an inline heading such as:
        Zecser Business LLP, Kochi | Data Science Engineer Intern ...
        Sorice Solutions Private Limited, Palarivattom | Java Developer ...
    """
    if not line:
        return None

    # Location is expected before the pipe that separates the
    # company/location portion from the job title and dates.
    left_part = SEPARATOR_PATTERN.split(line.strip(), maxsplit=1)[0]
    left_part = remove_date_text(left_part).strip(" ,|")

    if not left_part:
        return None

    # First try known dictionary entries, preferring the longest match.
    known_locations = locations if locations is not None else load_locations()
    location = extract_location_from_dictionary(left_part, known_locations)

    if location:
        return location

    # Handle "Company, City" and "Company, City, State" formats.
    # Inspect comma-separated suffixes from right to left.
    parts = [part.strip() for part in left_part.split(",") if part.strip()]

    for part in reversed(parts):
        candidate = clean_location_candidate(part)

        if not candidate:
            continue

        if candidate.lower() in LOCATION_LOOKUP:
            return candidate

        # A single city name without a company suffix can be accepted.
        if (
            len(parts) > 1
            and not contains_company_indicator(candidate)
            and re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", candidate)
        ):
            return candidate

    # Finally, accept a plain city/state pair only if it does not
    # contain a recognizable company-name term.
    if (
        CITY_STATE_PATTERN.fullmatch(left_part)
        and not contains_company_indicator(left_part)
    ):
        return left_part

    return None


# ------------------------------------------------------------------
# LOCATION EXTRACTION FROM SEPARATORS
# ------------------------------------------------------------------

def extract_location_from_separator(line):
    """Extract a location from pipe- or dash-separated text."""
    if not line:
        return None

    text = remove_date_text(str(line).strip())

    if not text:
        return None

    # Handle inline company/location headings before generic splitting.
    inline_location = extract_inline_location(line)

    if inline_location:
        return inline_location

    if "|" in text:
        parts = SEPARATOR_PATTERN.split(text)

        for part in reversed(parts):
            candidate = clean_location_candidate(part)

            if not candidate:
                continue

            if (
                CITY_STATE_PATTERN.fullmatch(candidate)
                and not contains_company_indicator(candidate)
            ):
                return candidate

            if candidate.lower() in LOCATION_LOOKUP:
                return candidate

    parts = DASH_SEPARATOR_PATTERN.split(text)

    if len(parts) > 1:
        for part in reversed(parts):
            candidate = clean_location_candidate(part)

            if not candidate:
                continue

            if (
                CITY_STATE_PATTERN.fullmatch(candidate)
                and not contains_company_indicator(candidate)
            ):
                return candidate

            if candidate.lower() in LOCATION_LOOKUP:
                return candidate

    candidate = clean_location_candidate(text)

    if (
        candidate
        and CITY_STATE_PATTERN.fullmatch(candidate)
        and not contains_company_indicator(candidate)
    ):
        return candidate

    if candidate and candidate.lower() in LOCATION_LOOKUP:
        return candidate

    return None


# ------------------------------------------------------------------
# LOCATION EXTRACTION FROM DICTIONARY
# ------------------------------------------------------------------

def extract_location_from_dictionary(line, locations):
    """Find the longest known location contained in a line."""
    if not line or not locations:
        return None

    lower_line = line.lower()
    matches = []

    for location in locations:
        if not isinstance(location, str) or not location:
            continue

        # Require word boundaries to avoid accidental substring matches.
        pattern = rf"(?<!\w){re.escape(location)}(?!\w)"

        if re.search(pattern, lower_line, re.IGNORECASE):
            matches.append(location)

    matches.sort(key=len, reverse=True)

    for location in matches:
        if not looks_like_description(location):
            return location

    return None


# ------------------------------------------------------------------
# GENERIC CITY / STATE EXTRACTION
# ------------------------------------------------------------------

def extract_city_state(line):
    """Extract a city/state candidate without returning company text."""
    if not line:
        return None

    text = remove_date_text(line)

    if not text:
        return None

    # Remove the title/date side of inline company/location headings.
    text = SEPARATOR_PATTERN.split(text, maxsplit=1)[0].strip()

    # Prefer the final comma-separated component when the preceding
    # text appears to be a company name.
    comma_parts = [part.strip() for part in text.split(",") if part.strip()]

    if len(comma_parts) > 1 and contains_company_indicator(text):
        candidate = clean_location_candidate(comma_parts[-1])

        if candidate:
            if candidate.lower() in LOCATION_LOOKUP:
                return candidate

            if re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", candidate):
                return candidate

    candidates = [
        clean_location_candidate(part)
        for part in SEPARATOR_PATTERN.split(text)
    ]

    candidates.extend(
        clean_location_candidate(part)
        for part in DASH_SEPARATOR_PATTERN.split(text)
    )

    candidates.append(clean_location_candidate(text))

    for candidate in candidates:
        if (
            candidate
            and CITY_STATE_PATTERN.fullmatch(candidate)
            and not contains_company_indicator(candidate)
        ):
            return candidate

    return None


# ------------------------------------------------------------------
# MAIN LOCATION EXTRACTION
# ------------------------------------------------------------------

def extract_location(experience_block):
    """
    Extract a location from an experience block.

    Extraction order:
        1. Inline company/location headings
        2. Explicit separator patterns
        3. Known locations from the location dictionary
        4. Generic city/state patterns
    """
    if not experience_block:
        return None

    if isinstance(experience_block, list):
        lines = []

        for item in experience_block:
            if isinstance(item, list):
                lines.extend(item)
            else:
                lines.append(item)
    else:
        lines = str(experience_block).splitlines()

    lines = [
        str(line).strip()
        for line in lines
        if line and str(line).strip()
    ]

    if not lines:
        return None

    locations = load_locations()

    # Pass 1: parse inline company/location headings.
    for line in lines:
        location = extract_inline_location(line, locations)

        if location:
            return location

    # Pass 2: explicit separator patterns.
    for line in lines:
        location = extract_location_from_separator(line)

        if location:
            return location

    # Pass 3: known locations in the dictionary.
    for line in lines:
        location = extract_location_from_dictionary(line, locations)

        if location:
            # Do not return the entire company/location heading.
            inline = extract_inline_location(line, locations)
            return inline or location

    # Pass 4: generic city/state patterns.
    for line in lines:
        location = extract_city_state(line)

        if location:
            return location

    return None
