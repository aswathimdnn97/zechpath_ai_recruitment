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

    text = " ".join(
        block
    )

    text = re.sub(
        r"\(\s*(19|20)\d{2}\s*\)",
        "",
        text
    )

    text = re.sub(
        r"\s*[—–-]\s*"
        r"[^—–()-]+"
        r"\s*(?:\(\s*(19|20)\d{2}\s*\))?$",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )
    # Remove punctuation separators and normalize slashes/pipes
    text = re.sub(r"[—–-]", " ", text)
    text = re.sub(r"\s*(?:/|\|)\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # If a known organization appears at or near the end, strip it off.
    matches = list(KNOWN_ORG_PATTERN.finditer(text))
    if matches:
        last = matches[-1]
        # if the last match ends within the final 6 characters or at the end,
        # treat it as a trailing organization and remove from its start.
        if last.end() >= len(text) - 6:
            text = text[: last.start()].strip()

    return text