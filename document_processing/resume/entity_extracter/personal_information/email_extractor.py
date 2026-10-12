import re


EMAIL_PATTERN = re.compile(
    r"""
    (?<![\w.-])
    [A-Za-z0-9]
    [A-Za-z0-9._%+-]*
    @
    [A-Za-z0-9-]+
    (?:\.[A-Za-z0-9-]+)+
    """,
    re.VERBOSE | re.IGNORECASE,
)


def extract_email(text):

    if not text:
        return None

    match = EMAIL_PATTERN.search(text)

    if not match:
        return None

    email = match.group(0)

    # Remove punctuation that may follow an email
    # in resume text.
    email = email.rstrip(
        ".,;:)]}"
    )

    return email