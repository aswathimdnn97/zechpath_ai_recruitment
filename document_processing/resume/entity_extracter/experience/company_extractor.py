"""
company_extractor.py

Responsibilities
----------------
1. Extract company names from experience blocks.
2. Ignore dates.
3. Ignore responsibility/description lines.
4. Ignore technical skill lines.
5. Ignore job titles.
6. Separate company from location.
7. Support:
       Title - Company
       Company - Location
       Title - Company - Location
       Company | Location | Dates
8. Prefer explicit company suffixes.
9. Never return a responsibility sentence as a company.
"""

import json
import re
from pathlib import Path
from functools import lru_cache

# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ============================================================
# FILES
# ============================================================

SUFFIX_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "companies"
    / "company_suffix.json"
)


TITLE_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "job_titles"
    / "master_job_titles.json"
)


LOCATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "locations"
    / "location_dictionary.json"
)


# ============================================================
# JSON LOADERS
# ============================================================
@lru_cache(maxsize=1)
def load_suffixes():

    try:

        with open(
            SUFFIX_FILE,
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):

        return []

    if isinstance(
        data,
        dict
    ):

        return data.get(
            "suffixes",
            []
        )

    if isinstance(
        data,
        list
    ):

        return data

    return []

@lru_cache(maxsize=1)
def load_job_titles():

    try:

        with open(
            TITLE_FILE,
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):

        return []

    if isinstance(
        data,
        dict
    ):

        return data.get(
            "titles",
            []
        )

    if isinstance(
        data,
        list
    ):

        return data

    return []

@lru_cache(maxsize=1)
def load_locations():

    try:

        with open(
            LOCATION_FILE,
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):

        return []

    if isinstance(
        data,
        dict
    ):

        return data.get(
            "locations",
            []
        )

    if isinstance(
        data,
        list
    ):

        return data

    return []


# ============================================================
# ACTION / RESPONSIBILITY WORDS
# ============================================================

ACTION_WORDS = {

    "developed",
    "designed",
    "implemented",
    "created",
    "built",
    "worked",
    "responsible",
    "collaborated",
    "collaborate",
    "collaboration",
    "partnered",
    "improved",
    "enhanced",
    "maintained",
    "managed",
    "optimized",
    "tested",
    "using",
    "used",
    "knowledge",
    "experience",
    "added",
    "participated",
    "contributed",
    "led",
    "coordinated",
    "facilitated",
    "organized",
    "executed",
    "deployed",
    "configured",
    "supported",
    "monitored",
    "analyzed",
    "researched",
    "reviewed",
    "documented",
    "resolved",
    "performed",
    "conducted",
    "achieved",
    "established",
    "integrated",
    "wrote",
    "built",
    "handled",
    "worked",
    "assisted",
    "provided",
    "debugged",
    "fixed",
    "prepared",
    "investigated",
    "implemented",
}


# ============================================================
# TECHNICAL WORDS
# ============================================================

TECH_WORDS = {

    "python",
    "java",
    "javascript",
    "typescript",
    "html",
    "css",
    "mysql",
    "postgresql",
    "mongodb",
    "react",
    "node",
    "nodejs",
    "php",
    "api",
    "apis",
    "rest",
    "fastapi",
    "django",
    "flask",
    "git",
    "github",
    "gitlab",
    "docker",
    "aws",
    "azure",
    "redis",
    "sql",
    "pytest",
    "pydantic",
}

TECH_WORD_PATTERNS = tuple(
    re.compile(rf"\b{re.escape(word)}\b")
    for word in TECH_WORDS
)

RESPONSIBILITY_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"^\s*used\s+",
        r"^\s*worked\s+",
        r"^\s*responsible\s+for",
        r"^\s*developed\s+",
        r"^\s*designed\s+",
        r"^\s*implemented\s+",
        r"^\s*created\s+",
        r"^\s*built\s+",
        r"^\s*wrote\s+",
        r"^\s*tested\s+",
        r"^\s*managed\s+",
        r"^\s*maintained\s+",
        r"^\s*configured\s+",
        r"^\s*deployed\s+",
        r"^\s*documented\s+",
        r"^\s*investigated\s+",
        r"^\s*prepared\s+",
        r"^\s*assisted\s+",
    )
)


# ============================================================
# COMPANY-SPECIFIC WORDS
# ============================================================

COMPANY_WORDS = {
    "company",
    "corporation",
    "corporate",
    "technologies",
    "technology",
    "solutions",
    "systems",
    "software",
    "labs",
    "lab",
    "services",
    "consulting",
    "consultants",
    "group",
    "industries",
    "limited",
    "ltd",
    "llc",
    "inc",
    "incorporated",
    "enterprises",
    "digital",
    "networks",
    "ventures",
}


# ============================================================
# DATE DETECTION
# ============================================================

MONTH_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)


DATE_PATTERN = re.compile(
    rf"""
    \b
    (?:
        {MONTH_PATTERN}\s+\d{{4}}
    )
    |
    \b\d{4}\b
    |
    \bPresent\b
    |
    \bCurrent\b
    """,
    re.IGNORECASE | re.VERBOSE,
)


DATE_RANGE_PATTERN = re.compile(
    rf"""
    (?:
        {MONTH_PATTERN}\s+\d{{4}}
        |
        \d{4}
    )
    \s*
    [-–—\uFFFD]
    \s*
    (?:
        {MONTH_PATTERN}\s+\d{{4}}
        |
        \d{4}
        |
        Present
        |
        Current
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

DATE_LABEL_PATTERN = re.compile(
    r"^\s*(date|duration|period)\s*[:\-]?\s*",
    re.IGNORECASE,
)

EXPERIENCE_DATE_LINE_PATTERN = re.compile(
    rf"""
    ^
    (?:
        {MONTH_PATTERN}\s+\d{{4}}
        |
        \d{{4}}
    )
    \s*
    (?:
        [-–—\uFFFD]
        \s*
        (?:
            {MONTH_PATTERN}\s+\d{{4}}
            |
            \d{{4}}
            |
            Present
            |
            Current
        )
    )?
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)


def is_date(line):
    """
    Return True only when the entire line is essentially
    a date or date range.
    """

    if not isinstance(line, str):
        return False

    text = line.strip()

    if not text:
        return False

    # Remove common date labels
    text = DATE_LABEL_PATTERN.sub("", text)

    return bool(EXPERIENCE_DATE_LINE_PATTERN.fullmatch(text))

# ============================================================
# DATE CLEANING
# ============================================================

def strip_dates_from_company(line):
    """
    Remove dates from a company candidate.
    """

    if not isinstance(
        line,
        str
    ):
        return line

    # Full date range
    line = DATE_RANGE_PATTERN.sub(
        "",
        line
    )

    # Month + year
    line = re.sub(
        rf"\b{MONTH_PATTERN}\s+\d{{4}}\b",
        "",
        line,
        flags=re.IGNORECASE
    )

    # Year range
    line = re.sub(
        r"\b\d{4}\s*[-–—\uFFFD]\s*(?:\d{4}|present|current)\b",
        "",
        line,
        flags=re.IGNORECASE
    )

    # Standalone year
    line = re.sub(
        r"\b(?:19|20)\d{2}\b",
        "",
        line
    )

    line = re.sub(
        r"\s+",
        " ",
        line
    )

    return line.strip(
        " ,|:-–—"
    )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_company(text):

    if not text:
        return None

    text = strip_dates_from_company(
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = text.strip(
        " ,|:-–—"
    )

    if not text:
        return None

    return text


# ============================================================
# TITLE DETECTION
# ============================================================
@lru_cache(maxsize=1)
def build_title_sets():

    titles = set()

    raw_titles = load_job_titles()

    for item in raw_titles:

        if isinstance(
            item,
            dict
        ):

            name = item.get(
                "name"
            )

        elif isinstance(
            item,
            str
        ):

            name = item

        else:

            name = None

        if name:

            titles.add(
                name.strip().lower()
            )

    return titles


TITLE_ROLE_WORDS = {

    "developer",
    "engineer",
    "programmer",
    "analyst",
    "manager",
    "consultant",
    "architect",
    "specialist",
    "scientist",
    "designer",
    "administrator",
    "intern",
    "trainee",
    "lead",
    "senior",
    "junior",
    "associate",
    "director",
    "officer",
    "executive",
    "assistant",
    "developer",
    "tester",
}


def looks_like_title(text, titles=None):

    if not text:
        return False

    lower = text.lower().strip()

    if titles and lower in titles:
        return True

    words = set(
        lower.split()
    )

    return bool(
        words.intersection(
            TITLE_ROLE_WORDS
        )
    )


# ============================================================
# LOCATION DETECTION
# ============================================================

def looks_like_location(text, locations=None):

    if not text:
        return False

    text = text.strip()

    if not text:
        return False

    lower = text.lower()

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if locations:

        for location in locations:

            if not isinstance(
                location,
                str
            ):
                continue

            if lower == location.lower().strip():

                return True

    # --------------------------------------------------------
    # City, State
    #
    # Kochi, Kerala
    # Calicut, Kerala
    # Bangalore, Karnataka
    # --------------------------------------------------------

    if re.fullmatch(
        r"[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*)*"
        r"\s*,\s*"
        r"[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*)*",
        text
    ):

        return True

    return False


# ============================================================
# RESPONSIBILITY DETECTION
# ============================================================

def is_responsibility_line(
    line
):

    if not line:
        return False

    lower = line.lower().strip()

    words = lower.split()

    if not words:
        return False

    # --------------------------------------------------------
    # Strong first-word signal
    # --------------------------------------------------------

    if words[0] in ACTION_WORDS:
        return True

    # --------------------------------------------------------
    # Sentence-style description
    # --------------------------------------------------------

    if len(words) >= 7:

        action_count = sum(
            word.strip(
                ".,:;()"
            )
            in ACTION_WORDS
            for word in words
        )

        if action_count >= 1:
            return True

    # --------------------------------------------------------
    # Common responsibility phrases
    # --------------------------------------------------------

    return any(
        pattern.search(lower)
        for pattern in RESPONSIBILITY_PATTERNS
    )


# ============================================================
# TECHNICAL LINE DETECTION
# ============================================================

def is_technical_line(line):

    if not line:
        return False

    lower = line.lower()

    tech_count = sum(
        bool(pattern.search(lower))
        for pattern in TECH_WORD_PATTERNS
    )

    return tech_count >= 2


# ============================================================
# TITLE - COMPANY
# ============================================================

def extract_company_from_title_company(
    line,
    titles=None,
    locations=None
):
    """
    Extract company from:

        Python Developer - CodeNest Technologies

    But NOT:

        CodeNest Technologies - Kochi, Kerala
    """

    if not isinstance(
        line,
        str
    ):
        return None

    if "|" in line:
        return None

    separators = [
        " - ",
        " – ",
        " — ",
    ]

    for separator in separators:

        if separator not in line:
            continue

        parts = [
            part.strip()
            for part in line.split(
                separator
            )
            if part.strip()
        ]

        if len(parts) < 2:
            continue

        # ----------------------------------------------------
        # Find a title segment.
        # ----------------------------------------------------

        for index, part in enumerate(
            parts[:-1]
        ):

            if not looks_like_title(
                part,
                titles
            ):
                continue

            # The next segment is the company.
            company = parts[index + 1]

            # If next part is location, don't use it.
            if looks_like_location(
                company,
                locations
            ):
                continue

            company = normalize_company(
                company
            )

            if company:
                return company

    return None


# ============================================================
# COMPANY - LOCATION
# ============================================================

def extract_company_from_company_location(
    line,
    titles=None,
    locations=None
):
    """
    Extract company from:

        CodeNest Technologies - Kochi, Kerala

        Python Developer - CodeNest Technologies - Kochi, Kerala

    Returns:
        CodeNest Technologies
    """

    if not isinstance(line, str):
        return None

    line = strip_dates_from_company(line)

    comma_location = split_company_location_by_comma(line)
    if comma_location:
        return comma_location[0]

    separators = [
        " - ",
        " – ",
        " — ",
    ]

    for separator in separators:

        if separator not in line:
            continue

        parts = [
            part.strip()
            for part in line.split(separator)
            if part.strip()
        ]

        if len(parts) < 2:
            continue

        # ----------------------------------------------------
        # Last part must be a location
        # ----------------------------------------------------

        if not looks_like_location(
            parts[-1],
            locations
        ):
            continue

        # Remove location
        content_parts = parts[:-1]

        if not content_parts:
            continue

        # ----------------------------------------------------
        # Title - Company - Location
        # ----------------------------------------------------

        for part in content_parts:

            if looks_like_title(
                part,
                titles
            ):
                continue

            if is_responsibility_line(part):
                continue

            if is_technical_line(part):
                continue

            candidate = normalize_company(part)

            if candidate:
                return candidate

        # ----------------------------------------------------
        # Company - Location
        # ----------------------------------------------------

        candidate = normalize_company(
            content_parts[-1]
        )

        if not candidate:
            continue

        if looks_like_title(
            candidate,
            titles
        ):
            continue

        if is_responsibility_line(candidate):
            continue

        if is_technical_line(candidate):
            continue

        return candidate

    return None

# ============================================================
# PIPE FORMAT
# ============================================================

def extract_company_from_pipe(
    line,
    titles=None,
    locations=None
):
    """
    Support:

        Python Developer | CodeNest Technologies | Kochi, Kerala | Jan 2024 - Jun 2024

        CodeNest Technologies | Kochi, Kerala | Jan 2024 - Jun 2024
    """

    if "|" not in line:
        return None

    parts = [
        part.strip()
        for part in line.split("|")
        if part.strip()
    ]

    if not parts:
        return None

    # Remove date segments.
    parts = [
        part
        for part in parts
        if not is_date(part)
    ]

    if not parts:
        return None

    for part in parts:

        company = extract_company_from_company_location(
            part,
            titles,
            locations
        )

        if company:
            return company

        comma_location = split_company_location_by_comma(part)
        if comma_location:
            return comma_location[0]

    # --------------------------------------------------------
    # Search for explicit location.
    # --------------------------------------------------------

    location_index = None

    for index, part in enumerate(
        parts
    ):

        if looks_like_location(
            part,
            locations
        ):
            location_index = index
            break

    # --------------------------------------------------------
    # If first part is title and second is company.
    # --------------------------------------------------------

    if len(parts) >= 2:

        if looks_like_title(
            parts[0],
            titles
        ):

            candidate = parts[1]

            if not looks_like_location(
                candidate,
                locations
            ):

                return normalize_company(
                    candidate
                )

    # --------------------------------------------------------
    # Otherwise first non-location part.
    # --------------------------------------------------------

    for part in parts:

        if looks_like_location(
            part,
            locations
        ):
            continue

        if looks_like_title(
            part,
            titles
        ):
            continue

        if is_responsibility_line(
            part
        ):
            continue

        candidate = normalize_company(
            part
        )

        if candidate:
            return candidate

    return None


# ============================================================
# COMPANY SUFFIX CHECK
# ============================================================

def has_company_suffix(
    text,
    suffixes
):

    if not text:
        return False

    lower = text.lower()

    return any(
        str(suffix).strip().lower()
        in lower
        for suffix in suffixes
        if isinstance(
            suffix,
            str
        )
    )


def split_company_location_by_comma(line, suffixes=None):
    if not isinstance(line, str) or "," not in line:
        return None

    if re.search(r"\s+[-–—]\s+", line):
        return None

    company, location = line.rsplit(",", 1)
    company = company.strip()
    location = location.strip()
    suffixes = suffixes or load_suffixes()

    if (
        not has_company_suffix(company, suffixes)
        or has_company_suffix(location, suffixes)
    ):
        return None

    if not re.fullmatch(
        r"[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,3}",
        location,
    ):
        return None

    return company, location


# ============================================================
# PROPER NOUN CHECK
# ============================================================

def looks_like_company_proper_noun(
    text
):

    if not text:
        return False

    words = text.split()

    if not (
        2 <= len(words) <= 8
    ):
        return False

    capitalized = sum(
        1
        for word in words
        if word
        and word[0].isupper()
    )

    return capitalized >= 2


# ============================================================
# MAIN EXTRACTION
# ============================================================

def extract_companies(
    experience_section
):

    if not experience_section:
        return []

    # --------------------------------------------------------
    # Flatten nested input.
    # --------------------------------------------------------

    if (
        isinstance(
            experience_section,
            list
        )
        and experience_section
        and isinstance(
            experience_section[0],
            list
        )
    ):

        flattened = []

        for block in experience_section:

            if isinstance(
                block,
                list
            ):

                flattened.extend(
                    block
                )

        experience_section = flattened

    if not isinstance(
        experience_section,
        list
    ):
        return []

    suffixes = load_suffixes()

    locations = load_locations()

    titles = build_title_sets()

    companies = []
    structured_lines = set()

    # ========================================================
    # FIRST PASS
    #
    # Strong structured patterns.
    # ========================================================

    for raw_line in experience_section:

        if not isinstance(
            raw_line,
            str
        ):
            continue

        line = raw_line.strip()

        if not line:
            continue

        # ----------------------------------------------------
        # Ignore pure date lines.
        # ----------------------------------------------------

        if is_date(line):
            continue

        comma_companies = [
            part.strip()
            for part in line.split(",")
            if part.strip()
        ]
        if (
            len(comma_companies) > 1
            and all(
                has_company_suffix(part, suffixes)
                for part in comma_companies
            )
        ):
            companies.extend(comma_companies)
            structured_lines.add(line.casefold())
            continue

        # ----------------------------------------------------
        # Title - Company
        # ----------------------------------------------------

        company = extract_company_from_title_company(
            line,
            titles,
            locations
        )

        if company:

            companies.append(
                company
            )
            structured_lines.add(
                line.casefold()
            )

            continue

        # ----------------------------------------------------
        # Company - Location
        # ----------------------------------------------------

        company = extract_company_from_company_location(
            line,
            titles,
            locations
        )
        if company:

            companies.append(
                company
            )
            structured_lines.add(
                line.casefold()
            )

            continue

        # ----------------------------------------------------
        # Pipe-separated structure
        # ----------------------------------------------------

        company = extract_company_from_pipe(
            line,
            titles,
            locations
        )

        if company:

            companies.append(
                company
            )
            structured_lines.add(
                line.casefold()
            )

            continue

    # ========================================================
    # SECOND PASS
    #
    # Explicit company suffixes.
    # ========================================================

    for raw_line in experience_section:

        if not isinstance(
            raw_line,
            str
        ):
            continue

        line = raw_line.strip()

        if not line:
            continue

        if line.casefold() in structured_lines:
            continue

        if is_date(line):
            continue

        if is_responsibility_line(
            line
        ):
            continue

        if is_technical_line(
            line
        ):
            continue

        # Don't accept a pure location.
        if looks_like_location(
            line,
            locations
        ):
            continue

        # Don't accept a pure title.
        if looks_like_title(
            line,
            titles
        ):
            continue

        candidate = normalize_company(
            line
        )

        if not candidate:
            continue

        if has_company_suffix(
            candidate,
            suffixes
        ):

            companies.append(
                candidate
            )

    # ========================================================
    # THIRD PASS
    #
    # Proper-noun company heuristic.
    # ========================================================

    for raw_line in experience_section:

        if not isinstance(
            raw_line,
            str
        ):
            continue

        line = raw_line.strip()

        if not line:
            continue

        if line.casefold() in structured_lines:
            continue

        if is_date(line):
            continue

        if is_responsibility_line(
            line
        ):
            continue

        if is_technical_line(
            line
        ):
            continue

        if looks_like_location(
            line,
            locations
        ):
            continue

        if looks_like_title(
            line,
            titles
        ):
            continue

        candidate = normalize_company(
            line
        )

        if not candidate:
            continue

        if looks_like_company_proper_noun(
            candidate
        ):

            companies.append(
                candidate
            )

    # ========================================================
    # FOURTH PASS
    #
    # Resume templates often place a company on the line
    # immediately after a title without using a company suffix:
    #
    #     Senior HR Executive
    #     PeopleSphere
    #
    # Accept that adjacent line only when it is not itself a
    # title, date, location, responsibility, or technical line.
    # ========================================================

    for index, raw_line in enumerate(experience_section[:-1]):

        if not isinstance(raw_line, str):
            continue

        title_line = raw_line.strip()

        if not title_line or is_date(title_line):
            continue

        if not looks_like_title(title_line, titles):
            continue

        raw_company_line = experience_section[index + 1]

        if not isinstance(raw_company_line, str):
            continue

        company_line = raw_company_line.strip()

        if not company_line or is_date(company_line):
            continue

        if (
            looks_like_title(company_line, titles)
            or looks_like_location(company_line, locations)
            or is_responsibility_line(company_line)
            or is_technical_line(company_line)
        ):
            continue

        candidate = normalize_company(company_line)

        if candidate:
            companies.append(candidate)

    # ========================================================
    # CLEAN / DEDUPLICATE
    # ========================================================

    result = []

    seen = set()

    for company in companies:

        company = normalize_company(
            company
        )

        if not company:
            continue

        key = company.lower()

        if key in seen:
            continue

        seen.add(key)

        result.append(
            company
        )

    return result


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def extract_company(experience_block):
    """
    Extract the best single company from one experience block.

    Supported formats:

        Python Developer - CodeNest Technologies
        CodeNest Technologies - Kochi, Kerala
        Python Developer - CodeNest Technologies - Kochi, Kerala
        Python Developer | CodeNest Technologies | Kochi, Kerala | Jan 2024 - Jun 2024
        CodeNest Technologies | Kochi, Kerala | Jan 2024 - Jun 2024

    Returns:
        Clean company name only.
    """

    if not experience_block:
        return None

    if isinstance(experience_block, str):
        experience_block = [experience_block]

    if not isinstance(experience_block, list):
        return None

    suffixes = load_suffixes()
    locations = load_locations()
    titles = build_title_sets()

    # ========================================================
    # PASS 1
    # Strong structured patterns
    # ========================================================

    for raw_line in experience_block:

        if not isinstance(raw_line, str):
            continue

        line = raw_line.strip()

        if not line:
            continue

        # Never process pure date lines
        if is_date(line):
            continue

        # ----------------------------------------------------
        # Company - Location
        # ----------------------------------------------------

        company = extract_company_from_company_location(
            line,
            titles,
            locations
        )

        if company:
            return company

        # ----------------------------------------------------
        # Title - Company
        # ----------------------------------------------------

        company = extract_company_from_title_company(
            line,
            titles,
            locations
        )

        if company:
            return company

        # ----------------------------------------------------
        # Pipe format
        # ----------------------------------------------------

        company = extract_company_from_pipe(
            line,
            titles,
            locations
        )

        if company:
            return company

    # ========================================================
    # PASS 2
    # Explicit company suffix
    # ========================================================

    for raw_line in experience_block:

        if not isinstance(raw_line, str):
            continue

        line = raw_line.strip()

        if not line:
            continue

        if is_date(line):
            continue

        if is_responsibility_line(line):
            continue

        if is_technical_line(line):
            continue

        if looks_like_location(
            line,
            locations
        ):
            continue

        if looks_like_title(
            line,
            titles
        ):
            continue

        candidate = normalize_company(line)

        if not candidate:
            continue

        if has_company_suffix(
            candidate,
            suffixes
        ):
            return candidate

    # ========================================================
    # PASS 3
    # Conservative proper-noun heuristic
    # ========================================================

    for raw_line in experience_block:

        if not isinstance(raw_line, str):
            continue

        line = raw_line.strip()

        if not line:
            continue

        if is_date(line):
            continue

        if is_responsibility_line(line):
            continue

        if is_technical_line(line):
            continue

        if looks_like_location(
            line,
            locations
        ):
            continue

        if looks_like_title(
            line,
            titles
        ):
            continue

        candidate = normalize_company(line)

        if not candidate:
            continue

        if looks_like_company_proper_noun(candidate):
            return candidate

    return None
# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    test_block = [

        "Python Developer",

        "CodeNest Technologies - Kochi, Kerala",

        "Jan 2024 - Jun 2024",

        "Developed FastAPI endpoints for candidate, "
        "job-description and application workflows.",

        "Designed PostgreSQL tables and SQL queries "
        "for candidate profiles and scoring results.",

        "Built Pydantic request and response schemas "
        "with validation for REST API payloads.",

        "Wrote pytest cases for authentication, "
        "validation, CRUD operations and error handling.",

        "Used Git and pull requests for source control, "
        "code review and release preparation.",
    ]

    print(
        "Companies:",
        extract_companies(
            test_block
        )
    )

    print(
        "Best company:",
        extract_company(
            test_block
        )
    )
    
    if __name__ == "__main__":

     test_block = [
        "Python Developer",
        "CodeNest Technologies - Kochi, Kerala",
        "Jan 2024 - Jun 2024",
        "Developed FastAPI endpoints for candidate, "
        "job-description and application workflows.",
        "Designed PostgreSQL tables and SQL queries "
        "for candidate profiles and scoring results.",
        "Built Pydantic request and response schemas "
        "with validation for REST API payloads.",
        "Wrote pytest cases for authentication, "
        "validation, CRUD operations and error handling.",
        "Used Git and pull requests for source control, "
        "code review and release preparation.",
    ]

    print(
        "EXTRACTED COMPANY:",
        repr(extract_company(test_block))
    )
    
    result = extract_company_from_company_location(
    "CodeNest Technologies - Kochi, Kerala",
    build_title_sets(),
    load_locations()
)

    print("COMPANY + LOCATION:", repr(result))