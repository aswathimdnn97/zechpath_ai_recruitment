def parse_document(text, headings):
    """
    Parse normalized JD text into sections.

    Args:
        text: Normalized JD text.
        headings: List/set of normalized section headings.

    Returns:
        Dictionary containing section names and their content.
    """

    sections = {}
    current_section = "header"

    sections[current_section] = []

    # Convert headings to a set for fast lookup
    heading_set = {
        str(heading).strip().lower()
        for heading in headings
    }

    lines = text.splitlines()

    for line in lines:

        line = line.strip()

        if not line:
            continue

        normalized_line = line.lower()

        # -----------------------------------------
        # Section heading
        # -----------------------------------------

        if normalized_line in heading_set:

            current_section = normalized_line

            if current_section not in sections:
                sections[current_section] = []

            continue

        # -----------------------------------------
        # Section content
        # -----------------------------------------

        sections[current_section].append(line)

    return sections