import re

TITLE_KEYWORDS = {
    "developer",
    "engineer",
    "software",
    "intern",
    "fresher",
    "junior",
    "senior",
    "lead",
    "manager",
    "analyst",
    "architect",
    "consultant",
    "specialist",
    "student",
    "graduate",
    "trainee",
    "associate",
}


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


def _is_title_or_contact_fragment(part):
    part = part.strip()
    if not part:
        return True

    lower = part.lower()

    if "@" in part or "linkedin.com" in lower or "github.com" in lower:
        return True

    if re.search(r"\+?\d{1,3}[\s.-]?\d{5}[\s.-]?\d{5}", part):
        return True

    if re.search(r"\b(?:" + "|".join(sorted(TITLE_KEYWORDS, key=len, reverse=True)) + r")\b", lower):
        return True

    return False


def _is_location_candidate(part):
    part = part.strip()
    if not part or not "," in part:
        return False

    if _is_title_or_contact_fragment(part):
        return False

    if re.search(r"\b(?:india|kerala|karnataka|tamil nadu|maharashtra|delhi|bangalore|bengaluru|hyderabad|chennai|kochi|pune|mumbai)\b", part.lower()):
        return True

    # Accept generic city/state/country patterns like "Bengaluru, Karnataka"
    if re.search(r"^[A-Za-z][A-Za-z\s.-]+,\s*[A-Za-z][A-Za-z\s.-]+(?:,\s*[A-Za-z][A-Za-z\s.-]+)?$", part):
        return True

    return False


def extract_location(text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines[:15]:
        parts = [p.strip() for p in re.split(r"\s*\|\s*", line)]

        if len(parts) > 1:
            for part in parts:
                if _is_location_candidate(part):
                    return part

        if "," not in line:
            continue

        if _looks_like_contact_line(line):
            continue

        if _is_location_candidate(line):
            return line

    return None