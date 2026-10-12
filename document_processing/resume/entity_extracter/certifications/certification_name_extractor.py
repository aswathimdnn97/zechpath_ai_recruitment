import re

from document_processing.resume.entity_extracter.certifications.organization_extractor import (
    split_organization_suffix,
)


# ============================================================
# PATTERNS
# ============================================================

YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)

STATUS_PATTERN = re.compile(
    r"\b(?:completed|complete|passed|attained|"
    r"received|achieved|obtained|earned)\b",
    re.IGNORECASE,
)

KNOWN_ORG_PATTERN = re.compile(
    r"\b(?:"
    r"microsoft"
    r"|google\s+cloud"
    r"|google"
    r"|coursera"
    r"|deep\s*learning\s*\.?\s*ai"
    r"|deeplearning\s*\.?\s*ai"
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

    Returns:
        str
    """
    if not isinstance(text, str):
        return ""

    text = text.strip()

    if not text:
        return ""

    # Normalize PDF dash characters.
    text = text.replace("\u2013", "-")  # en dash
    text = text.replace("\u2014", "-")  # em dash
    text = text.replace("\u2212", "-")  # minus sign

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
    if not text:
        return ""

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
    if not text:
        return ""

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
    if not text:
        return ""

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
            ->
        Python for Everybody

        AWS Developer - Amazon Web Services
            ->
        AWS Developer
    """
    if not text:
        return ""

    suffix = split_organization_suffix(text)
    if suffix:
        text = suffix[0]

    organization_pattern = (
        r"(?:"
        r"microsoft"
        r"|google\s+cloud"
        r"|google"
        r"|coursera"
        r"|deep\s*learning\s*\.?\s*ai"
        r"|deeplearning\s*\.?\s*ai"
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
    if not text:
        return ""

    text = re.sub(
        r"^[\s•●▪◦*\-]+",
        "",
        text,
    )

    return _clean_text(text)


# ============================================================
# METADATA DETECTION
# ============================================================

def _is_metadata_line(line):
    """
    Determine whether a line is obvious certification metadata.
    """
    if not isinstance(line, str):
        return False

    line = line.strip()

    if not line:
        return False

    return bool(
        re.match(
            r"^(?:"
            r"issued|issue date|issued date|issued on|"
            r"expiration|expiration date|expiry|expiry date|"
            r"expires|valid until|valid through|"
            r"credential id|credential number|credential no|"
            r"certificate id|certificate number|certificate no|"
            r"certification id|certification number|certification no|"
            r"cert id|cert number|cert no"
            r")\b",
            line,
            flags=re.IGNORECASE,
        )
    )


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

    if isinstance(block, str):
        lines = [block]

    elif isinstance(block, (list, tuple)):
        lines = list(block)

    else:
        return None

    cleaned_lines = []

    for line in lines:
        line = _clean_text(line)

        if not line:
            continue

        cleaned_lines.append(line)

    if not cleaned_lines:
        return None

    # ========================================================
    # IMPORTANT
    #
    # The certification splitter creates logical blocks.
    #
    # Therefore the FIRST meaningful non-metadata line is
    # normally the certification name.
    # ========================================================

    candidate = None

    for line in cleaned_lines:

        # ----------------------------------------------------
        # Skip status-only lines.
        # ----------------------------------------------------

        if STATUS_PATTERN.fullmatch(line):
            continue

        # ----------------------------------------------------
        # Skip obvious metadata.
        # ----------------------------------------------------

        if _is_metadata_line(line):
            continue

        # ----------------------------------------------------
        # Skip standalone years.
        # ----------------------------------------------------

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

    text = _remove_leading_bullets(text)

    text = _remove_status(text)

    text = _remove_certificate_wrapper(text)

    text = _remove_years(text)

    text = _remove_organization(text)

    # Normalize slash formatting but PRESERVE slash.
    #
    # Example:
    #
    # Python / Domain Certification
    #
    # remains:
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

    # Must contain at least one alphabetic character.
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


# ============================================================
# MANUAL TEST
# ============================================================

if __name__ == "__main__":

    test_blocks = [
        [
            "Python / Domain Certification",
            "Completed",
        ],
        [
            "Professional Development Program",
            "Completed",
        ],
        [
            "AWS Certified Developer",
            "Amazon Web Services",
            "Issued: 2024",
        ],
        [
            "Python for Everybody - Coursera",
        ],
    ]

    print("\nCERTIFICATION NAME TESTS")
    print("=" * 60)

    for index, block in enumerate(
        test_blocks,
        start=1,
    ):
        result = extract_certification_name(block)

        print(f"\nTEST {index}")
        print("INPUT :", block)
        print("OUTPUT:", result)