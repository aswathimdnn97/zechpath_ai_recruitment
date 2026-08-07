import re


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


def extract_email(text):

    match = EMAIL_PATTERN.search(text)

    if match:
        return match.group()

    return None