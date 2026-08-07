
def parse_document(text, headings):

    sections = {"header": []}
    current_section = "header"

    lines = text.split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if line in headings:
            current_section = line
            sections[current_section] = []

        else:
            sections[current_section].append(line)

    return sections