import re


# ============================================================
# TECHNOLOGY LABEL
# ============================================================

TECHNOLOGY_LABEL_PATTERN = re.compile(
    r"""
    ^
    (?:
        technolog(?:y|ies)(?:\s+used)?
        |tech(?:nology)?\s*stack
        |tools?(?:\s*(?:&|and)\s*technologies?)?(?:\s+used)?
        |languages?(?:\s*(?:&|and)\s*frameworks?)?
        |frameworks?(?:\s+and\s+libraries)?
        |built\s+(?:with|using)
        |developed\s+using
        |using
    )
    (?:\s*[:\-–—]\s*|\s+)
    (.+)
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)

PROJECT_NARRATIVE_START_PATTERN = re.compile(
    r"\s+(?=(?:"
    r"built|developed|designed|implemented|created|engineered|"
    r"architected|led|added|integrated|deployed|managed|automated|"
    r"established|delivered|tested|used|worked|improved|maintained|"
    r"configured|supported|provided|created|"
    r"the\s+project|this\s+project|the\s+application|the\s+system"
    r")\b)",
    re.IGNORECASE,
)


# ============================================================
# URL
# ============================================================

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
# TECHNOLOGY SEPARATOR
# ============================================================

TECH_SEPARATOR_PATTERN = re.compile(
    r"\s*(?:,|\||;|•|&|\band\b)\s*",
    re.IGNORECASE,
)


# ============================================================
# CLEAN LINE
# ============================================================

def clean_line(line):

    if not line:
        return ""

    line = str(line).strip()

    line = re.sub(
        r"^[•●▪◦*\-]\s*",
        "",
        line,
    )

    line = re.sub(
        r"\s+",
        " ",
        line,
    )

    return line.strip()


# ============================================================
# TECHNOLOGY LINE
# ============================================================

def is_technology_line(line):

    if not line:
        return False

    return bool(
        TECHNOLOGY_LABEL_PATTERN.match(line)
    )


# ============================================================
# EXTRACT TECHNOLOGY TEXT
# ============================================================

def extract_technology_text(line):

    match = TECHNOLOGY_LABEL_PATTERN.match(line)

    if not match:
        return None

    technology_text = match.group(1).strip()
    narrative_boundary = PROJECT_NARRATIVE_START_PATTERN.search(
        technology_text
    )

    if narrative_boundary:
        technology_text = technology_text[:narrative_boundary.start()]

    return technology_text.strip(" .;")


def extract_project_narrative_from_technology_line(line):
    match = TECHNOLOGY_LABEL_PATTERN.match(line)

    if not match:
        return None

    technology_text = match.group(1).strip()
    narrative_boundary = PROJECT_NARRATIVE_START_PATTERN.search(
        technology_text
    )

    if not narrative_boundary:
        return None

    narrative = technology_text[narrative_boundary.start():].strip()
    return narrative or None


# ============================================================
# SPLIT TECHNOLOGIES
# ============================================================

def split_technologies(text):

    if not text:
        return []

    # Remove URLs
    text = URL_PATTERN.sub("", text)

    parts = TECH_SEPARATOR_PATTERN.split(text)

    technologies = []

    for part in parts:

        part = part.strip()

        if not part:
            continue

        technologies.append(part)

    return technologies


# ============================================================
# CLEAN TECHNOLOGY
# ============================================================

def clean_technology(technology):

    if not technology:
        return ""

    technology = technology.strip()

    technology = technology.strip(
        ":-,;|"
    )

    technology = re.sub(
        r"\s+",
        " ",
        technology,
    )

    return technology.strip()


# ============================================================
# EXTRACT PROJECT TECHNOLOGIES
# ============================================================

def extract_project_technologies(block):

    if not block:
        return []

    if isinstance(block, str):

        lines = block.splitlines()

    elif isinstance(block, list):

        lines = block

    else:
        return []

    technologies = []

    for raw_line in lines:

        if not isinstance(raw_line, str):
            continue

        line = clean_line(raw_line)

        if not line:
            continue

        if not is_technology_line(line):
            continue

        technology_text = extract_technology_text(line)

        if not technology_text:
            continue

        extracted = split_technologies(
            technology_text
        )

        for technology in extracted:

            technology = clean_technology(
                technology
            )

            if technology:
                technologies.append(
                    technology
                )

    # --------------------------------------------------------
    # Remove duplicates while preserving order
    # --------------------------------------------------------

    unique_technologies = []

    seen = set()

    for technology in technologies:

        key = technology.lower()

        if key in seen:
            continue

        seen.add(key)

        unique_technologies.append(
            technology
        )

    return unique_technologies