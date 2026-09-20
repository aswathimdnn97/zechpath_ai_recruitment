import re


# ============================================================
# PATTERNS
# ============================================================

YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)


STATUS_PATTERN = re.compile(
    r"\b(?:completed|complete|passed|attained|"
    r"received|achieved|obtained)\b",
    re.IGNORECASE,
)


KNOWN_ORG_PATTERN = re.compile(
    r"\b(?:"
    r"microsoft"
    r"|google\s+cloud"
    r"|google"
    r"|coursera"
    r"|deep\s*learning\.ai"
    r"|deeplearning\.ai"
    r"|tensorflow"
    r"|ibm"
    r"|amazon\s+web\s+services"
    r"|aws"
    r"|udemy"
    r"|oracle"
    r"|cisco"
    r"|comptia"
    r"|meta"
    r"|udacity"
    r"|linkedin\s+learning"
    r"|pluralsight"
    r"|edx"
    r"|simplilearn"
    r")\b",
    re.IGNORECASE,
)


# ============================================================
# CLEANING HELPERS
# ============================================================

def _clean_text(text):
    """
    Basic text normalization.
    """

    if not isinstance(text, str):
        return ""

    text = text.strip()

    if not text:
        return ""

    # Normalize PDF dash characters.
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "-")
    text = text.replace("\u2212", "-")

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _remove_status(text):
    """
    Remove completion/status words.

    Examples:

        Python Certification Completed
            ->
        Python Certification

        Professional Development Program - Completed
            ->
        Professional Development Program
    """

    text = STATUS_PATTERN.sub(
        " ",
        text,
    )

    # Remove dangling separators left behind.
    text = re.sub(
        r"\s*[-|:;,]\s*$",
        "",
        text,
    )

    text = re.sub(
        r"^\s*[-|:;,]\s*",
        "",
        text,
    )

    return _clean_text(text)


def _remove_certificate_wrapper(text):
    """
    Remove generic wrappers when they are used as prefixes.

    Examples:

        Certificate: Python Basics
            ->
        Python Basics

        Certification - Python Basics
            ->
        Python Basics

    But:

        Python / Domain Certification
            ->
        Python / Domain Certification

    because 'Certification' is part of the actual title.
    """

    text = re.sub(
        r"^\s*(?:certificate|certification|certified)"
        r"\s*[:\-]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return _clean_text(text)


def _remove_years(text):
    """
    Remove parenthesized or trailing years.

    Examples:

        Python Certificate (2024)
            ->
        Python Certificate

        Python Certificate 2024
            ->
        Python Certificate
    """

    # Parenthesized year.
    text = re.sub(
        r"\(\s*(?:19|20)\d{2}\s*\)",
        "",
        text,
    )

    # Trailing year.
    text = re.sub(
        r"\s+(?:19|20)\d{2}\s*$",
        "",
        text,
    )

    return _clean_text(text)


def _remove_organization(text):
    """
    Remove a known issuing organization when it appears
    as a suffix.

    Examples:

        Python for Everybody - Coursera
            -> Python for Everybody

        AWS Developer - Amazon Web Services
            -> AWS Developer
    """

    organization_pattern = (
        r"(?:"
        r"microsoft"
        r"|google\s+cloud"
        r"|google"
        r"|coursera"
        r"|deep\s*learning\.ai"
        r"|deeplearning\.ai"
        r"|tensorflow"
        r"|ibm"
        r"|amazon\s+web\s+services"
        r"|aws"
        r"|udemy"
        r"|oracle"
        r"|cisco"
        r"|comptia"
        r"|meta"
        r"|udacity"
        r"|linkedin\s+learning"
        r"|pluralsight"
        r"|edx"
        r"|simplilearn"
        r")"
    )

    # Organization after -, | or :
    text = re.sub(
        rf"\s*[-|:]\s*{organization_pattern}"
        rf"(?:\s*\(\s*(?:19|20)\d{{2}}\s*\))?"
        rf"\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return _clean_text(text)


def _remove_leading_bullets(text):
    """
    Remove PDF bullet characters.
    """

    text = re.sub(
        r"^[\s•●▪◦*-]+",
        "",
        text,
    )

    return _clean_text(text)


# ============================================================
# MAIN EXTRACTOR
# ============================================================

def extract_certification_name(block):
    """
    Extract the certification name from a certification block.

    Examples
    --------

    Input:
        [
            "Python / Domain Certification",
            "Completed"
        ]

    Output:
        "Python / Domain Certification"


    Input:
        [
            "Professional Development Program",
            "Completed"
        ]

    Output:
        "Professional Development Program"


    Input:
        [
            "AWS Certified Developer",
            "Amazon Web Services",
            "Issued: 2024"
        ]

    Output:
        "AWS Certified Developer"


    Input:
        [
            "Python for Everybody - Coursera"
        ]

    Output:
        "Python for Everybody"
    """

    if not block:
        return None

    # ========================================================
    # Normalize block
    # ========================================================

    if isinstance(
        block,
        str,
    ):
        lines = [block]

    elif isinstance(
        block,
        list,
    ):
        lines = block

    else:
        return None

    cleaned_lines = []

    for line in lines:

        line = _clean_text(line)

        if not line:
            continue

        cleaned_lines.append(
            line
        )

    if not cleaned_lines:
        return None

    # ========================================================
    # IMPORTANT:
    #
    # The certification splitter now creates logical blocks.
    #
    # Therefore the FIRST meaningful non-metadata line is
    # normally the certification name.
    # ========================================================

    candidate = None

    for line in cleaned_lines:

        # Skip status-only lines.
        if STATUS_PATTERN.fullmatch(
            line
        ):
            continue

        # Skip obvious metadata.
        if re.match(
            r"^(?:"
            r"issued|issue date|issued date|issued on|"
            r"expiration|expiration date|expiry|expiry date|"
            r"expires|valid until|valid through|"
            r"credential id|credential number|credential no|"
            r"certificate id|certificate number|certificate no|"
            r"certification id|certification number|certification no"
            r")\b",
            line,
            flags=re.IGNORECASE,
        ):
            continue

        # Skip standalone years.
        if re.fullmatch(
            r"(?:19|20)\d{2}",
            line,
        ):
            continue

        candidate = line
        break

    if not candidate:
        return None

    # ========================================================
    # Clean candidate
    # ========================================================

    text = candidate

    text = _remove_leading_bullets(
        text
    )

    text = _remove_status(
        text
    )

    text = _remove_certificate_wrapper(
        text
    )

    text = _remove_years(
        text
    )

    text = _remove_organization(
        text
    )

    # Normalize slash formatting but PRESERVE slash.
    #
    # Example:
    #
    # Python / Domain Certification
    #
    # should remain:
    #
    # Python / Domain Certification
    text = re.sub(
        r"\s*/\s*",
        " / ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    # Remove trailing punctuation.
    text = re.sub(
        r"[,:;|]+$",
        "",
        text,
    ).strip()

    # ========================================================
    # Validation
    # ========================================================

    if not text:
        return None

    if not any(
        character.isalpha()
        for character in text
    ):
        return None

    # Reject only truly generic names.
    generic_names = {
        "associate",
        "professional",
        "specialist",
        "fundamentals",
        "specialization",
        "specialisation",
        "certificate",
        "certification",
        "certified",
        "license",
        "licence",
    }

    if text.lower() in generic_names:
        return None

    return text