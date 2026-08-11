import re


# ============================================================
# Patterns
# ============================================================

TECHNOLOGY_LABEL_PATTERN = re.compile(
    r"""
    ^
    (?:
        technologies?
        |tech\s*stack
        |technology\s*stack
        |tools
        |technologies\s*used
        |tools\s*used
        |built\s*with
        |developed\s*using
        |using
    )
    \s*[:\-]?\s*
    (.+)
    $
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
# Technology separators
# ============================================================

TECH_SEPARATOR_PATTERN = re.compile(
    r"\s*(?:,|\||;|•)\s*"
)


# ============================================================
# Common technology prefixes
# ============================================================

TECH_PREFIXES = (
    "technologies:",
    "technology:",
    "tech stack:",
    "technology stack:",
    "tools:",
    "technologies used:",
    "tools used:",
    "built with:",
    "developed using:",
    "using:",
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

    # Remove bullets
    line = re.sub(r"^[•●▪◦*-]\s*", "", line)

    # Normalize whitespace
    line = re.sub(r"\s+", " ", line)

    return line.strip()


def is_technology_line(line):
    """
    Check whether a line explicitly contains
    technology information.
    """

    return bool(TECHNOLOGY_LABEL_PATTERN.match(line))


def extract_technology_text(line):
    """
    Extract the text after a technology label.
    """

    match = TECHNOLOGY_LABEL_PATTERN.match(line)

    if not match:
        return None

    return match.group(1).strip()


def split_technologies(text):
    """
    Split a technology string into individual technologies.
    """

    if not text:
        return []

    # Remove URLs
    text = URL_PATTERN.sub("", text)

    # Normalize common separators
    parts = TECH_SEPARATOR_PATTERN.split(text)

    technologies = []

    for part in parts:

        part = part.strip()

        if not part:
            continue

        technologies.append(part)

    return technologies


def clean_technology(technology):
    """
    Clean an individual technology name.
    """

    technology = technology.strip()

    # Remove surrounding punctuation
    technology = technology.strip(":-,;|")

    # Normalize whitespace
    technology = re.sub(r"\s+", " ", technology)

    return technology.strip()


# ============================================================
# Main Extractor
# ============================================================

def extract_project_technologies(block):
    """
    Extract technologies from an individual project block.

    Parameters
    ----------
    block : list[str] | str
        Individual project block.

    Returns
    -------
    list[str]
        Extracted technologies.
    """

    if not block:
        return []

    # --------------------------------------------------------
    # Support string input
    # --------------------------------------------------------

    if isinstance(block, str):
        lines = block.splitlines()
    else:
        lines = block

    technologies = []

    # --------------------------------------------------------
    # Extract explicit technology lines
    # --------------------------------------------------------

    for raw_line in lines:

        line = clean_line(raw_line)

        if not line:
            continue

        if not is_technology_line(line):
            continue

        technology_text = extract_technology_text(line)

        if not technology_text:
            continue

        extracted = split_technologies(technology_text)

        for technology in extracted:

            technology = clean_technology(technology)

            if technology:
                technologies.append(technology)

    # --------------------------------------------------------
    # Remove duplicates while preserving order
    # --------------------------------------------------------

    unique_technologies = []
    seen = set()

    for technology in technologies:

        key = technology.lower()

        if key not in seen:
            seen.add(key)
            unique_technologies.append(technology)

    return unique_technologies

block = [
    "AI Resume Screening System",
    "Developed an AI-based resume screening platform.",
    "Technologies: Python, FastAPI, PostgreSQL, Sentence Transformers",
    "Tech Stack: React | Node.js | Express | MongoDB",
   " Tools: Docker; Kubernetes; AWS; Git",
    "GitHub: https://github.com/example/project"
]

result = extract_project_technologies(block)

print(result)