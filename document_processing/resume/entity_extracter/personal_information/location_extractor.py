import re


def _looks_like_contact_line(line):
    lower = line.lower()

    if "@" in line:
        return True

    if "linkedin.com" in lower:
        return True

    if "github.com" in lower:
        return True

    if re.search(r"\+?\d{1,3}[\s.-]?\d{5}[\s.-]?\d{5}", line):
        return True

    return False


def extract_location(text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines[:10]:

        if "," not in line:
            continue

        if line.count("|") >= 2:
            location_part = line.split("|")[0].strip()
            if location_part and "," in location_part:
                return location_part

        if _looks_like_contact_line(line):
            continue

        return line

    return None