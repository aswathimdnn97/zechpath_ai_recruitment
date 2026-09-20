import re


def clean_resume_lines(text):
    if not isinstance(text, str):
        return []

    lines = []

    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()

        # Remove common PDF extraction noise.
        if not line or re.fullmatch(r"[\W_]*[A-Za-z]?[\W_]*", line):
            continue

        line = re.sub(r"^[•●▪◦*-]\s*", "", line)
        lines.append(line)

    return lines