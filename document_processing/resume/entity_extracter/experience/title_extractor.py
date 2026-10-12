"""
title_extractor.py

Responsibilities
----------------
1. Extract raw job titles from one experience block
2. Remove dates
3. Ignore company names
4. Ignore description lines
5. Return candidate job titles

No validation is performed here.
"""

import json
import re
from pathlib import Path
from functools import lru_cache

# ----------------------------------------------------
# Project Root
# ----------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

# ----------------------------------------------------
# Company Dictionary
# ----------------------------------------------------

COMPANY_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "companies"
    / "company_dictionary.json"
)

# ----------------------------------------------------
# Load Companies
# ----------------------------------------------------

@lru_cache(maxsize=1)
def load_companies():
    """Load the company dictionary once per process."""
    with open(COMPANY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

# ----------------------------------------------------
# Remove Date
# ----------------------------------------------------

import re

MONTH_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
    r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)"
)

DATE_TOKEN = rf"(?:{MONTH_PATTERN}\.?\s+)?(?:19|20)\d{{2}}"

DATE_RANGE_PATTERN = re.compile(
    rf"""
    \b
    (?:
        {MONTH_PATTERN}\.?\s+(?:19|20)\d{{2}}
        |
        (?:19|20)\d{{2}}
    )
    \s*
    (?:-|–|—|to)\s*
    (?:
        {MONTH_PATTERN}\.?\s+(?:19|20)\d{{2}}
        |
        (?:19|20)\d{{2}}
        |
        present|current|now
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

SINGLE_DATE_PATTERN = re.compile(
    rf"\b{DATE_TOKEN}\b",
    re.IGNORECASE,
)


def remove_date(text: str) -> str:
    """Remove a date or date range and the text following it."""
    if not text:
        return ""

    match = DATE_RANGE_PATTERN.search(text)

    if match:
        return text[:match.start()].strip(" \t-–—|,;:")

    match = SINGLE_DATE_PATTERN.search(text)

    if match:
        return text[:match.start()].strip(" \t-–—|,;:")

    return text.strip()

# ----------------------------------------------------
# Description Detection
# ----------------------------------------------------

# Strong signals that a line describes work rather than a job title.
DESCRIPTION_START_PATTERN = re.compile(
    r"""
    ^\s*(?:[-•*]\s*)?
    (?:
        developed|prepared|worked|was\s+responsible|
        implemented|created|designed|maintained|
        improved|enhanced|built|collaborated|
        partnered|communicated|assessed|troubleshot|
        contributed|explored|presented|wrote|
        documented|tested|delivered|performed|
        completed|handled|supported|executed|
        updated|coordinated|assisted|utilized|
        responsible\s+for|experience\s+in
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

DESCRIPTION_VERB_PATTERN = re.compile(
    r"\b(?:developed|implemented|maintained|improved|"
    r"tested|documented|delivered|troubleshot|"
    r"collaborated|contributed|executed|supported)\b",
    re.IGNORECASE,
)

TITLE_TOKENS = {
    "developer",
    "engineer",
    "programmer",
    "analyst",
    "manager",
    "consultant",
    "architect",
    "specialist",
    "scientist",
    "intern",
    "trainee",
    "lead",
    "executive",
    "assistant",
    "designer",
    "tester",
    "test",
    "owner",
    "administrator",
    "admin",
    "officer",
    "coordinator",
    "technician",
    "accountant",
    "recruiter",
    "director",
    "president",
    "founder",
    "researcher",
    "instructor",
    "teacher",
    "support",
    "associate",
    "principal",
    "supervisor",
    "architect",
    "product",
    "qa",
    "devops",
    "freelancer",
}


def is_description(text: str) -> bool:
    """Return True when a line has strong description-like signals."""
    if not isinstance(text, str):
        return False

    text = text.strip()

    if not text:
        return False

    # Clear action-oriented description at the start of a line.
    if DESCRIPTION_START_PATTERN.search(text):
        return True

    words = text.split()

    # Long, sentence-like lines are unlikely to be job titles.
    if len(words) >= 8 and text.endswith((".", ";")):
        return True

    # Avoid rejecting a short title just because it contains a verb.
    # Look for several words plus a work-description verb.
    if len(words) >= 7 and DESCRIPTION_VERB_PATTERN.search(text):
        return True

    return False


def looks_like_title_text(text: str) -> bool:
    """Check whether text contains a recognized role-related token."""
    if not isinstance(text, str):
        return False

    words = {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9+#.]+", text)
    }

    return bool(words & TITLE_TOKENS)



def split_title_company(line: str):
    """Extract a likely title from a title-company line."""
    if not isinstance(line, str):
        return ""

    text = line.strip()

    if not text:
        return ""

    # Split only once so separators inside the company name are less likely
    # to create multiple fragments.
    match = re.search(r"\s*(\||–|—|-)\s*", text)

    if not match:
        return text

    left = text[:match.start()].strip()
    right = text[match.end():].strip()

    if not left or not right:
        return text

    left_is_title = looks_like_title_text(left)
    right_is_title = looks_like_title_text(right)

    if left_is_title and not right_is_title:
        return left

    if right_is_title and not left_is_title:
        return right

    # Ambiguous lines are left unchanged for downstream checks.
    return text


def looks_like_location(text):
    """Recognize simple city/state strings like 'Kochi, Kerala'."""

    if not isinstance(text, str):
        return False

    candidate = text.strip()
    if not candidate:
        return False

    return bool(re.fullmatch(r"[A-Z][a-zA-Z]+\s*,\s*[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*", candidate))


def looks_like_company(text):
    """Heuristic for company names that should not become title candidates."""

    lower = text.lower()

    company_keywords = [
        "pvt",
        "private",
        "limited",
        "ltd",
        "inc",
        "corp",
        "soft",
        "solutions",
        "technology",
        "technologies",
        "systems",
        "services",
        "labs",
        "group",
        "industries",
        "consulting",
        "network",
    ]

    if not any(keyword in lower for keyword in company_keywords):
        return False

    title_keywords = [
        "engineer",
        "developer",
        "manager",
        "analyst",
        "consultant",
        "architect",
        "specialist",
        "scientist",
        "intern",
        "trainee",
        "lead",
        "executive",
        "designer",
    ]

    return not any(keyword in lower for keyword in title_keywords)


# ----------------------------------------------------
# Extract Titles
# ----------------------------------------------------

def extract_titles(experience_block):
    """
    Parameters
    ----------
    experience_block : list[str]

    Returns
    -------
    list[str]
    """

    if not experience_block:
        return []

    # Flatten one level if needed
    if (
        isinstance(experience_block, list)
        and experience_block
        and isinstance(experience_block[0], list)
    ):
        experience_block = experience_block[0]

    company_lookup = {

        company["name"].lower()

        for company in load_companies()

    }

    titles = []

    seen = set()

    for line in experience_block:
        if not isinstance(line, str):
            continue

        line = line.strip()

        if not line:
            continue

        # Remove dates before title/company classification.
        line = remove_date(line)

        if not line:
            continue

        # Separate likely title-company combinations.
        line = split_title_company(line)

        if not line:
            continue

        # Ignore work-description lines.
        if is_description(line):
            continue

        # Ignore company-like lines.
        if looks_like_company(line):
            continue

        # Ignore location-only lines.
        if looks_like_location(line):
            continue

        lower = line.casefold()

        # Ignore exact company dictionary matches.
        if lower in company_lookup:
            continue

        # Ignore likely location/address lines.
        if "," in line and len(line.split()) > 2:
            continue

        if lower not in seen:
            seen.add(lower)
            titles.append(line)

    return titles

test_cases = [
    ["Python Developer", "CodeNest Technologies - Kochi, Kerala",
     "Jan 2024 - Jun 2024"],
    ["QA Tester - Acme Labs", "Tested APIs and documented defects."],
    ["Product Owner | Example Systems", "Jan 2022 - Present"],
    ["Developed APIs for internal applications."],
    ["Software Engineer Jan 2022 - Present"],
    ["ABC Technologies - Kochi, Kerala"],
]

for index, block in enumerate(test_cases, start=1):
    print(f"\nTest {index}")
    print("Input:", block)
    print("Extracted titles:", extract_titles(block))