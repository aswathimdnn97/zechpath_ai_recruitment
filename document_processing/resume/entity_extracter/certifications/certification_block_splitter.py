"""
certification_block_splitter.py

Split a certification section into logical certification blocks.

Example input:

[
    "AWS Certified Solutions Architect - Associate",
    "Amazon Web Services",
    "Issued: March 2024",
    "Credential ID: AWS123",
    "Microsoft Certified: Azure Fundamentals",
    "Microsoft",
    "Issued: 2023",
]

Expected output:

[
    [
        "AWS Certified Solutions Architect - Associate",
        "Amazon Web Services",
        "Issued: March 2024",
        "Credential ID: AWS123",
    ],
    [
        "Microsoft Certified: Azure Fundamentals",
        "Microsoft",
        "Issued: 2023",
    ],
]
"""

import re


# ============================================================
# PATTERNS
# ============================================================

YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)


YEAR_RANGE_PATTERN = re.compile(
    r"""
    \b
    (?:19|20)\d{2}
    \s*
    [-–—]
    \s*
    (?:
        (?:19|20)\d{2}
        |
        present
        |
        current
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# BASIC CLEANING
# ============================================================

def clean_line(line):
    """
    Clean one certification line.

    Returns:
        str | None
    """

    if not isinstance(line, str):
        return None

    line = line.strip()

    if not line:
        return None

    return line


# ============================================================
# SPLIT LONG CERTIFICATION LINE
# ============================================================

def split_long_certification_line(line):
    """
    Split a long line when multiple certifications are
    separated by em dash / en dash.

    Example:

        AWS Certified Developer — Microsoft Certified Azure

    becomes:

        [
            "AWS Certified Developer",
            "Microsoft Certified Azure"
        ]
    """

    if not isinstance(line, str):
        return [line]

    parts = re.split(
        r"\s+[—–]\s+",
        line
    )

    if len(parts) <= 1:
        return [line]

    cleaned_parts = [
        part.strip()
        for part in parts
        if part.strip()
    ]

    if len(cleaned_parts) <= 1:
        return [line]

    return cleaned_parts


# ============================================================
# CERTIFICATION START DETECTION
# ============================================================

def is_certification_start(line):
    """
    Determine whether a line looks like the beginning
    of a certification record.

    Strong signals:

        Certified
        Certification
        Certificate
        License
        Licence

    Secondary signals:

        Associate
        Specialist
        Professional
        Fundamentals
        Specialization
    """

    if not isinstance(line, str):
        return False

    line = line.strip()

    if not line:
        return False

    lower = line.lower()

    # ========================================================
    # Metadata lines are NOT certification starts
    # ========================================================

    metadata_prefixes = (
        "issued:",
        "issue date:",
        "issued date:",
        "issued on:",
        "expiration:",
        "expires:",
        "expiry:",
        "expiration date:",
        "expiry date:",
        "expiration on:",
        "credential id:",
        "credential number:",
        "credential no:",
        "certification id:",
        "certification number:",
        "certification no:",
        "certificate id:",
        "certificate number:",
        "certificate no:",
        "cert id:",
        "cert number:",
        "cert no:",
    )

    if lower.startswith(metadata_prefixes):
        return False

    # ========================================================
    # Standalone year is NOT certification start
    # ========================================================

    if re.fullmatch(
        r"(?:19|20)\d{2}",
        line
    ):
        return False

    # ========================================================
    # Date range is NOT certification start
    # ========================================================

    if YEAR_RANGE_PATTERN.fullmatch(line):
        return False

    # ========================================================
    # Explicit certification keywords
    #
    # Strongest signal.
    # ========================================================

    certification_keywords = (
        "certified",
        "certification",
        "certificate",
        "license",
        "licence",
    )

    if any(
        keyword in lower
        for keyword in certification_keywords
    ):
        return True

    # ========================================================
    # Secondary certification indicators
    # ========================================================

    certification_indicators = (
        "associate",
        "specialist",
        "professional",
        "fundamentals",
        "specialization",
    )

    if any(
        indicator in lower
        for indicator in certification_indicators
    ):

        words = line.split()

        # Avoid very short random lines
        if len(words) >= 2:
            return True

    return False


# ============================================================
# NORMALIZE INPUT
# ============================================================

def normalize_certification_input(
    certification_section
):
    """
    Normalize certification input.

    Supports:

        "line1\\nline2"

    and:

        ["line1", "line2"]

    and:

        [
        ["line1", "line2"],
        ["line3", "line4"]
        ]

    Returns:

        [
            ["certification line", "organization", ...],
            [...]
        ]
    """

    if not certification_section:
        return []

    # ========================================================
    # STRING INPUT
    # ========================================================

    if isinstance(
        certification_section,
        str
    ):

        lines = []

        for line in certification_section.splitlines():

            line = clean_line(line)

            if line:
                lines.extend(
                    split_long_certification_line(
                        line
                    )
                )

        return split_flat_certification_lines(
            lines
        )

    # ========================================================
    # MUST BE LIST
    # ========================================================

    if not isinstance(
        certification_section,
        list
    ):
        return []

    # ========================================================
    # BLOCK STRUCTURED INPUT
    # ========================================================

    if all(
        isinstance(item, list)
        for item in certification_section
    ):

        blocks = []

        for block in certification_section:

            cleaned_block = []

            for line in block:

                line = clean_line(line)

                if line:

                    cleaned_block.extend(
                        split_long_certification_line(
                            line
                        )
                    )

            if cleaned_block:

                sub_blocks = (
                    split_flat_certification_lines(
                        cleaned_block
                    )
                )

                blocks.extend(
                    sub_blocks
                )

        return blocks

    # ========================================================
    # FLAT LIST
    # ========================================================

    lines = []

    for item in certification_section:

        line = clean_line(item)

        if line:

            lines.extend(
                split_long_certification_line(
                    line
                )
            )

    return split_flat_certification_lines(
        lines
    )


# ============================================================
# FLAT LIST SPLITTER
# ============================================================

def split_flat_certification_lines(lines):
    """
    Split flat certification lines into logical blocks.

    A new certification starts whenever
    is_certification_start() returns True
    and a previous block already exists.
    """

    if not lines:
        return []

    blocks = []

    current_block = []

    for line in lines:

        # ====================================================
        # NEW CERTIFICATION
        # ====================================================

        if (
            is_certification_start(line)
            and current_block
        ):

            blocks.append(
                current_block
            )

            current_block = []

        current_block.append(line)

    # ========================================================
    # FINAL BLOCK
    # ========================================================

    if current_block:

        blocks.append(
            current_block
        )

    return blocks


# ============================================================
# MERGE ORGANIZATION-ONLY BLOCKS
# ============================================================

def _merge_org_only_blocks(blocks):
    """
    Merge organization-only blocks into the previous
    certification block.

    Example:

        [
            ["AWS Certified Developer"],
            ["Amazon Web Services"]
        ]

    becomes:

        [
            [
                "AWS Certified Developer",
                "Amazon Web Services"
            ]
        ]
    """

    if not blocks:
        return []

    ORG_HINT = re.compile(
        r"""
        \b
        (?:
            amazon\s+web\s+services
            |
            aws
            |
            microsoft
            |
            google\s+cloud
            |
            google
            |
            coursera
            |
            deep\s*learning\.ai
            |
            tensorflow
            |
            ibm
            |
            oracle
            |
            cisco
            |
            comptia
            |
            meta
            |
            accenture
        )
        \b
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    merged = []

    for block in blocks:

        # ----------------------------------------------------
        # Single organization line
        # ----------------------------------------------------

        if (
            len(block) == 1
            and ORG_HINT.search(block[0])
            and merged
            and not is_certification_start(block[0])
        ):

            merged[-1].extend(
                block
            )

        else:

            merged.append(
                block
            )

    return merged


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def split_certification_blocks(
    certification_section
):
    """
    Public certification block splitter.

    Returns:

        [
            [
                "AWS Certified Developer",
                "Amazon Web Services",
                "Issued: 2024"
            ],
            [
                "Microsoft Certified Azure",
                "Microsoft",
                "Issued: 2023"
            ]
        ]
    """

    blocks = normalize_certification_input(
        certification_section
    )

    blocks = _merge_org_only_blocks(
        blocks
    )

    return blocks


# ============================================================
# MANUAL TEST
# ============================================================

if __name__ == "__main__":

    section = [
        "AWS Certified Solutions Architect - Associate",
        "Amazon Web Services",
        "Issued: March 2024",
        "Credential ID: AWS123",
        "Microsoft Certified: Azure Fundamentals",
        "Microsoft",
        "Issued: 2023",
    ]

    result = split_certification_blocks(
        section
    )

    print("\nRESULT:")
    print(result)

    print("\nBLOCK COUNT:")
    print(len(result))

    for index, block in enumerate(
        result,
        start=1
    ):

        print(
            f"\nBLOCK {index}:"
        )

        for line in block:
            print(
                f"  {line}"
            )
