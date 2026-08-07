import re

LINKEDIN_PATTERN = re.compile(
    r"(https?://)?(www\.)?linkedin\.com/[^\s]+",
    re.IGNORECASE
)

def extract_linkedin(text):

    match = LINKEDIN_PATTERN.search(text)

    if match:
        return match.group()

    return None