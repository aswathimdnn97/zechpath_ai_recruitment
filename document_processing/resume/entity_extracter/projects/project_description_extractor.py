
import re

from document_processing.resume.entity_extracter.projects.project_technologies_extractor import (
    extract_project_narrative_from_technology_line,
    is_technology_line,
)


# ============================================================
# Patterns
# ============================================================

METADATA_PATTERN = re.compile(
    r"""
    ^
    (?:
        technologies?(?:\s+used)?
        |tech\s*stack
        |tools?(?:\s*(?:&|and)\s*technologies?)?
        |skills
        |role
        |responsibilities
        |github
        |gitlab
        |repository
        |repo
        |demo
        |live
        |website
        |url
        |link
    )
    \s*:
    """,
    re.IGNORECASE | re.VERBOSE,
)

URL_PATTERN = re.compile(
    r"""
    (?:
        https?://
        |
        www\.
        |
        github\.com
        |
        gitlab\.com
        |
        bitbucket\.org
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

DATE_PATTERN = re.compile(
    r"""
    ^
    (?:
        \d{4}
        |
        \d{4}\s*[-–—]\s*(?:\d{4}|present|current)
        |
        (?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|
        may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|
        oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}
    )
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)

ACTION_PATTERN = re.compile(
    r"""
    \b
    (?:
        developed|built|designed|implemented|created|
        engineered|architected|integrated|deployed|
        managed|tested|maintained|configured|validated|
        automated|connected|used|improved|established|
        delivered|supported|provided|worked|led
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

BULLET_PATTERN = re.compile(r"^[•●▪◦*\-]+\s*")

# Matches a title followed by an action-oriented description.
INLINE_SEPARATOR_PATTERN = re.compile(r"\s+[-–—:]\s+")


# ============================================================
# Helpers
# ============================================================

def clean_line(line):
    """Clean a single resume line."""

    if not isinstance(line, str):
        return ""

    line = line.strip()
    line = BULLET_PATTERN.sub("", line)
    line = re.sub(r"\s+", " ", line)

    return line.strip()


def is_metadata_line(line):
    """Check whether a line contains project metadata."""

    return bool(METADATA_PATTERN.match(line))


def is_url_line(line):
    """Check whether a line contains URL information."""

    return bool(URL_PATTERN.search(line))


def _is_date_line(line):
    """Identify standalone date or date-range lines."""

    return bool(DATE_PATTERN.fullmatch(line.strip()))


def _extract_inline_description(line):
    """
    Extract the description when the title and narrative share a line.

    Example:
        Student Records REST API - Developed a backend service.

    Returns:
        Developed a backend service.
    """

    match = INLINE_SEPARATOR_PATTERN.search(line)

    if not match:
        return None

    title = line[:match.start()].strip()
    remainder = line[match.end():].strip()

    if not title or not remainder:
        return None

    # Avoid splitting ordinary hyphenated project names.
    action_match = ACTION_PATTERN.search(remainder)

    if action_match and action_match.start() <= 15:
        return remainder

    return None


def _extract_technology_narrative(line):
    """
    Extract narrative appended to a technology-labelled line.

    The technology extractor determines where its technology
    list ends and narrative text begins.
    """

    try:
        if not is_technology_line(line):
            return None

        narrative = extract_project_narrative_from_technology_line(
            line
        )

        return clean_line(narrative) or None

    except (TypeError, ValueError, AttributeError):
        return None


def _is_project_heading(line):
    """Identify a standalone project heading."""

    return bool(
        re.match(
            r"^(?:project|project name)\s*:",
            line,
            re.IGNORECASE,
        )
    )


# ============================================================
# Main Extractor
# ============================================================

def extract_project_description(block):
    """
    Extract project description from an individual project block.

    Supports:
    - Title and description on the same line.
    - Descriptions on subsequent lines.
    - Narrative following a technology label.
    - String, list, or tuple input.

    Returns:
        str | None: Extracted description, or None if unavailable.
    """

    if not block:
        return None

    if isinstance(block, str):
        lines = block.splitlines()
    elif isinstance(block, (list, tuple)):
        lines = list(block)
    else:
        return None

    cleaned_lines = [
        clean_line(line)
        for line in lines
        if isinstance(line, str)
    ]

    cleaned_lines = [
        line for line in cleaned_lines if line
    ]

    if not cleaned_lines:
        return None

    description_lines = []

    # First, check whether the first line contains both the
    # project title and its description.
    inline_description = _extract_inline_description(
        cleaned_lines[0]
    )

    if inline_description:
        description_lines.append(inline_description)

    # Process all remaining lines.
    start_index = 1

    for line in cleaned_lines[start_index:]:

        # Skip standalone date lines.
        if _is_date_line(line):
            continue

        # Extract narrative that may follow a technology list.
        if is_technology_line(line):
            narrative = _extract_technology_narrative(line)

            if narrative:
                description_lines.append(narrative)

            continue

        # Ignore metadata and URL lines.
        if is_metadata_line(line):
            continue

        if is_url_line(line):
            continue

        # Ignore standalone project headings.
        if _is_project_heading(line):
            continue

        description_lines.append(line)

    if not description_lines:
        return None

    description = " ".join(description_lines)
    description = re.sub(r"\s+", " ", description).strip()

    return description or None
