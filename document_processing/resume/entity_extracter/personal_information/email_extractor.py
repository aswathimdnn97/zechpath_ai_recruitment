import re


# ---------------------------------------------------------
# Email pattern
# ---------------------------------------------------------
# Supports:
#   arjun@example.com
#   arjun.menon@example.com
#   arjun_menon@example.co.in
#   arjun-menon+work@example.org
#
# The dot before the domain extension is escaped as \.
# so it means an actual dot.
# ---------------------------------------------------------

EMAIL_PATTERN = re.compile(
    r"""
    (?<![\w.-])
    [A-Za-z0-9]
    [A-Za-z0-9._%+-]*
    @
    [A-Za-z0-9-]+
    (?:\.[A-Za-z0-9-]+)+
    (?![\w.-])
    """,
    re.IGNORECASE | re.VERBOSE,
)


def extract_email(text):
    """
    Extract the first valid email address from text.

    Returns:
        str | None
    """

    if not text:
        return None

    match = EMAIL_PATTERN.search(
        text
    )

    if not match:
        return None

    email = match.group(0)

    # Remove accidental punctuation that may
    # come from the resume text.
    email = email.rstrip(
        ".,;:)]}"
    )

    return email
