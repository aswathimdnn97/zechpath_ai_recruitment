
import re


TECHNOLOGY_LABEL_PATTERN = re.compile(
    r"^\s*(?:"
    r"technologies?(?:\s+used)?|tech\s*stack|"
    r"tools?(?:\s*(?:&|and)\s*technologies?)?|"
    r"languages?(?:\s*(?:&|and)\s*frameworks?)?|"
    r"frameworks?(?:\s+and\s+libraries)?|"
    r"built\s+(?:with|using)|developed\s+using"
    r")\s*[:\-–—]\s*(.+)$",
    re.IGNORECASE,
)

URL_PATTERN = re.compile(
    r"https?://\S+|www\.\S+|"
    r"(?:github\.com|gitlab\.com|bitbucket\.org)/\S+",
    re.IGNORECASE,
)

# Extend this list as your master skill dictionary grows.
KNOWN_TECHNOLOGIES = [
    "Python",
    "Django",
    "FastAPI",
    "Flask",
    "PostgreSQL",
    "MySQL",
    "SQLite",
    "SQL",
    "Git",
    "GitHub",
    "Postman",
    "REST API",
    "React",
    "JavaScript",
    "TypeScript",
    "Java",
    "Spring Boot",
    "MongoDB",
    "Redis",
    "Docker",
    "AWS",
    "HTML",
    "CSS",
]

# Match longer names first, e.g. Spring Boot before Java.
TECHNOLOGY_PATTERN = re.compile(
    r"(?<!\w)(?:"
    + "|".join(
        re.escape(item)
        for item in sorted(KNOWN_TECHNOLOGIES, key=len, reverse=True)
    )
    + r")(?!\w)",
    re.IGNORECASE,
)

SEPARATOR_PATTERN = re.compile(r"\s*[,;|•]\s*")


def clean_line(line):
    if not isinstance(line, str):
        return ""

    line = re.sub(r"^[•●▪◦*\-]+\s*", "", line.strip())
    return re.sub(r"\s+", " ", line).strip()


def is_technology_line(line):
    """
    Check whether a line contains an explicit technology label.

    Supports labels such as:
    Technologies: Python, Django
    Technology Used: FastAPI
    Tech Stack: React, Django
    Tools: Git, Postman
    Built with Python, Django
    Developed using FastAPI
    """
    if not isinstance(line, str) or not line.strip():
        return False

    return bool(TECHNOLOGY_LABEL_PATTERN.match(line.strip()))

def _split_list(text):
    text = URL_PATTERN.sub("", text)
    return [
        item.strip(" \t.,;:|")
        for item in SEPARATOR_PATTERN.split(text)
        if item.strip(" \t.,;:|")
    ]


def _extract_known_technologies(text):
    text = URL_PATTERN.sub("", text)
    text = re.sub(
        r"\b(?:github|gitlab|bitbucket)\s*:\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return [match.group(0) for match in TECHNOLOGY_PATTERN.finditer(text)]

def extract_project_narrative_from_technology_line(line):
    """
    Extract narrative text that follows the technology list.

    Example:
        Technologies: Python, Django. Developed a REST API.

    Returns:
        Developed a REST API.
    """
    match = TECHNOLOGY_LABEL_PATTERN.match(line.strip())

    if not match:
        return None

    technology_text = match.group(1).strip()

    narrative_pattern = re.compile(
        r"\s+(?=(?:"
        r"developed|built|designed|implemented|created|"
        r"engineered|integrated|deployed|managed|tested|"
        r"maintained|configured|validated|automated"
        r")\b)",
        re.IGNORECASE,
    )

    boundary = narrative_pattern.search(technology_text)

    if not boundary:
        return None

    return technology_text[boundary.start():].strip() or None



def extract_project_technologies(block):
    if not block:
        return []

    lines = block.splitlines() if isinstance(block, str) else block
    technologies = []
    seen = set()

    for raw_line in lines:
        line = clean_line(raw_line)

        if not line:
            continue

        # First handle explicit technology labels.
        label_match = TECHNOLOGY_LABEL_PATTERN.match(line)

        if label_match:
            found = _split_list(label_match.group(1))
        else:
            # Also find recognized technologies in narrative text.
            found = _extract_known_technologies(line)

        for technology in found:
            key = technology.casefold()

            if key not in seen:
                seen.add(key)
                technologies.append(technology)

    return technologies
