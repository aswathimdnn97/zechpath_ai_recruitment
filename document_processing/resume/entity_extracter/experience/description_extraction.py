
"""
description_extraction.py

Responsibilities
----------------
1. Extract job responsibilities and achievements.
2. Remove title, company, location, and date metadata.
3. Handle headers and descriptions appearing on the same line.
4. Preserve genuine responsibility sentences.
5. Return description lines as list[str].
"""

import re


DATE_PATTERN = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|"
    r"may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b"
    r"|\b(?:present|current)\b"
    r"|\b\d{4}\b",
    re.IGNORECASE,
)

SEPARATOR_PATTERN = re.compile(r"^[\s\-|,:;–—]+")
SENTENCE_START_PATTERN = re.compile(
    r"\b(?:created|developed|built|implemented|designed|"
    r"maintained|managed|worked|worked on|responsible for|"
    r"assisted|contributed|integrated|tested|tested and|"
    r"practiced|collaborated|optimized|automated|deployed|"
    r"improved|performed|configured|supported|learned)\b",
    re.IGNORECASE,
)


def is_date(text):
    """Return True when the complete line resembles date metadata."""
    if not isinstance(text, str):
        return False

    value = text.strip()

    if not value:
        return False

    return bool(
        re.fullmatch(
            r"(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|"
            r"apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|"
            r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|"
            r"dec(?:ember)?)\s+\d{4}"
            r"|(?:19|20)\d{2}"
            r"|present|current"
            r"|(?:19|20)\d{2}\s*[-–—]\s*"
            r"(?:(?:19|20)\d{2}|present|current))",
            value,
            re.IGNORECASE,
        )
    )


def is_location(text):
    """Recognize standalone location or work-arrangement lines."""
    if not isinstance(text, str):
        return False

    value = text.strip()

    if not value:
        return False

    if value.casefold() in {
        "remote",
        "hybrid",
        "onsite",
        "on-site",
        "work from home",
        "work from anywhere",
    }:
        return True

    return bool(
        re.fullmatch(
            r"[A-Z][a-zA-Z]+(?:[\s-]+[A-Z][a-zA-Z]+)*"
            r"\s*,\s*[A-Z][a-zA-Z]+(?:[\s-]+[A-Z][a-zA-Z]+)*",
            value,
        )
    )


def is_company(text):
    """Heuristic for standalone organization-name lines."""
    if not isinstance(text, str):
        return False

    value = text.strip()

    if not value:
        return False

    keywords = (
        "inc",
        "llc",
        "ltd",
        "limited",
        "technologies",
        "technology",
        "solutions",
        "software",
        "systems",
        "corporation",
        "corp",
        "university",
        "college",
        "institute",
        "school",
    )

    lower = value.casefold()

    return any(
        re.search(
            rf"\b{re.escape(keyword)}\b",
            lower,
        )
        for keyword in keywords
    )


def looks_like_title(text):
    """Heuristic for standalone job-title lines."""
    if not isinstance(text, str):
        return False

    lower = text.casefold()

    title_keywords = (
        "engineer",
        "developer",
        "scientist",
        "manager",
        "analyst",
        "assistant",
        "intern",
        "consultant",
        "specialist",
        "architect",
        "administrator",
        "designer",
        "lead",
        "trainee",
    )

    return any(
        re.search(rf"\b{re.escape(keyword)}\b", lower)
        for keyword in title_keywords
    )


def _normalize_for_comparison(value):
    """Normalize text for reliable case-insensitive comparison."""
    if not isinstance(value, str):
        return ""

    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def _remove_metadata_prefix(text, metadata_values):
    """
    Remove known metadata from the beginning of a line.

    Supports headers such as:
    Backend Development Trainee - ByteBridge Learning Hub Remote
    Created a Django application...
    """
    text = text.strip()

    values = sorted(
        {
            value.strip()
            for value in metadata_values
            if isinstance(value, str) and value.strip()
        },
        key=len,
        reverse=True,
    )

    # Remove repeated leading metadata, in any order.
    changed = True

    while text and changed:
        changed = False
        text = SEPARATOR_PATTERN.sub("", text).strip()

        for value in values:
            if text.casefold().startswith(value.casefold()):
                remainder = text[len(value):]

                # Require a boundary after the matched metadata.
                if remainder and remainder[0].isalnum():
                    continue

                text = remainder.strip()
                text = SEPARATOR_PATTERN.sub("", text).strip()
                changed = True
                break

    return text


def clean_experience_description(
    description,
    title=None,
    company=None,
    location=None,
    duration=None,
):
    """
    Clean a description string while preserving its responsibilities.
    """
    if not isinstance(description, str):
        return ""

    text = " ".join(description.split())

    metadata_values = [title, company, location]

    if isinstance(duration, dict):
        metadata_values.extend(
            [
                duration.get("start_date"),
                duration.get("end_date"),
            ]
        )

    text = _remove_metadata_prefix(text, metadata_values)

    # Remove a remaining known header before the first responsibility.
    # This is limited to a prefix; it never globally deletes company
    # or location words from genuine responsibility sentences.
    for value in sorted(
        [
            value.strip()
            for value in metadata_values
            if isinstance(value, str) and value.strip()
        ],
        key=len,
        reverse=True,
    ):
        pattern = (
            r"^\s*"
            + re.escape(value)
            + r"\s*(?:[-|,:;–—]\s*)?"
        )
        text = re.sub(
            pattern,
            "",
            text,
            count=1,
            flags=re.IGNORECASE,
        ).strip()

    return text.strip(" \t\r\n-|,:;–—")


def extract_description(
    experience_block,
    title=None,
    company=None,
    location=None,
    duration=None,
):
    """
    Extract experience description lines.

    Parameters
    ----------
    experience_block : list[str] | str
    title, company, location : str | None
    duration : dict | None

    Returns
    -------
    list[str]
    """
    if not experience_block:
        return []

    if isinstance(experience_block, str):
        lines = experience_block.splitlines()

    elif isinstance(experience_block, list):
        lines = []

        for item in experience_block:
            if isinstance(item, str):
                lines.extend(item.splitlines())
            elif isinstance(item, list):
                lines.extend(
                    line
                    for line in item
                    if isinstance(line, str)
                )
    else:
        return []

    metadata_values = [title, company, location]

    if isinstance(duration, dict):
        metadata_values.extend(
            [
                duration.get("start_date"),
                duration.get("end_date"),
            ]
        )

    descriptions = []

    for raw_line in lines:
        if not isinstance(raw_line, str):
            continue

        line = " ".join(raw_line.split()).strip()

        if not line:
            continue

        # Crucially, strip known metadata before classifying the line.
        # Otherwise a combined header/responsibility line is discarded
        # merely because it contains a job-title keyword.
        line = _remove_metadata_prefix(line, metadata_values)

        if not line:
            continue

        # Skip metadata-only lines.
        if is_date(line):
            continue

        if is_location(line):
            continue

        if (
            _normalize_for_comparison(line)
            in {
                _normalize_for_comparison(title),
                _normalize_for_comparison(company),
                _normalize_for_comparison(location),
            }
            and _normalize_for_comparison(line)
        ):
            continue

        # Skip standalone title/company lines, not sentences containing
        # those words alongside actual responsibilities.
        if (
            looks_like_title(line)
            and not SENTENCE_START_PATTERN.search(line)
            and not re.search(r"\s[-|]\s", line)
        ):
            continue

        if is_company(line) and not SENTENCE_START_PATTERN.search(line):
            continue

        cleaned = clean_experience_description(
            line,
            title=title,
            company=company,
            location=location,
            duration=duration,
        )

        if cleaned:
            descriptions.append(cleaned)

    return descriptions
