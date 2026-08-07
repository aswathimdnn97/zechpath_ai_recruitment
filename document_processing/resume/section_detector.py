def detect_sections(text, headings):

    sections = {}
    current_section = None

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        # Heading already normalized
        if line.lower() in headings:

            current_section = line.lower()

            if current_section not in sections:
                sections[current_section] = []

            sections[current_section].append([])
            
            continue

        if current_section:
            sections[current_section][-1].append(line)

    return sections