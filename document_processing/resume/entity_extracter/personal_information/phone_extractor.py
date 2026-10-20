import re


# Supports:
# 9876543210
# 98765 43210
# 98765-43210
# +91 98765 43210
# +91-98765-43210
# +91 900XX 12345
# +91 900xx 12345
# Phone: 900XX12345

# for testing phone pattern
PHONE_PATTERN = re.compile(
    r"""
    (?<![A-Za-z0-9])
    (?P<phone>
        (?:\+\d{1,3}[\s.-]?)?
        [0-9Xx]{5}
        [\s.-]?
        [0-9Xx]{5}
    )
    (?![A-Za-z0-9])
    """,
    re.VERBOSE,
)

# for production phone pattern
# PHONE_PATTERN = re.compile(
#     r"""
#     (?<![A-Za-z0-9])
#     (?P<phone>
#         (?:\+\d{1,3}[\s.-]?)?
#         (?:\(\d{2,4}\)[\s.-]?)?
#         \d(?:[\s.-]?\d){6,14}
#     )
#     (?![A-Za-z0-9])
#     """,
#     re.VERBOSE,
# )


def extract_phone(text):
    """
    Extract a phone number, including masked test numbers.

    Returns:
        str | None
    """
    if not isinstance(text, str) or not text.strip():
        return None

    match = PHONE_PATTERN.search(text)

    if not match:
        return None

    phone = match.group("phone").strip()

    # Normalize repeated whitespace while preserving X masking.
    phone = re.sub(r"\s+", " ", phone)

    return phone
