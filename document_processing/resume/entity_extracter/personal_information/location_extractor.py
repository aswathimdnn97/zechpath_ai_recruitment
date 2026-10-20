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

LOCATION_LABEL_PATTERN = re.compile(
    r"^\s*(?:(?:current|present)\s+)?"
    r"(?:location|address|based\s+in|city)\s*:\s*",
    re.IGNORECASE,
)

KNOWN_LOCATIONS_PATTERN = re.compile(
    r"\b(?:india|kerala|karnataka|tamil nadu|maharashtra|"
    r"delhi|bangalore|bengaluru|hyderabad|chennai|kochi|"
    r"pune|mumbai|thrissur|kozhikode|calicut|kannur|"
    r"palakkad|trivandrum|thiruvananthapuram)\b",
    re.IGNORECASE,
)

PHONE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?:\+\d{1,3}[\s.-]?)?"
    r"[0-9Xx]{5}[\s.-]?[0-9Xx]{5}"
    r"(?![A-Za-z0-9])"
)


def _normalize_location_text(value):
    """Remove location labels and surrounding separators."""
    if not isinstance(value, str):
        return None

    value = value.strip()
    value = LOCATION_LABEL_PATTERN.sub("", value)
    value = value.strip(" \t,|;-")

    return value or None


def _is_title_or_contact_fragment(part):
    """Reject contact details and job-title fragments."""
    if not part:
        return True

    lower = part.casefold()

    if "@" in part:
        return True

    if any(
        domain in lower
        for domain in ("linkedin.com", "github.com")
    ):
        return True

    if PHONE_PATTERN.search(part):
        return True

    if re.search(
        r"\b(?:"
        + "|".join(
            re.escape(word)
            for word in sorted(TITLE_KEYWORDS, key=len, reverse=True)
        )
        + r")\b",
        lower,
    ):
        return True

    return False


def _is_location_candidate(part):
    """Return True when the cleaned text resembles a location."""
    part = _normalize_location_text(part)

    if not part:
        return False

    if _is_title_or_contact_fragment(part):
        return False

    # Avoid accepting a whole contact line as a location.
    if "@" in part or PHONE_PATTERN.search(part):
        return False

    # Known city/state/country names.
    if KNOWN_LOCATIONS_PATTERN.search(part):
        return True

    # Generic City, State or City, State, Country format.
    return bool(
        re.fullmatch(
            r"[A-Za-z][A-Za-z\s.-]+,\s*"
            r"[A-Za-z][A-Za-z\s.-]+"
            r"(?:,\s*[A-Za-z][A-Za-z\s.-]+)?",
            part,
        )
    )


def _looks_like_contact_line(line):
    lower = line.casefold()

    return (
        "@" in line
        or "linkedin.com" in lower
        or "github.com" in lower
        or bool(PHONE_PATTERN.search(line))
    )


def extract_location(text):
    """
    Extract a location from the resume's contact/header area.

    Returns a cleaned location without labels such as 'Location:'.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Prioritize explicitly labelled location values.
    for line in lines[:20]:
        labelled = LOCATION_LABEL_PATTERN.match(line)

        if labelled:
            value = _normalize_location_text(line)

            # Handle: Location: Thrissur, Kerala | Phone: ...
            if value:
                value = re.split(
                    r"\s+\|\s+|\s+(?=(?:phone|email|mobile)\s*:)",
                    value,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0].strip()

            if _is_location_candidate(value):
                return value

    # Next, inspect header lines with pipe-separated contact details.
    for line in lines[:15]:
        parts = re.split(r"\s*\|\s*", line)

        for part in parts:
            value = _normalize_location_text(part)

            if _is_location_candidate(value):
                return value

        # Do not treat an entire contact line as a location.
        if _looks_like_contact_line(line):
            continue

        value = _normalize_location_text(line)

        if _is_location_candidate(value):
            return value

    return None
