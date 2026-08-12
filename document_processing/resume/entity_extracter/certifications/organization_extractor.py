import re


KNOWN_ORGANIZATION_PATTERN = re.compile(
    r"""
    microsoft
    |
    google\s+cloud
    |
    coursera
    |
    deep\s*learning\.ai
    |
    tensorflow
    |
    ibm
    |
    amazon\s+web\s+services
    |
    aws
    |
    oracle
    """,
    re.IGNORECASE | re.VERBOSE
)

DATE_ONLY_PATTERN = re.compile(
    r"""
    ^
    (?:
        (?:issued|issue\s+date|awarded|completed|completion\s+date|expires?|expiration|valid\s+until|valid\s+through)\s*[:\-]?\s*
    )?
    (?:(?:19|20)\d{2}|\d{1,2}[/-](?:19|20)\d{2}|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s*,?\s*(?:19|20)\d{2})
    $
    """,
    re.IGNORECASE | re.VERBOSE
)


def _infer_org_from_title(title):
    """Infer a likely issuing organization from a certification title."""
    if not title or not isinstance(title, str):
        return None

    normalized = title.strip()
    if not normalized:
        return None

    if re.search(r"\baws\b|amazon\s+web\s+services", normalized, re.IGNORECASE):
        return "Amazon Web Services"
    if re.search(r"\boracle\b", normalized, re.IGNORECASE):
        return "Oracle"
    if re.search(r"\bmicrosoft\b", normalized, re.IGNORECASE):
        return "Microsoft"
    if re.search(r"\bgoogle\s+cloud\b|\bgoogle\b", normalized, re.IGNORECASE):
        return "Google Cloud"
    if re.search(r"\bcoursera\b", normalized, re.IGNORECASE):
        return "Coursera"
    if re.search(r"\bdeep\s*learning\.ai\b", normalized, re.IGNORECASE):
        return "Deep Learning.AI"
    if re.search(r"\btensorflow\b", normalized, re.IGNORECASE):
        return "TensorFlow"
    if re.search(r"\bibm\b", normalized, re.IGNORECASE):
        return "IBM"
    return None


def extract_issuing_organization(
    block
):

    if not block:
        return None

    # Prefer lines after the title (commonly the second line contains org)
    if isinstance(block, list):
        for line in block[1:]:
            if not line or not isinstance(line, str):
                continue

            organization = line.strip()
            organization = re.sub(r"^Issued:\s*", "", organization, flags=re.I)
            organization = re.sub(r"\(\s*(19|20)\d{2}\s*\)", "", organization).strip()

            if not organization:
                continue

            if DATE_ONLY_PATTERN.fullmatch(organization):
                continue

            if "/" in organization:
                return organization

            if KNOWN_ORGANIZATION_PATTERN.search(organization):
                return organization

            if len(organization.split()) <= 5:
                return organization

    # Title-based fallback for organizations implied by the certification name itself.
    if isinstance(block, list) and block:
        title = block[0].strip()
        inferred = _infer_org_from_title(title)
        if inferred:
            return inferred

    text = " ".join(block) if isinstance(block, list) else str(block)
    parts = re.split(r"\s*[—–]\s*", text, maxsplit=1)

    if len(parts) == 2:
        organization = parts[1]
        organization = re.sub(r"\(\s*(19|20)\d{2}\s*\)", "", organization)
        organization = organization.strip()

        if not organization:
            return None
        if DATE_ONLY_PATTERN.fullmatch(organization):
            return None
        return organization

    return None