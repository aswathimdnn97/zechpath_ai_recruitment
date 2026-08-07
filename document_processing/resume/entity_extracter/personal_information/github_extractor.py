import re


GITHUB_PATTERN = re.compile(
    r"(https?://)?(www\.)?github\.com/[^\s]+",
    re.IGNORECASE
)


def extract_github(text):

    match = GITHUB_PATTERN.search(text)

    if match:
        return match.group()

    return None