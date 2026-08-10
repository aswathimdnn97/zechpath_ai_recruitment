import re


# ---------------------------------------------------------
# Phone number pattern
# ---------------------------------------------------------
#
# Supports examples such as:
#
# 9876543210
# 98765 43210
# 98765-43210
# +91 98765 43210
# +91-98765-43210
# +91 9876543210
# 91 98765 43210
#
# ---------------------------------------------------------

PHONE_PATTERN = re.compile(
    r"""
    (?<!\d)

    # Optional country code
    (?:
        \+?\d{1,3}
        [\s.-]?
    )?

    # First part of phone number
    \d{5}

    # Optional separator
    [\s.-]?

    # Second part
    \d{5}

    (?!\d)
    """,
    re.VERBOSE,
)


def extract_phone(text):
    """
    Extract the first phone number from text.

    Returns:
        str | None
    """

    if not text:
        return None

    match = PHONE_PATTERN.search(
        text
    )

    if not match:
        return None

    phone = match.group(0).strip()

    # Normalize repeated whitespace.
    phone = re.sub(
        r"\s+",
        " ",
        phone,
    )

    return phone
