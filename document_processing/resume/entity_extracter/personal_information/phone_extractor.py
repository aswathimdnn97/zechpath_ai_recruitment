import re


PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[- ]?)?(?:\d{10})"
)


def extract_phone(text):

    match = PHONE_PATTERN.search(text)

    if match:
        return match.group()

    return None