"""
university_extractor.py

Responsibilities
----------------
1. Detect universities using the external dictionary.
2. Support university aliases.
3. Detect unknown universities using generic patterns.
4. Preserve the original university text.
5. Return canonical university name when available.
6. Never require every university to exist in the dictionary.
7. Remove only the detected university from a line.
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

UNIVERSITY_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "education"
    / "university_dictionary.json"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_university_text(text: str) -> str:
    """
    Normalize text for dictionary lookup.

    The original text is never modified by this function.
    """

    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

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
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except (
        json.JSONDecodeError,
        OSError,
    ) as exc:

        print(
            f"[WARNING] Failed to load university dictionary: "
            f"{exc}"
        )

        return []

    if isinstance(data, dict):

        universities = data.get(
            "universities",
            [],
        )

    elif isinstance(data, list):

        universities = data

    else:

        universities = []

    return universities


UNIVERSITIES = _load_university_dictionary()


# ============================================================
# ALIAS LOOKUP
# ============================================================

def _build_alias_lookup():

    lookup = {}

    for university in UNIVERSITIES:

        if not isinstance(university, dict):
            continue

        canonical_name = university.get(
            "canonical_name"
        )

        if not canonical_name:
            continue

        aliases = university.get(
            "aliases",
            [],
        )

        if not isinstance(aliases, list):
            aliases = [aliases]

        aliases = list(aliases)

        # Canonical name is also a valid alias.
        aliases.append(canonical_name)

        for alias in aliases:

            if not isinstance(alias, str):
                continue

            normalized_alias = (
                normalize_university_text(alias)
            )

            if not normalized_alias:
                continue

            lookup[
                normalized_alias
            ] = canonical_name

    return lookup


ALIAS_LOOKUP = _build_alias_lookup()


# ============================================================
# DICTIONARY REGEX
# ============================================================

def _build_dictionary_pattern():

    aliases = list(
        ALIAS_LOOKUP.keys()
    )

    if not aliases:
        return None

    # Longest aliases first.
    aliases.sort(
        key=len,
        reverse=True,
    )

    escaped_aliases = [
        re.escape(alias)
        for alias in aliases
    ]

    pattern = (
        r"(?<!\w)"
        r"(?:"
        + "|".join(escaped_aliases)
        + r")"
        r"(?!\w)"
    )

    return re.compile(
        pattern,
        flags=re.IGNORECASE,
    )


DICTIONARY_PATTERN = (
    _build_dictionary_pattern()
)


# ============================================================
# GENERIC UNIVERSITY PATTERNS
# ============================================================

GENERIC_UNIVERSITY_PATTERNS = [

    # University of Kerala
    # University of Delhi
    re.compile(
        r"\bUniversity\s+of\s+"
        r"[A-Za-z][A-Za-z0-9&.'()-]*"
        r"(?:\s+[A-Za-z][A-Za-z0-9&.'()-]*){0,6}",
        flags=re.IGNORECASE,
    ),

    # Anna University
    # XYZ University
    # Some Technological University
    re.compile(
        r"\b"
        r"[A-Za-z][A-Za-z0-9&.'()-]*"
        r"(?:\s+[A-Za-z][A-Za-z0-9&.'()-]*){0,7}"
        r"\s+University\b",
        flags=re.IGNORECASE,
    ),
]


# ============================================================
# DICTIONARY MATCH
# ============================================================

def _extract_from_dictionary(
    text: str,
) -> Optional[Dict[str, Any]]:

    if not text:
        return None

    if DICTIONARY_PATTERN is None:
        return None

    match = DICTIONARY_PATTERN.search(text)

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
        "canonical_name": canonical_name,
        "source": "dictionary",
        "start": match.start(),
        "end": match.end(),
    }


# ============================================================
# GENERIC MATCH
# ============================================================

def _extract_from_generic_pattern(
    text: str,
) -> Optional[Dict[str, Any]]:

    if not text:
        return None

    for pattern in GENERIC_UNIVERSITY_PATTERNS:

        match = pattern.search(text)

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
# MAIN EXTRACTOR
# ============================================================

def extract_university(
    text: str,
) -> Optional[Dict[str, Any]]:
    """
    Extract a university from one text line.

    Strategy
    --------
    1. Dictionary matching.
    2. Generic university pattern fallback.
    """

    if not isinstance(text, str):
        return None

    text = text.strip()

    if not text:
        return None

    # Dictionary first.
    result = _extract_from_dictionary(
        text
    )

    if result:
        return result

    # Generic fallback.
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
    university_result: Optional[Dict[str, Any]],
) -> str:
    """
    Remove only the detected university from a line.

    Examples
    --------
    VTU - B.Tech
        -> - B.Tech

    ABC College - VTU - B.Tech
        -> ABC College - - B.Tech
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
        cleaned,
    )

    # Clean separators left around the removed university.
    cleaned = re.sub(
        r"\s*[-–—|]\s*[-–—|]\s*",
        " - ",
        cleaned,
    )

    cleaned = cleaned.strip(
        " -–—|,;"
    )

    return cleaned


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    test_lines = [
        "APJ Abdul Kalam Technological University",
        "Visvesvaraya Technological University",
        "University of Kerala",
        "ABC University",
        "VTU - B.Tech",
        "B.Tech - VTU",
        "ABC College - VTU - B.Tech",
    ]

    for line in test_lines:

        result = extract_university(line)

        print("\nINPUT:")
        print(line)

        print("\nRESULT:")
        print(result)

        if result:
            print("\nREMOVED:")
            print(
                remove_university_content(
                    line,
                    result,
                )
            )
