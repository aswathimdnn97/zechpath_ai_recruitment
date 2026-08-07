import re

def fix_layout(text):
    """
    Clean layout issues while preserving document structure.

    - Remove extra spaces
    - Normalize tabs
    - Remove empty lines
    - Preserve one logical line per input line
    """

    if not text:
        return ""

    cleaned_lines = []

    for line in text.splitlines():

        # Replace tabs with spaces
        line = line.replace("\t", " ")

        # Collapse multiple spaces
        line = re.sub(r"\s+", " ", line).strip()

        # Skip empty lines
        if not line:
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)