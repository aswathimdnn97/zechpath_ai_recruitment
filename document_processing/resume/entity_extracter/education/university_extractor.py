"""
university_extractor.py

Responsibilities
----------------
1. Detect universities using the external dictionary.
2. Support university aliases.
3. Detect unknown universities using generic patterns.
4. Preserve the original university text from the resume.
5. Return canonical university name when available.
6. Never require every university to exist in the dictionary.
7. Remove only the detected university from a line.

Architecture
------------
Dictionary
    ↓
Known university / alias
    ↓
Canonical name

If dictionary lookup fails:
    ↓
Generic university pattern detection
    ↓
Unknown university
    ↓
canonical_name = None
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[5]

UNIVERSITY_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "universities"
    / "university_dictionary.json"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_university_text(text: str) -> str:
    """
    Normalize text for dictionary lookup.

    This does NOT change the original value returned
    to the caller.
    """

    if not text:
        return ""

    text = text.replace("\xa0", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip().lower()


# ============================================================
# LOAD UNIVERSITY DICTIONARY
# ============================================================

def _load_university_dictionary():

    if not UNIVERSITY_FILE.exists():

        print(
            f"[WARNING] University dictionary not found: "
            f"{UNIVERSITY_FILE}"
        )

        return []

    try:

        with open(
            UNIVERSITY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ) as exc:

        print(
            f"[WARNING] Failed to load university dictionary: "
            f"{exc}"
        )

        return []

    # --------------------------------------------------------
    # Expected format
    #
    # {
    #     "universities": [...]
    # }
    # --------------------------------------------------------

    if isinstance(data, dict):

        universities = data.get(
            "universities",
            []
        )

    elif isinstance(data, list):

        universities = data

    else:

        universities = []

    return universities


UNIVERSITIES = _load_university_dictionary()


# ============================================================
# BUILD ALIAS LOOKUP
# ============================================================

def _build_alias_lookup():

    lookup = {}

    for university in UNIVERSITIES:

        if not isinstance(
            university,
            dict
        ):
            continue

        canonical_name = university.get(
            "canonical_name"
        )

        if not canonical_name:
            continue

        aliases = university.get(
            "aliases",
            []
        )

        # ----------------------------------------------------
        # Also allow canonical name itself.
        # ----------------------------------------------------

        aliases = list(aliases)

        aliases.append(
            canonical_name
        )

        for alias in aliases:

            if not isinstance(
                alias,
                str
            ):
                continue

            normalized_alias = normalize_university_text(
                alias
            )

            if not normalized_alias:
                continue

            lookup[
                normalized_alias
            ] = canonical_name

    return lookup


ALIAS_LOOKUP = _build_alias_lookup()


# ============================================================
# BUILD DICTIONARY REGEX
# ============================================================

def _build_dictionary_pattern():

    aliases = list(
        ALIAS_LOOKUP.keys()
    )

    if not aliases:
        return None

    # --------------------------------------------------------
    # Longest aliases first.
    #
    # Example:
    #
    # "Anna University"
    # before
    # "Anna"
    # --------------------------------------------------------

    aliases.sort(
        key=len,
        reverse=True
    )

    escaped_aliases = []

    for alias in aliases:

        escaped_aliases.append(
            re.escape(alias)
        )

    pattern = (
        r"(?<!\w)"
        r"(?:"
        + "|".join(
            escaped_aliases
        )
        + r")"
        r"(?!\w)"
    )

    return re.compile(
        pattern,
        flags=re.IGNORECASE
    )


DICTIONARY_PATTERN = (
    _build_dictionary_pattern()
)


# ============================================================
# GENERIC UNIVERSITY PATTERNS
# ============================================================

"""
These patterns are NOT a university dictionary.

They simply recognize linguistic structures such as:

    Anna University
    XYZ University
    University of Kerala
    Some Technological University

This provides fallback coverage for universities that are
not present in university_dictionary.json.
"""

GENERIC_UNIVERSITY_PATTERNS = [

    # --------------------------------------------------------
    # University of <Name>
    #
    # University of Kerala
    # University of Delhi
    # --------------------------------------------------------

    re.compile(
        r"\bUniversity\s+of\s+"
        r"[A-Za-z][A-Za-z0-9&.'()-]*"
        r"(?:\s+[A-Za-z][A-Za-z0-9&.'()-]*){0,6}",
        flags=re.IGNORECASE
    ),

    # --------------------------------------------------------
    # <Name> University
    #
    # Anna University
    # XYZ University
    # Some Technological University
    # --------------------------------------------------------

    re.compile(
        r"\b"
        r"[A-Za-z][A-Za-z0-9&.'()-]*"
        r"(?:\s+[A-Za-z][A-Za-z0-9&.'()-]*){0,7}"
        r"\s+University\b",
        flags=re.IGNORECASE
    ),

]


# ============================================================
# DICTIONARY MATCH
# ============================================================

def _extract_from_dictionary(
    text: str
) -> Optional[Dict[str, Any]]:

    if not text:
        return None

    if DICTIONARY_PATTERN is None:
        return None

    match = DICTIONARY_PATTERN.search(
        text
    )

    if not match:
        return None

    value = match.group(0).strip()

    normalized = normalize_university_text(
        value
    )

    canonical_name = ALIAS_LOOKUP.get(
        normalized
    )

    return {

        "value": value,

        "canonical_name":
            canonical_name,

        "source": "dictionary",

        "start": match.start(),

        "end": match.end(),

    }


# ============================================================
# GENERIC UNIVERSITY MATCH
# ============================================================

def _extract_from_generic_pattern(
    text: str
) -> Optional[Dict[str, Any]]:

    if not text:
        return None

    for pattern in GENERIC_UNIVERSITY_PATTERNS:

        match = pattern.search(
            text
        )

        if not match:
            continue

        value = match.group(0).strip()

        if not value:
            continue

        return {

            "value": value,

            "canonical_name": None,

            "source": "pattern",

            "start": match.start(),

            "end": match.end(),

        }

    return None


# ============================================================
# MAIN UNIVERSITY EXTRACTOR
# ============================================================

def extract_university(
    text: str
) -> Optional[Dict[str, Any]]:
    """
    Extract a university from one text line.

    Strategy
    --------
    1. Dictionary matching.
    2. Generic university-pattern fallback.

    Unknown universities are still returned.

    Example
    -------
    Input:
        "Anna University"

    Output:
        {
            "value": "Anna University",
            "canonical_name": "Anna University",
            "source": "dictionary",
            ...
        }

    Unknown:
        "ABC University"

    Output:
        {
            "value": "ABC University",
            "canonical_name": None,
            "source": "pattern",
            ...
        }
    """

    if not isinstance(
        text,
        str
    ):
        return None

    text = text.strip()

    if not text:
        return None

    # --------------------------------------------------------
    # FIRST: dictionary
    # --------------------------------------------------------

    result = _extract_from_dictionary(
        text
    )

    if result:
        return result

    # --------------------------------------------------------
    # SECOND: generic fallback
    # --------------------------------------------------------

    result = _extract_from_generic_pattern(
        text
    )

    if result:
        return result

    return None


# ============================================================
# REMOVE UNIVERSITY CONTENT
# ============================================================

def remove_university_content(
    text: str,
    university_result: Optional[Dict[str, Any]]
) -> str:
    """
    Remove the detected university from a line.

    Example
    -------
    "VTU - B.Tech"

    becomes:

    "- B.Tech"
    """

    if not text:
        return ""

    if not university_result:
        return text

    start = university_result.get(
        "start"
    )

    end = university_result.get(
        "end"
    )

    if start is None or end is None:
        return text

    cleaned = (
        text[:start]
        + " "
        + text[end:]
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned
    )

    return cleaned.strip()