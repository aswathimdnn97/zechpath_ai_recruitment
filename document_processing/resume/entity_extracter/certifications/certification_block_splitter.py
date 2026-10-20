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

from document_processing.resume.entity_extracter.certifications.organization_extractor import (
    split_organization_suffix,
)


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
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

DATE_RANGE_SEPARATOR_PATTERN = re.compile(
    rf"""
    (?P<start>
        (?:{MONTH_PATTERN}\s*,?\s*)?
        (?:19|20)\d{{2}}
    )
    (?P<before>\s*)
    (?P<separator>[—–])
    (?P<after>\s*)
    (?P<end>
        (?:
            (?:{MONTH_PATTERN}\s*,?\s*)?
            (?:19|20)\d{{2}}
            |
            present
            |
            current
            |
            ongoing
        )
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

PROFESSIONAL_DATA_ENGINEER_PATTERN = re.compile(
    r"\bprofessional\s*data\s*engineer\b",
    re.IGNORECASE,
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

    # Remove unrelated resume headers and test-data descriptions.
    if is_document_noise(line):
        return None

    return line
# ============================================================
# DOCUMENT NOISE FILTER
# ============================================================

DOCUMENT_NOISE_PATTERNS = (
    re.compile(
        r"\b(?:curriculum\s+vitae|resume)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bfictional\s+test\s+data\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\btest\s+data\s+for\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\beligibility\s+api\s+validation\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bsample\s+resume\b",
        re.IGNORECASE,
    ),
)


def is_document_noise(line):
    """
    Detect resume headings and unrelated test-data descriptions.

    Do not reject normal certification titles merely because
    they contain words such as 'professional' or 'fundamentals'.
    """
    if not isinstance(line, str):
        return False

    return any(
        pattern.search(line)
        for pattern in DOCUMENT_NOISE_PATTERNS
    )
# ============================================================
# SPLIT LONG CERTIFICATION LINE
# ============================================================

def split_long_certification_line(line):
    """
    Split a long line when multiple certifications are
    separated by em dash / en dash or by completion markers.

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

    # Split on completion/status markers, which are common in flat inline sections
    # such as: "Certificate Python / Domain Certification Completed Professional Development Program Completed Workplace Communication Completed"
    matches = list(re.finditer(r"\b(?:completed|passed|attained|received)\b", line, flags=re.IGNORECASE))
    if matches:
        segments = []
        last_index = 0
        for match in matches:
            segment = line[last_index:match.start()].strip()
            if segment:
                segments.append(segment)
                segments.append("Completed")
            last_index = match.end()
        tail = line[last_index:].strip()
        if tail:
            segments.append(tail)
        cleaned = [part.strip() for part in segments if part and part.strip()]
        if len(cleaned) > 1:
            return cleaned

    date_range_token = "\x00DATE_RANGE_SEPARATOR\x00"
    protected_line = DATE_RANGE_SEPARATOR_PATTERN.sub(
        lambda match: (
            f"{match.group('start')}"
            f"{match.group('before')}"
            f"{date_range_token}"
            f"{match.group('after')}"
            f"{match.group('end')}"
        ),
        line,
    )

    parts = re.split(
        r"\s+[—–]\s+",
        protected_line
    )

    if len(parts) <= 1:
        return [line]

    cleaned_parts = [
        part.replace(date_range_token, "–").strip()
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
    of a certification or training record.
    """
    if not isinstance(line, str):
        return False

    line = line.strip()

    if not line:
        return False

    lower = line.lower()

    # Ignore document noise.
    if is_document_noise(line):
        return False

    # Metadata lines are not certification starts.
    if _is_metadata_line_for_splitter(line):
        return False

    # Standalone year is not a certification start.
    if re.fullmatch(r"(?:19|20)\d{2}", line):
        return False

    # Date ranges are not certification starts.
    if YEAR_RANGE_PATTERN.fullmatch(line):
        return False

    if PROFESSIONAL_DATA_ENGINEER_PATTERN.search(line):
        return True

    # Explicit certification wording.
    certification_keywords = (
        "certified",
        "certification",
        "certificate",
        "license",
        "licence",
    )

    if any(keyword in lower for keyword in certification_keywords):
        return True

    # Known organization suffix.
    if split_organization_suffix(line):
        return True

    # Recognize common training/course title patterns.
    # These are targeted signals, not a requirement for every title.
    course_indicators = (
        "fundamentals",
        "professional development",
        "programming",
        "development and testing",
        "specialization",
        "specialisation",
    )

    if any(indicator in lower for indicator in course_indicators):
        return True

    return False


def _is_metadata_line_for_splitter(line):
    """Identify certification metadata lines."""
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
            line.strip(),
            re.IGNORECASE,
        )
    )

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

    # Training records often use "Course | Issuer" without
    # certification-specific wording in the course title.
    parts = [part.strip() for part in line.split("|")]
    if len(parts) > 1 and all(parts):
        return True

    if split_organization_suffix(line):
        return True

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
        split_parts = split_long_certification_line(line)

        if len(split_parts) > 1 and split_parts != [line]:
            if current_block:
                blocks.append(current_block)
                current_block = []
            for part in split_parts:
                normalized_part = part.strip().lower()
                if normalized_part in {"completed", "passed", "attained", "received"}:
                    if current_block:
                        blocks.append(current_block)
                        current_block = []
                    continue
                if is_certification_start(part) and current_block:
                    blocks.append(current_block)
                    current_block = []
                current_block.append(part)
            continue

        normalized_line = line.strip().lower()

        if normalized_line in {"completed", "passed", "attained", "received"}:
            if current_block:
                blocks.append(current_block)
                current_block = []
            continue

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
