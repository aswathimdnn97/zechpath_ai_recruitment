import re


# ============================================================
# Patterns
# ============================================================

PROJECT_LABEL_PATTERN = re.compile(
    r"^\s*project(?:\s*name)?\s*[:\-]\s*(.+)$",
    re.IGNORECASE,
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


def is_project_label(line):
    """
    Check whether a line explicitly identifies a project.
    """

    return bool(PROJECT_LABEL_PATTERN.match(line))


def extract_project_name_from_label(line):
    """
    Extract project name from an explicit project label.
    """

    match = PROJECT_LABEL_PATTERN.match(line)

    if not match:
        return None

    return match.group(1).strip()


def looks_like_project_title(line):
    """
    Heuristic to identify a project title.

    Project titles are generally short and don't look like
    normal descriptive sentences.
    """

    if not line:
        return False

    # Too long → probably description
    if len(line) > 80:
        return False

    # Description-like sentence
    if line.endswith((".", "!", "?")):
        return False

    words = line.split()

    # Very long text is unlikely to be a title
    if len(words) > 10:
        return False

    # Common description starters
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
        "implemented ",
    )

    if line.lower().startswith(description_starters):
        return False

    return True


# ============================================================
# Main splitter
# ============================================================

def split_project_blocks(section):
    """
    Split a PROJECTS section into individual project blocks.

    Supports:

        list[str]

    and:

        list[list[str]]

    Parameters
    ----------
    section : list[str] | list[list[str]] | str

    Returns
    -------
    list[list[str]]
    """

    if not section:
        return []

    # --------------------------------------------------------
    # Convert input into a flat list of lines
    # --------------------------------------------------------

    if isinstance(section, str):

        raw_lines = section.splitlines()

    elif isinstance(section, list):

        # Handle nested list:
        #
        # [
        #     [
        #         "Project 1",
        #         "...",
        #         "Project 2"
        #     ]
        # ]
        #
        if all(isinstance(item, list) for item in section):

            raw_lines = []

            for group in section:
                raw_lines.extend(group)

        else:

            raw_lines = section

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
    # Split projects
    # --------------------------------------------------------

    blocks = []
    current_block = []

    for line in lines:

        # ----------------------------------------------------
        # Explicit Project: label
        # ----------------------------------------------------

        if is_project_label(line):

            if current_block:
                blocks.append(current_block)

            current_block = []

            project_name = extract_project_name_from_label(line)

            if project_name:
                current_block.append(project_name)

            continue

        # ----------------------------------------------------
        # Detect a new project title
        # ----------------------------------------------------

        if (
            current_block
            and looks_like_project_title(line)
            and len(current_block) >= 2
        ):
            blocks.append(current_block)
            current_block = [line]
            continue

        # ----------------------------------------------------
        # Normal content
        # ----------------------------------------------------

        current_block.append(line)

    # --------------------------------------------------------
    # Add final block
    # --------------------------------------------------------

    if current_block:
        blocks.append(current_block)

    return blocks