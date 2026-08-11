import re


# ============================================================
# Patterns
# ============================================================

DATE_PATTERN = re.compile(
    r"""
    ^
    (?:
        (?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|
        may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|
        oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)
        \s+\d{4}
        |
        \d{4}
        |
        \d{4}\s*[-–]\s*\d{4}
    )
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)


URL_PATTERN = re.compile(
    r"^(?:https?://|www\.|github\.com|gitlab\.com|bitbucket\.org)",
    re.IGNORECASE,
)


# ============================================================
# Metadata labels that should NOT be treated as project names
# ============================================================

METADATA_LABELS = {
    "project",
    "projects",
    "project name",
    "description",
    "technologies",
    "technology",
    "tech stack",
    "tools",
    "skills",
    "role",
    "responsibilities",
    "github",
    "demo",
    "url",
}


# ============================================================
# Helpers
# ============================================================

def _clean_line(line):
    """
    Clean a single resume line.
    """

    line = line.strip()

    # Remove common bullet characters
    line = re.sub(r"^[•●▪◦*-]\s*", "", line)

    # Normalize whitespace
    line = re.sub(r"\s+", " ", line)

    return line.strip()


def _is_invalid_project_name(line):
    """
    Determine whether a line should not be considered
    as a project name.
    """

    if not line:
        return True

    normalized = line.lower().strip(":- ")

    # Section / metadata labels
    if normalized in METADATA_LABELS:
        return True

    # Date
    if DATE_PATTERN.match(line):
        return True

    # URL
    if URL_PATTERN.match(line):
        return True

    # Technology metadata
    if normalized.startswith(
        (
            "technologies:",
            "technology:",
            "tech stack:",
            "tools:",
            "skills:",
        )
    ):
        return True

    # URL metadata
    if normalized.startswith(
        (
            "github:",
            "demo:",
            "url:",
            "repository:",
        )
    ):
        return True

    return False


# ============================================================
# Main extractor
# ============================================================

def extract_project_name(block):
    """
    Extract project name from a project block.

    Parameters
    ----------
    block : list[str] | str
        Isolated project block.

    Returns
    -------
    str | None
        Extracted project name.
    """

    if not block:
        return None

    # Support both list[str] and raw string input
    if isinstance(block, str):
        lines = block.splitlines()
    else:
        lines = block

    for line in lines:

        line = _clean_line(line)

        if _is_invalid_project_name(line):
            continue

        return line

    return None


block = [
    "AI Resume Screening System",
    "Jan 2025 - Apr 2025",
    "Developed an AI-based resume screening platform.",
    "Technologies: Python, FastAPI, PostgreSQL",
    "GitHub: https://github.com/example/project"
]

result = extract_project_name(block)

print(result)