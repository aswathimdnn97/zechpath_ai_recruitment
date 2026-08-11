import re

def fix_layout(text, headings=None):
    """
    Clean layout issues while preserving document structure.

    - Remove extra spaces
    - Normalize tabs
    - Remove empty lines
    - Merge soft-wrapped continuation lines
    """

    if not text:
        return ""

    heading_set = {
        str(heading).strip().lower()
        for heading in headings
    } if headings else set()

    cleaned_lines = []
    pending_line = None

    for line in text.splitlines():

        # Replace tabs with spaces
        line = line.replace("\t", " ")

        # Collapse multiple spaces
        line = re.sub(r"\s+", " ", line).strip()

        # Skip empty lines
        if not line:
            if pending_line is not None:
                cleaned_lines.append(pending_line)
                pending_line = None
            continue

        if pending_line is None:
            pending_line = line
            continue

        if line in heading_set:
            cleaned_lines.append(pending_line)
            pending_line = line
            continue

        if (
            line[0].islower()
            and not pending_line.endswith((".", "!", "?", ":", ";"))
        ):
            pending_line = f"{pending_line} {line}"
            continue

        cleaned_lines.append(pending_line)
        pending_line = line

    if pending_line is not None:
        cleaned_lines.append(pending_line)

    return "\n".join(cleaned_lines)