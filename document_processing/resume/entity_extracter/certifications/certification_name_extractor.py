import re


YEAR_PATTERN = re.compile(
    r"\b(19|20)\d{2}\b"
)


KNOWN_ORG_PATTERN = re.compile(
    r"(?:\b(microsoft|google\s+cloud|coursera|deep\s*learning\.ai|tensorflow|ibm)\b)",
    re.IGNORECASE,
)


def extract_certification_name(block):

    if not block:
        return None

    text = " ".join(block)

    # Remove parenthesized years and trailing standalone years.
    text = re.sub(r"\(\s*(?:19|20)\d{2}\s*\)", "", text)
    text = re.sub(r"\b(?:19|20)\d{2}\b(?=\s*$)", "", text).strip()

    # Remove trailing organization-like fragments after a dash/pipe/semicolon.
    text = re.sub(
        r"\s*[—–-]\s*[^—–()-]+\s*(?:\(\s*(?:19|20)\d{2}\s*\))?$",
        "",
        text,
    )

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[—–-]", " ", text)
    text = re.sub(r"\s*(?:/|\|)\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # If a known organization appears at or near the end, strip it off.
    matches = list(KNOWN_ORG_PATTERN.finditer(text))
    if matches:
        last = matches[-1]
        if last.end() >= len(text) - 6:
            text = text[: last.start()].strip()

    if not text:
        return None

    # Strip a trailing standalone year that may have been appended to the title.
    text = re.sub(r"\s+\b(?:19|20)\d{2}\b\s*$", "", text).strip()

    if not text:
        return None

    generic_names = {
        "associate",
        "professional",
        "specialist",
        "fundamentals",
        "specialization",
        "certificate",
        "certification",
        "certified",
    }
    if text.lower() in generic_names:
        return None

    return text