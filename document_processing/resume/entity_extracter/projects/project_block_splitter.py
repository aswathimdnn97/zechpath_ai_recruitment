import re

from document_processing.resume.entity_extracter.projects.project_technologies_extractor import (
    is_technology_line,
)


# ============================================================
# PROJECT LABEL
# ============================================================

PROJECT_LABEL_PATTERN = re.compile(
    r"^\s*project(?:\s*name)?\s*[:\-]\s*(.+?)\s*$",
    re.IGNORECASE,
)


# ============================================================
# METADATA LABELS
# ============================================================

METADATA_LABEL_PATTERN = re.compile(
    r"^\s*(?:"
    r"technologies?"
    r"|tech\s+stack"
    r"|technology\s+stack"
    r"|tools"
    r"|technologies\s+used"
    r"|tools\s+used"
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
# CLEAN LINE
# ============================================================

def clean_line(line):
    if not line:
        return ""

    line = str(line).strip()

    # Remove bullet characters
    line = re.sub(
        r"^[•●▪◦*\-]\s*",
        "",
        line,
    )

    # Normalize whitespace
    line = re.sub(r"\s+", " ", line)

    return line.strip()


# ============================================================
# PROJECT LABEL
# ============================================================

def is_project_label(line):
    if not line:
        return False

    return bool(
        PROJECT_LABEL_PATTERN.match(line)
    )


def extract_project_name_from_label(line):
    match = PROJECT_LABEL_PATTERN.match(line)

    if not match:
        return None

    return match.group(1).strip()


# ============================================================
# METADATA
# ============================================================

def is_metadata_line(line):
    if not line:
        return False

    return bool(
        METADATA_LABEL_PATTERN.match(line)
    )


# ============================================================
# URL LINE
# ============================================================

def is_url_line(line):
    if not line:
        return False

    return bool(
        URL_PATTERN.search(line)
    )


# ============================================================
# PROJECT TITLE HEURISTIC
# ============================================================

def looks_like_project_title(line):
    if not line:
        return False

    if is_metadata_line(line):
        return False

    if is_url_line(line):
        return False

    if is_project_label(line):
        return False

    # Too long to reasonably be a project title
    if len(line) > 80:
        return False

    words = line.split()

    if len(words) > 10:
        return False

    # Sentence-like lines are usually descriptions
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
        "implemented ",
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

    elif isinstance(section, list):

        raw_lines = []

        for item in section:

            if isinstance(item, list):
                raw_lines.extend(item)

            elif isinstance(item, str):
                raw_lines.append(item)

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

        # ====================================================
        # EXPLICIT PROJECT LABEL
        # ====================================================

        if is_project_label(line):

            # Save previous project only if it has content
            if current_block:
                blocks.append(current_block)

            current_block = []

            project_name = extract_project_name_from_label(line)

            if project_name:
                current_block.append(project_name)

            continue

        # ====================================================
        # METADATA
        #
        # IMPORTANT:
        # Metadata belongs to the current project.
        # It must NEVER start a new project.
        # ====================================================

        if (
            is_metadata_line(line)
            or is_technology_line(line)
            or is_url_line(line)
        ):

            current_block.append(line)
            continue

        # ====================================================
        # POSSIBLE NEW PROJECT TITLE
        # ====================================================

        if (
            current_block
            and len(current_block) >= 2
            and looks_like_project_title(line)
        ):

            blocks.append(current_block)

            current_block = [line]

            continue

        # ====================================================
        # NORMAL DESCRIPTION LINE
        # ====================================================

        current_block.append(line)

    # --------------------------------------------------------
    # Final block
    # --------------------------------------------------------

    if current_block:
        blocks.append(current_block)

    # --------------------------------------------------------
    # Remove empty blocks
    # --------------------------------------------------------

    blocks = [
        block
        for block in blocks
        if block
    ]

    return blocks