import re


# ============================================================
# Patterns
# ============================================================

METADATA_PATTERN = re.compile(
    r"""
    ^
    (?:
        technologies?
        |tech\s*stack
        |tools
        |skills
        |role
        |responsibilities
        |github
        |gitlab
        |repository
        |repo
        |demo
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


# ============================================================
# Helpers
# ============================================================

def clean_line(line):
    """
    Clean a single resume line.
    """

    if not line:
        return ""

    line = line.strip()

    # Remove common bullet characters
    line = re.sub(r"^[•●▪◦*-]\s*", "", line)

    # Normalize whitespace
    line = re.sub(r"\s+", " ", line)

    return line.strip()


def is_metadata_line(line):
    """
    Check whether a line contains project metadata
    rather than description.
    """

    return bool(METADATA_PATTERN.match(line))


def is_url_line(line):
    """
    Check whether a line is a URL or URL-related line.
    """

    return bool(URL_PATTERN.search(line))


# ============================================================
# Main Extractor
# ============================================================

def extract_project_description(block):
    """
    Extract project description from an individual project block.

    Parameters
    ----------
    block : list[str] | str
        Individual project block.

    Returns
    -------
    str | None
        Project description.
    """

    if not block:
        return None

    # --------------------------------------------------------
    # Support both list input and string input
    # --------------------------------------------------------

    if isinstance(block, str):
        lines = block.splitlines()
    else:
        lines = block

    cleaned_lines = [
        clean_line(line)
        for line in lines
    ]

    cleaned_lines = [
        line for line in cleaned_lines
        if line
    ]

    if len(cleaned_lines) <= 1:
        return None

    # --------------------------------------------------------
    # First line is normally the project name
    # --------------------------------------------------------

    description_lines = []

    for line in cleaned_lines[1:]:

        # Skip metadata
        if is_metadata_line(line):
            continue

        # Skip URLs
        if is_url_line(line):
            continue

        description_lines.append(line)

    if not description_lines:
        return None

    # --------------------------------------------------------
    # Combine description lines
    # --------------------------------------------------------

    description = " ".join(description_lines)

    # Normalize spaces
    description = re.sub(r"\s+", " ", description).strip()

    return description or None