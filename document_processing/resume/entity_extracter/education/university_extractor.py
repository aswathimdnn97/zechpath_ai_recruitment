
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
8. Remove graduation years from university-name remainders.
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

    if not isinstance(text, str) or not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()


# ============================================================
# REMOVE YEARS FROM UNIVERSITY REMAINDER
# ============================================================

def remove_years_from_university_remainder(
    text: str,
) -> str:
    """
    Remove standalone four-digit years from text that may
    otherwise be appended to a university name.

    Examples
    --------
    ', 2025'       -> ''
    ' - 2025'      -> ''
    ', 2020 - 2025' -> ''
    'Campus, 2025' -> 'Campus'

    This function should be applied to the remainder, not
    indiscriminately to the original university name.

    Graduation-year extraction should remain a separate step.
    """

    if not isinstance(text, str) or not text:
        return ""

    # Remove standalone years between 1900 and 2099.
    text = re.sub(
        r"(?<!\d)(?:19|20)\d{2}(?!\d)",
        "",
        text,
    )

    # Normalize separators left after removing years without flattening
    # commas that separate location components.
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*[;|]\s*", " ", text)
    text = re.sub(
        r"\s*[-–—]\s*",
        " ",
        text,
    )

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip(" ,;|–—-")


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

    except (json.JSONDecodeError, OSError) as exc:
        print(
            f"[WARNING] Failed to load university dictionary: "
            f"{exc}"
        )
        return []

    if isinstance(data, dict):
        universities = data.get("universities", [])

    elif isinstance(data, list):
        universities = data

    else:
        universities = []

    return universities if isinstance(universities, list) else []


UNIVERSITIES = _load_university_dictionary()


# ============================================================
# ALIAS LOOKUP
# ============================================================

def _build_alias_lookup():

    lookup = {}

    for university in UNIVERSITIES:

        if not isinstance(university, dict):
            continue

        canonical_name = university.get("canonical_name")

        if not isinstance(canonical_name, str):
            continue

        canonical_name = canonical_name.strip()

        if not canonical_name:
            continue

        aliases = university.get("aliases", [])

        if not isinstance(aliases, list):
            aliases = [aliases]

        # The canonical name is also a valid alias.
        aliases = list(aliases)
        aliases.append(canonical_name)

        for alias in aliases:

            if not isinstance(alias, str):
                continue

            normalized_alias = normalize_university_text(alias)

            if not normalized_alias:
                continue

            lookup[normalized_alias] = canonical_name

    return lookup


ALIAS_LOOKUP = _build_alias_lookup()


# ============================================================
# DICTIONARY REGEX
# ============================================================

def _build_dictionary_pattern():

    aliases = list(ALIAS_LOOKUP.keys())

    if not aliases:
        return None

    # Match longer aliases before shorter aliases.
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


DICTIONARY_PATTERN = _build_dictionary_pattern()


# ============================================================
# GENERIC UNIVERSITY PATTERNS
# ============================================================

GENERIC_UNIVERSITY_PATTERNS = [

    # Examples:
    # University of Kerala
    # University of Delhi
    re.compile(
        r"\bUniversity\s+of\s+"
        r"[A-Za-z][A-Za-z0-9&.'()-]*"
        r"(?:\s+[A-Za-z][A-Za-z0-9&.'()-]*){0,6}",
        flags=re.IGNORECASE,
    ),

    # Examples:
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
    """
    Extract a university using dictionary aliases.

    start and end refer to positions in the supplied text.
    """

    if not text or DICTIONARY_PATTERN is None:
        return None

    match = DICTIONARY_PATTERN.search(text)

    if not match:
        return None

    value = match.group(0).strip()

    normalized = normalize_university_text(value)

    canonical_name = ALIAS_LOOKUP.get(normalized)

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
    """
    Detect university names not present in the dictionary.
    """

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
    2. Generic pattern fallback.

    The returned value preserves the matched text.
    """

    if not isinstance(text, str):
        return None

    text = text.strip()

    if not text:
        return None

    # Dictionary matching first.
    result = _extract_from_dictionary(text)

    if result:
        return result

    # Generic university-name fallback.
    return _extract_from_generic_pattern(text)


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
    'VTU - B.Tech'
        -> 'B.Tech'

    'ABC College - VTU - B.Tech'
        -> 'ABC College - B.Tech'

    'University of Calicut, 2025'
        -> '2025'
    """

    if not isinstance(text, str) or not text:
        return ""

    if not university_result:
        return text

    start = university_result.get("start")
    end = university_result.get("end")

    if not isinstance(start, int) or not isinstance(end, int):
        return text

    if start < 0 or end < start or end > len(text):
        return text

    cleaned = text[:start] + " " + text[end:]

    # Normalize whitespace.
    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    )

    # Remove duplicated separators.
    cleaned = re.sub(
        r"\s*[-–—|]\s*[-–—|]\s*",
        " - ",
        cleaned,
    )

    return cleaned.strip(" -–—|,;")


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
        "University of Calicut, 2025",
    ]

    for line in test_lines:

        result = extract_university(line)

        print("\nINPUT:")
        print(line)

        print("\nUNIVERSITY RESULT:")
        print(result)

        if result:
            print("\nREMOVED UNIVERSITY:")
            print(
                remove_university_content(
                    line,
                    result,
                )
            )

    print("\nYEAR REMOVAL TESTS:")

    year_test_cases = [
        ", 2025",
        " - 2025",
        ", 2020 - 2025",
        "Campus, 2025",
    ]

    for value in year_test_cases:
        print(
            repr(value),
            "->",
            repr(
                remove_years_from_university_remainder(
                    value
                )
            ),
        )


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
