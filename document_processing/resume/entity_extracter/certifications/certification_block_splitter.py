"""
certification_block_splitter.py

Splits a detected certification section into logical
certification blocks.

Supported formats:

1. Standard multiline certification

    AWS Certified Developer
    Amazon Web Services
    Issued: 2024
    Credential ID: AWS123

2. Certification with completion status

    Python / Domain Certification       Completed
    Professional Development Program   Completed
    Workplace Communication             Completed

3. Flat certification lists

    AWS Certified Developer
    Microsoft Certified Azure
    Python Specialization

4. Provider-based certifications

    Python for Everybody - Coursera
    Django Web Development - Udemy

5. Nested section detector output

    [
        [
            "AWS Certified Developer",
            "Amazon Web Services",
            "2024"
        ]
    ]

6. Inline certifications

    Python Certification - Coursera;
    Django Certification - Udemy
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


MONTH_PATTERN = (
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|"
    r"apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)


DATE_PATTERN = re.compile(
    rf"""
    \b
    (?:
        {MONTH_PATTERN}\s+(?:19|20)\d{{2}}
        |
        {MONTH_PATTERN}\s+\d{{1,2}},?\s+(?:19|20)\d{{2}}
        |
        (?:19|20)\d{{2}}
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# STATUS PATTERNS
# ============================================================

# IMPORTANT:
# These are certification completion/status indicators.
#
# Example:
#
#   Python / Domain Certification Completed
#
# should remain ONE logical certification block.
#
# The status itself is preserved in the block so that
# downstream extractors can use it if required.

COMPLETION_PATTERN = re.compile(
    r"\b(?:completed|complete|passed|attained|"
    r"received|achieved|obtained)\b",
    re.IGNORECASE,
)


# A line containing ONLY a status is metadata belonging
# to the previous certification.

STATUS_ONLY_PATTERN = re.compile(
    r"^(?:completed|complete|passed|attained|"
    r"received|achieved|obtained)$",
    re.IGNORECASE,
)


# ============================================================
# CERTIFICATION PROVIDERS
# ============================================================

CERTIFICATION_PROVIDERS = (
    "amazon web services",
    "aws",
    "microsoft",
    "google cloud",
    "google",
    "coursera",
    "udemy",
    "deep learning.ai",
    "deeplearning.ai",
    "tensorflow",
    "ibm",
    "oracle",
    "cisco",
    "comptia",
    "meta",
    "udacity",
    "linkedin learning",
    "linkedin",
    "pluralsight",
    "edx",
    "simplilearn",
    "infosys",
    "accenture",
)


# ============================================================
# CERTIFICATION KEYWORDS
# ============================================================

CERTIFICATION_KEYWORDS = (
    "certified",
    "certification",
    "certificate",
    "specialization",
    "specialisation",
    "professional certificate",
    "professional certification",
    "credential",
    "license",
    "licence",
    "nanodegree",
)


CERTIFICATION_LEVEL_KEYWORDS = (
    "associate",
    "specialist",
    "fundamentals",
    "professional",
    "expert",
    "advanced",
    "administrator",
    "developer",
    "architect",
    "engineer",
    "practitioner",
)


# ============================================================
# METADATA KEYWORDS
# ============================================================

ISSUE_METADATA = (
    "issued",
    "issue date",
    "issued date",
    "issued on",
    "awarded",
    "completed on",
    "completion date",
    "completion",
    "obtained",
    "achieved",
)


EXPIRATION_METADATA = (
    "expiration",
    "expiration date",
    "expiry",
    "expiry date",
    "expires",
    "expires on",
    "valid until",
    "valid through",
)


CREDENTIAL_METADATA = (
    "credential id",
    "credential number",
    "credential no",
    "certificate id",
    "certificate number",
    "certificate no",
    "certification id",
    "certification number",
    "certification no",
    "cert id",
    "cert number",
    "cert no",
)


# ============================================================
# CLEANING
# ============================================================

def clean_line(line):
    """
    Clean a certification line.

    Handles common PDF/OCR artifacts.
    """

    if not isinstance(line, str):
        return None

    line = line.strip()

    if not line:
        return None

    # Normalize dash variants.
    line = line.replace("\u2013", "-")
    line = line.replace("\u2014", "-")
    line = line.replace("\u2212", "-")

    # Normalize bullets.
    line = line.replace("\u2022", " ")
    line = line.replace("\u25CF", " ")
    line = line.replace("\u25AA", " ")
    line = line.replace("\u25E6", " ")

    # Remove leading bullet characters.
    line = re.sub(
        r"^[\s•●▪◦*-]+",
        "",
        line,
    )

    # Normalize whitespace.
    line = re.sub(
        r"\s+",
        " ",
        line,
    )

    return line.strip()


# ============================================================
# CERTIFICATION SECTION HEADING
# ============================================================

def is_certification_heading(line):
    """
    Detect certification section headings.

    These lines should NOT become certification records.
    """

    if not isinstance(line, str):
        return False

    line = clean_line(line)

    if not line:
        return False

    normalized = line.lower()

    normalized = re.sub(
        r"[^a-z0-9& ]",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()

    return normalized in {
        "certificate",
        "certificates",
        "certification",
        "certifications",
        "professional certificate",
        "professional certificates",
        "professional certification",
        "professional certifications",
        "technical certificate",
        "technical certificates",
        "technical certification",
        "technical certifications",
        "course certificate",
        "course certificates",
        "course certification",
        "course certifications",
        "license",
        "licenses",
        "licence",
        "licences",
    }


# ============================================================
# COMPLETION STATUS
# ============================================================

def has_completion_status(line):
    """
    Return True when a certification line contains
    a completion/status indicator.

    Examples:

        Python Certification Completed
        Professional Development Program Completed
        Workplace Communication - Passed
    """

    if not isinstance(line, str):
        return False

    line = clean_line(line)

    if not line:
        return False

    return bool(
        COMPLETION_PATTERN.search(line)
    )


def is_status_only(line):
    """
    Check whether a line contains ONLY a status.

    Example:

        Completed
        Passed
        Achieved
    """

    if not isinstance(line, str):
        return False

    line = clean_line(line)

    if not line:
        return False

    return bool(
        STATUS_ONLY_PATTERN.fullmatch(line)
    )


# ============================================================
# METADATA DETECTION
# ============================================================

def is_metadata_line(line):
    """
    Detect date / credential / issue / expiration metadata.
    """

    if not isinstance(line, str):
        return False

    line = clean_line(line)

    if not line:
        return False

    lower = line.lower()

    # Status-only lines are metadata.
    if is_status_only(line):
        return True

    # Explicit metadata labels.
    metadata_prefixes = (
        ISSUE_METADATA
        + EXPIRATION_METADATA
        + CREDENTIAL_METADATA
    )

    for prefix in metadata_prefixes:

        if lower.startswith(prefix):
            return True

    # Standalone year.
    if re.fullmatch(
        r"(?:19|20)\d{2}",
        line,
    ):
        return True

    # Year range.
    if YEAR_RANGE_PATTERN.fullmatch(line):
        return True

    return False


# ============================================================
# PROVIDER DETECTION
# ============================================================

def is_known_provider(line):
    """
    Detect known certification providers.
    """

    if not isinstance(line, str):
        return False

    line = clean_line(line)

    if not line:
        return False

    lower = line.lower()

    for provider in CERTIFICATION_PROVIDERS:

        if provider in lower:
            return True

    return False


def looks_like_organization(line):
    """
    Detect organization-only lines.

    Examples:

        Amazon Web Services
        Microsoft
        Coursera
        Google Cloud
    """

    if not isinstance(line, str):
        return False

    line = clean_line(line)

    if not line:
        return False

    if is_metadata_line(line):
        return False

    if is_known_provider(line):

        lower = line.lower()

        # Exact provider-only line.
        for provider in CERTIFICATION_PROVIDERS:

            if lower == provider:
                return True

    return False


# ============================================================
# CERTIFICATION START
# ============================================================

def is_certification_start(line):
    """
    Detect whether a line looks like the beginning
    of a certification.

    IMPORTANT:

    Completion-style rows are considered certification
    starts even when the title contains no explicit
    certification keyword.

    Example:

        Professional Development Program Completed

    is a certification start.
    """

    if not isinstance(line, str):
        return False

    line = clean_line(line)

    if not line:
        return False

    if is_certification_heading(line):
        return False

    if is_status_only(line):
        return False

    if is_metadata_line(line):
        return False

    lower = line.lower()

    # ========================================================
    # 1. COMPLETION ROW
    #
    # This is the most important addition for the screenshot.
    #
    # Example:
    #
    #   Python / Domain Certification Completed
    #   Professional Development Program Completed
    #   Workplace Communication Completed
    #
    # Each one is a separate certification.
    # ========================================================

    if has_completion_status(line):

        # Make sure there is actual title text before
        # the completion status.
        title_part = COMPLETION_PATTERN.sub(
            "",
            line,
        ).strip()

        if title_part:
            return True

    # ========================================================
    # 2. Strong certification keywords
    # ========================================================

    for keyword in CERTIFICATION_KEYWORDS:

        if keyword in lower:
            return True

    # ========================================================
    # 3. Known provider
    # ========================================================

    if is_known_provider(line):

        # Provider-only line is organization metadata.
        if looks_like_organization(line):
            return False

        return True

    # ========================================================
    # 4. Certification level indicators
    # ========================================================

    for indicator in CERTIFICATION_LEVEL_KEYWORDS:

        if indicator in lower:

            if len(line.split()) >= 2:
                return True

    # ========================================================
    # 5. Provider after separator
    #
    # Examples:
    #
    #   Python for Everybody - Coursera
    #   Django - Udemy
    # ========================================================

    if re.search(
        r"\s[-|/]\s*"
        r"(?:coursera|udemy|microsoft|google cloud|"
        r"aws|amazon web services|ibm|oracle|cisco|"
        r"udacity|edx|pluralsight)\b",
        lower,
    ):
        return True

    return False


# ============================================================
# INLINE CERTIFICATION SPLITTER
# ============================================================

def split_inline_certifications(line):
    """
    Split multiple certifications on one physical line.

    Examples:

        Python - Coursera; Django - Udemy

    becomes:

        Python - Coursera
        Django - Udemy

    IMPORTANT:

    Do NOT split on commas because commas can legitimately
    occur inside certification names.
    """

    line = clean_line(line)

    if not line:
        return []

    parts = re.split(
        r"\s*;\s*|\s*\|\s*",
        line,
    )

    parts = [
        clean_line(part)
        for part in parts
        if clean_line(part)
    ]

    return parts


# ============================================================
# COMPLETION ROW NORMALIZATION
# ============================================================

def normalize_completion_row(line):
    """
    Normalize a certification completion row.

    Example:

        Python / Domain Certification Completed

    becomes:

        Python / Domain Certification
        Completed

    The two values are kept together inside the SAME block.

    Returns:

        [
            "Python / Domain Certification",
            "Completed"
        ]
    """

    line = clean_line(line)

    if not line:
        return []

    match = COMPLETION_PATTERN.search(
        line
    )

    if not match:
        return [line]

    title = line[
        :match.start()
    ].strip()

    status = line[
        match.start():
    ].strip()

    if not title:
        return [line]

    return [
        title,
        status,
    ]


# ============================================================
# LONG LINE SPLITTER
# ============================================================

def split_long_certification_line(line):
    """
    Split a long certification line when it actually
    contains multiple certification records.

    IMPORTANT:

    A completion row such as:

        Python Certification Completed

    must NOT be split into two certification records.

    Instead it becomes:

        ["Python Certification", "Completed"]
    """

    line = clean_line(line)

    if not line:
        return []

    # --------------------------------------------------------
    # First handle semicolon / pipe separators.
    # --------------------------------------------------------

    inline_parts = split_inline_certifications(
        line
    )

    if len(inline_parts) > 1:
        return inline_parts

    # --------------------------------------------------------
    # Completion-style row.
    #
    # Keep title + status together.
    # --------------------------------------------------------

    if has_completion_status(line):

        return [
            line
        ]

    # --------------------------------------------------------
    # Otherwise leave line unchanged.
    # --------------------------------------------------------

    return [line]


# ============================================================
# NORMALIZE INPUT
# ============================================================

def normalize_certification_input(
    certification_section,
):
    """
    Normalize string / flat list / nested list into
    a clean flat list of physical lines.
    """

    if not certification_section:
        return []

    # ========================================================
    # STRING
    # ========================================================

    if isinstance(
        certification_section,
        str,
    ):

        lines = []

        for raw_line in certification_section.splitlines():

            line = clean_line(
                raw_line
            )

            if not line:
                continue

            parts = split_long_certification_line(
                line
            )

            lines.extend(parts)

        return lines

    # ========================================================
    # LIST
    # ========================================================

    if not isinstance(
        certification_section,
        list,
    ):
        return []

    lines = []

    for item in certification_section:

        # ----------------------------------------------------
        # Nested block
        # ----------------------------------------------------

        if isinstance(item, list):

            for nested_line in item:

                nested_line = clean_line(
                    nested_line
                )

                if not nested_line:
                    continue

                parts = split_long_certification_line(
                    nested_line
                )

                lines.extend(parts)

        # ----------------------------------------------------
        # Normal line
        # ----------------------------------------------------

        elif isinstance(item, str):

            item = clean_line(
                item
            )

            if not item:
                continue

            parts = split_long_certification_line(
                item
            )

            lines.extend(parts)

    return lines


# ============================================================
# FLAT CERTIFICATION SPLITTER
# ============================================================

def split_flat_certification_lines(lines):
    """
    Convert flat certification lines into logical blocks.

    Special handling for completion-style rows.

    Example:

        [
            "Python / Domain Certification Completed",
            "Professional Development Program Completed",
            "Workplace Communication Completed"
        ]

    becomes:

        [
            [
                "Python / Domain Certification",
                "Completed"
            ],
            [
                "Professional Development Program",
                "Completed"
            ],
            [
                "Workplace Communication",
                "Completed"
            ]
        ]
    """

    if not lines:
        return []

    blocks = []

    current_block = []

    for raw_line in lines:

        line = clean_line(
            raw_line
        )

        if not line:
            continue

        # ====================================================
        # Skip section heading
        # ====================================================

        if is_certification_heading(line):
            continue

        # ====================================================
        # STATUS-ONLY LINE
        #
        # Example:
        #
        #   Python Certification
        #   Completed
        #
        # "Completed" belongs to the previous certification.
        # ====================================================

        if is_status_only(line):

            if current_block:

                current_block.append(
                    line
                )

            continue

        # ====================================================
        # COMPLETION ROW
        #
        # Example:
        #
        #   Python / Domain Certification Completed
        #
        # This ALWAYS represents a new certification row.
        # ====================================================

        if has_completion_status(line):

            # Finish previous certification.
            if current_block:

                blocks.append(
                    current_block
                )

                current_block = []

            normalized = normalize_completion_row(
                line
            )

            if normalized:

                blocks.append(
                    normalized
                )

            continue

        # ====================================================
        # NEW CERTIFICATION START
        # ====================================================

        if (
            is_certification_start(line)
            and current_block
        ):

            blocks.append(
                current_block
            )

            current_block = []

        # ====================================================
        # ADD LINE
        # ====================================================

        current_block.append(
            line
        )

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
    Merge provider-only blocks into the preceding
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

    merged = []

    for block in blocks:

        if not block:
            continue

        # ----------------------------------------------------
        # Do NOT merge completion rows.
        #
        # They are independent certification records.
        # ----------------------------------------------------

        if any(
            has_completion_status(line)
            for line in block
        ):
            merged.append(
                list(block)
            )
            continue

        # ----------------------------------------------------
        # Organization-only block
        # ----------------------------------------------------

        if (
            len(block) == 1
            and looks_like_organization(
                block[0]
            )
            and merged
        ):

            merged[-1].extend(
                block
            )

            continue

        merged.append(
            list(block)
        )

    return merged


# ============================================================
# MERGE METADATA-ONLY BLOCKS
# ============================================================

def _merge_metadata_only_blocks(blocks):
    """
    Merge standalone metadata into the previous
    certification.

    Example:

        [
            ["AWS Certified Developer"],
            ["2024"]
        ]

    becomes:

        [
            [
                "AWS Certified Developer",
                "2024"
            ]
        ]
    """

    if not blocks:
        return []

    merged = []

    for block in blocks:

        if not block:
            continue

        # ----------------------------------------------------
        # Never merge completion certification rows.
        # ----------------------------------------------------

        if any(
            has_completion_status(line)
            for line in block
        ):
            merged.append(
                list(block)
            )
            continue

        # ----------------------------------------------------
        # Metadata-only block
        # ----------------------------------------------------

        if (
            len(block) == 1
            and is_metadata_line(
                block[0]
            )
            and merged
        ):

            merged[-1].extend(
                block
            )

            continue

        merged.append(
            list(block)
        )

    return merged


# ============================================================
# DEDUPLICATION
# ============================================================

def _deduplicate_blocks(blocks):
    """
    Remove exact duplicate blocks while preserving
    original text casing.
    """

    result = []

    seen = set()

    for block in blocks:

        cleaned_block = [
            clean_line(line)
            for line in block
            if clean_line(line)
        ]

        if not cleaned_block:
            continue

        key = tuple(
            line.lower()
            for line in cleaned_block
        )

        if key in seen:
            continue

        seen.add(key)

        result.append(
            cleaned_block
        )

    return result


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def split_certification_blocks(
    certification_section,
):
    """
    Main certification block splitter.

    Returns logical certification blocks.
    """

    # ========================================================
    # STEP 1
    # Normalize input
    # ========================================================

    lines = normalize_certification_input(
        certification_section
    )

    if not lines:
        return []

    # ========================================================
    # STEP 2
    # Remove section headings
    # ========================================================

    lines = [
        line
        for line in lines
        if not is_certification_heading(line)
    ]

    if not lines:
        return []

    # ========================================================
    # STEP 3
    # Split flat lines
    # ========================================================

    blocks = split_flat_certification_lines(
        lines
    )

    if not blocks:
        return []

    # ========================================================
    # STEP 4
    # Merge organization-only blocks
    # ========================================================

    blocks = _merge_org_only_blocks(
        blocks
    )

    # ========================================================
    # STEP 5
    # Merge metadata-only blocks
    # ========================================================

    blocks = _merge_metadata_only_blocks(
        blocks
    )

    # ========================================================
    # STEP 6
    # Deduplicate
    # ========================================================

    blocks = _deduplicate_blocks(
        blocks
    )

    return blocks


# ============================================================
# TESTS
# ============================================================

if __name__ == "__main__":

    test_cases = {

        # ----------------------------------------------------
        # SCREENSHOT FORMAT
        # ----------------------------------------------------

        "Screenshot format": [
            "Certificate",
            "Python / Domain Certification Completed",
            "Professional Development Program Completed",
            "Workplace Communication Completed",
        ],

        # ----------------------------------------------------
        # Same format without explicit certification keywords
        # ----------------------------------------------------

        "Generic completion rows": [
            "Completed Python Training",
            "Completed Professional Development Program",
            "Completed Workplace Communication",
        ],

        # ----------------------------------------------------
        # Completion on separate line
        # ----------------------------------------------------

        "Separate status line": [
            "Python / Domain Certification",
            "Completed",
            "Professional Development Program",
            "Completed",
            "Workplace Communication",
            "Completed",
        ],

        # ----------------------------------------------------
        # Standard certification
        # ----------------------------------------------------

        "Standard certification": [
            "AWS Certified Developer",
            "Amazon Web Services",
            "Issued: 2024",
            "Credential ID: AWS123",
        ],

        # ----------------------------------------------------
        # Multiple standard certifications
        # ----------------------------------------------------

        "Multiple certifications": [
            "AWS Certified Developer",
            "Amazon Web Services",
            "Issued: 2024",
            "Microsoft Certified Azure Fundamentals",
            "Microsoft",
            "Issued: 2023",
        ],

        # ----------------------------------------------------
        # Provider based
        # ----------------------------------------------------

        "Provider based": [
            "Python for Everybody - Coursera",
            "Django Web Development - Udemy",
            "Machine Learning Specialization - Coursera",
        ],

        # ----------------------------------------------------
        # Inline
        # ----------------------------------------------------

        "Inline": [
            "Python Certification - Coursera; "
            "Django Certification - Udemy"
        ],

        # ----------------------------------------------------
        # Nested
        # ----------------------------------------------------

        "Nested": [
            [
                "AWS Certified Developer",
                "Amazon Web Services",
                "2024",
            ],
            [
                "Microsoft Certified Azure Developer",
                "Microsoft",
                "2023",
            ],
        ],
    }


    for name, test_case in test_cases.items():

        print(
            "\n"
            + "=" * 70
        )

        print(
            name
        )

        print(
            "=" * 70
        )

        result = split_certification_blocks(
            test_case
        )

        for index, block in enumerate(
            result,
            start=1,
        ):

            print(
                f"\nBLOCK {index}:"
            )

            for line in block:

                print(
                    f"  {line}"
                )