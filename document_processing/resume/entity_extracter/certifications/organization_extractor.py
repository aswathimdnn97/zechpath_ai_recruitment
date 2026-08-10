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
    """,
    re.IGNORECASE | re.VERBOSE
)


def extract_issuing_organization(
    block
):

    if not block:
        return None
    # Prefer lines after the title (commonly the second line contains org)
    if isinstance(block, list) and len(block) > 1:

        for line in block[1:]:

            if not line or not isinstance(line, str):
                continue

            organization = line.strip()

            # remove common prefixes like 'Issued:'
            organization = re.sub(r"^Issued:\s*", "", organization, flags=re.I)

            # remove year in parentheses
            organization = re.sub(r"\(\s*(19|20)\d{2}\s*\)", "", organization).strip()

            if not organization:
                continue

            # If the line contains multiple orgs separated by '/', keep full cleaned line
            if "/" in organization:
                return organization

            # If line matches a known organization keyword, return the cleaned line
            if KNOWN_ORGANIZATION_PATTERN.search(organization):
                return organization

            # As a fallback, short lines (few words) after the title are likely org names
            if len(organization.split()) <= 5:
                return organization

    # Generic fallback: look after em dash in the whole block text
    text = " ".join(block) if isinstance(block, list) else str(block)

    parts = re.split(r"\s*[—–]\s*", text, maxsplit=1)

    if len(parts) == 2:

        organization = parts[1]

        organization = re.sub(r"\(\s*(19|20)\d{2}\s*\)", "", organization)

        organization = organization.strip()

        if organization:
            return organization

    return None