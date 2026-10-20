
import re

from document_processing.resume.entity_extracter.projects.project_technologies_extractor import (
    is_technology_line,
    extract_project_narrative_from_technology_line,
)


# ============================================================
# PROJECT LABEL
# ============================================================

PROJECT_LABEL_PATTERN = re.compile(
    r"^\s*project(?:\s+name)?\s*[:\-–—]\s*(.+?)\s*$",
    re.IGNORECASE,
)


# ============================================================
# METADATA LABELS
# ============================================================

METADATA_LABEL_PATTERN = re.compile(
    r"^\s*(?:"
    r"technologies?(?:\s+used)?"
    r"|tech\s+stack"
    r"|technology\s+stack"
    r"|tools?(?:\s+used)?"
    r"|built\s+with"
    r"|developed\s+using"
    r"|using"
    r"|github"
    r"|gitlab"
    r"|bitbucket"
    r"|repository"
    r"|repo"
    r"|demo"
    r"|live"
    r"|website"
    r"|url"
    r"|link"
    r"|role"
    r"|responsibilities"
    r")\s*:",
    re.IGNORECASE,
)


# ============================================================
# URL
# ============================================================

URL_PATTERN = re.compile(
    r"(?:"
    r"https?://"
    r"|www\."
    r"|github\.com/"
    r"|gitlab\.com/"
    r"|bitbucket\.org/"
    r")",
    re.IGNORECASE,
)


# ============================================================
# INLINE TITLE AND DESCRIPTION
# ============================================================

DESCRIPTION_ACTION_PATTERN = re.compile(
    r"\b(?:"
    r"developed|built|implemented|created|designed|"
    r"engineered|integrated|deployed|managed|tested|"
    r"maintained|configured|validated|automated|"
    r"connected|improved|established|delivered|"
    r"supported|provided|used|worked"
    r")\b",
    re.IGNORECASE,
)

INLINE_SEPARATOR_PATTERN = re.compile(r"\s+[-–—:]\s+")


# ============================================================
# CLEAN LINE
# ============================================================

def clean_line(line):
    if not line:
        return ""

    line = str(line).strip()

    line = re.sub(r"^[•●▪◦*\-]+\s*", "", line)
    line = re.sub(r"\s+", " ", line)

    return line.strip()


# ============================================================
# LABEL HELPERS
# ============================================================

def is_project_label(line):
    if not line:
        return False

    return bool(PROJECT_LABEL_PATTERN.match(line))


def extract_project_name_from_label(line):
    match = PROJECT_LABEL_PATTERN.match(line)

    if not match:
        return None

    return match.group(1).strip() or None


def is_metadata_line(line):
    if not line:
        return False

    return bool(METADATA_LABEL_PATTERN.match(line))


def is_url_line(line):
    if not line:
        return False

    return bool(URL_PATTERN.search(line))


# ============================================================
# SPLIT INLINE PROJECT TITLE AND DESCRIPTION
# ============================================================

def split_inline_project_line(line):
    """
    Split a combined project title and description.

    Example:
        Student Records REST API - Developed a backend service.

    Returns:
        ("Student Records REST API", "Developed a backend service.")

    If the line does not look like a combined title and
    description, returns (line, None).
    """

    if not line:
        return "", None

    match = INLINE_SEPARATOR_PATTERN.search(line)

    if not match:
        return line, None

    title = line[:match.start()].strip()
    remainder = line[match.end():].strip()

    if not title or not remainder:
        return line, None

    # Only split when the right-hand side begins with an
    # action-oriented description.
    action_match = DESCRIPTION_ACTION_PATTERN.search(remainder)

    if action_match and action_match.start() <= 15:
        return title, remainder

    return line, None


# ============================================================
# PROJECT TITLE HEURISTIC
# ============================================================

def looks_like_project_title(line):
    if not line:
        return False

    if is_metadata_line(line) or is_url_line(line):
        return False

    if is_project_label(line):
        return False

    # A combined title and description is not a new title.
    title, description = split_inline_project_line(line)

    if description:
        return False

    if len(line) > 80:
        return False

    words = line.split()

    if len(words) > 10:
        return False

    if line.endswith((".", "!", "?")):
        return False

    description_starters = (
        "built ",
        "developed ",
        "implemented ",
        "created ",
        "designed ",
        "worked ",
        "developing ",
        "using ",
        "used ",
        "responsible ",
        "managed ",
        "integrated ",
        "deployed ",
        "added ",
        "connected ",
        "validated ",
        "tested ",
        "maintained ",
        "automated ",
    )

    if line.lower().startswith(description_starters):
        return False

    return True


# ============================================================
# SPLIT PROJECT BLOCKS
# ============================================================

def split_project_blocks(section):
    if not section:
        return []

    # --------------------------------------------------------
    # Convert input to lines
    # --------------------------------------------------------

    if isinstance(section, str):
        raw_lines = section.splitlines()

    elif isinstance(section, (list, tuple)):
        raw_lines = []

        for item in section:
            if isinstance(item, (list, tuple)):
                raw_lines.extend(item)

            elif isinstance(item, str):
                raw_lines.extend(item.splitlines())

    else:
        return []

    # --------------------------------------------------------
    # Clean lines
    # --------------------------------------------------------

    lines = []

    for raw_line in raw_lines:
        if not isinstance(raw_line, str):
            continue

        line = clean_line(raw_line)

        if line:
            lines.append(line)

    if not lines:
        return []

    # --------------------------------------------------------
    # Build blocks
    # --------------------------------------------------------

    blocks = []
    current_block = []

    for line in lines:

        # Explicit project label.
        if is_project_label(line):
            if current_block:
                blocks.append(current_block)

            current_block = []

            project_name = extract_project_name_from_label(line)

            if project_name:
                # Support labels containing inline descriptions too.
                title, description = split_inline_project_line(
                    project_name
                )

                current_block.append(title)

                if description:
                    current_block.append(description)

            continue

        # Separate inline title and description before processing
        # metadata or project-boundary heuristics.
        title, inline_description = split_inline_project_line(line)

        if inline_description:
            if current_block:
                blocks.append(current_block)

            current_block = [title, inline_description]
            continue

        # Metadata belongs to the current project.
        if (
            is_metadata_line(line)
            or is_technology_line(line)
            or is_url_line(line)
        ):
            current_block.append(line)
            continue

        # Possible new project title.
        if (
            current_block
            and len(current_block) >= 2
            and looks_like_project_title(line)
        ):
            blocks.append(current_block)
            current_block = [line]
            continue

        # Normal description line.
        current_block.append(line)

    if current_block:
        blocks.append(current_block)

    return [block for block in blocks if block]


