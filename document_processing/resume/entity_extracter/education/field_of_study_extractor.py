"""
field_of_study_extractor.py

Extract the field/specialization studied by the candidate.

Examples
--------

Bachelor of Engineering
Computer Science and Engineering

-> Computer Science and Engineering

Bachelor of Technology
Information Technology

-> Information Technology

Electronics Communication Engineering 2026

-> Electronics Communication Engineering
"""

import re


# ---------------------------------------------------------
# Degree Indicators
# ---------------------------------------------------------

DEGREE_PATTERNS = [

    r"\bbachelor\b",

    r"\bmaster\b",

    r"\bb\.?\s*tech\b",

    r"\bb\.?\s*e\b",

    r"\bb\.?\s*sc\b",

    r"\bbca\b",

    r"\bm\.?\s*tech\b",

    r"\bm\.?\s*e\b",

    r"\bm\.?\s*sc\b",

    r"\bmca\b",

    r"\bmba\b",

    r"\bphd\b",

    r"\bdoctor of philosophy\b",

    r"\bassociate\b",

    r"\bdiploma\b",
]


# ---------------------------------------------------------
# Field Indicators
# ---------------------------------------------------------

FIELD_KEYWORDS = [

    "computer science",

    "computer applications",

    "information technology",

    "information systems",

    "electronics",

    "electronics and communication",

    "electrical engineering",

    "mechanical engineering",

    "civil engineering",

    "chemical engineering",

    "aerospace engineering",

    "biomedical engineering",

    "software engineering",

    "data science",

    "artificial intelligence",

    "machine learning",

    "natural language processing",

    "business administration",

    "business management",

    "management",

    "commerce",

    "physics",

    "chemistry",

    "mathematics",

    "biology",

    "economics",

    "finance",

    "accounting",

    "marketing",

    "human resources",

    "arts",

    "science",
]


# ---------------------------------------------------------
# Academic Year Patterns
# ---------------------------------------------------------

YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)

YEAR_RANGE_PATTERN = re.compile(
    r"""
    \b(?:19|20)\d{2}
    \s*
    [-–—]
    \s*
    (?:
        (?:19|20)\d{2}
        |
        present
    )
    \b
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def is_degree_line(line):
    """
    Check whether a line primarily represents a degree.
    """

    if not line:
        return False

    text = line.strip().lower()

    for pattern in DEGREE_PATTERNS:

        if re.search(
            pattern,
            text,
        ):
            return True

    return False


# ---------------------------------------------------------
# Remove Academic Years
# ---------------------------------------------------------

def _remove_academic_years(field):
    """
    Remove academic years from field-of-study text.

    Examples
    --------
    Electronics Communication Engineering 2026
        ->
    Electronics Communication Engineering

    Computer Science 2022-2026
        ->
    Computer Science
    """

    if not isinstance(field, str):
        return ""

    # Remove ranges first
    field = YEAR_RANGE_PATTERN.sub(
        "",
        field,
    )

    # Remove standalone years
    field = YEAR_PATTERN.sub(
        "",
        field,
    )

    # Normalize whitespace
    field = re.sub(
        r"\s+",
        " ",
        field,
    )

    return field.strip()


def clean_field(field):
    """
    Clean extracted field-of-study text.

    Years are removed because graduation_year is
    extracted separately.
    """

    if not isinstance(field, str):
        return None

    field = field.strip()

    if not field:
        return None

    # Remove academic years
    field = _remove_academic_years(field)

    # Remove surrounding punctuation
    field = field.strip(
        " ,.;:-|–—"
    )

    # Normalize whitespace
    field = re.sub(
        r"\s+",
        " ",
        field,
    )

    if not field:
        return None

    return field

# ---------------------------------------------------------
# Extract Field of Study
# ---------------------------------------------------------

def extract_field_of_study(block):
    """
    Extract field of study from an education block.

    Parameters
    ----------
    block : list[str]

    Returns
    -------
    str | None
    """

    if not block:
        return None

    for line in block:

        if not isinstance(
            line,
            str,
        ):
            continue

        line = line.strip()

        if not line:
            continue

        lower_line = line.lower()

        # =============================================
        # Handle "Degree in FieldOfStudy" pattern
        #
        # Example:
        # B.Tech in Computer Science and Engineering
        # =============================================

        if " in " in lower_line:

            parts = re.split(
                r"\s+in\s+",
                line,
                flags=re.IGNORECASE,
            )

            if len(parts) > 1:

                field_candidate = parts[1]

                # -------------------------------------
                # Remove everything after "|"
                # -------------------------------------

                if "|" in field_candidate:

                    field_candidate = (
                        field_candidate
                        .split("|")[0]
                        .strip()
                    )

                # -------------------------------------
                # Remove text after dash separator
                # -------------------------------------

                match = re.search(
                    r"\s[—–-]\s",
                    field_candidate,
                )

                if match:

                    field_candidate = (
                        field_candidate[
                            :match.start()
                        ].strip()
                    )

                else:

                    # ---------------------------------
                    # Remove institution information
                    # ---------------------------------

                    match = re.search(
                        r"\b(?:university|college|institute|institution|technological|polytechnic)\b",
                        field_candidate,
                        re.IGNORECASE,
                    )

                    if match:

                        field_candidate = (
                            field_candidate[
                                :match.start()
                            ].strip()
                        )

                # -------------------------------------
                # Clean academic years
                # -------------------------------------

                field_candidate = clean_field(
                    field_candidate
                )

                if field_candidate:

                    for keyword in FIELD_KEYWORDS:

                        if (
                            keyword.lower()
                            in field_candidate.lower()
                        ):
                            return field_candidate

        # =============================================
        # Fallback: field embedded in a degree line
        #
        # Example:
        #
        # Bachelor of Technology
        # Computer Science and Engineering
        # =============================================

        for keyword in FIELD_KEYWORDS:

            keyword_lower = keyword.lower()

            idx = lower_line.find(
                keyword_lower
            )

            if idx != -1:

                field_candidate = line[idx:]

                # -------------------------------------
                # Stop at pipe
                # -------------------------------------

                field_candidate = re.split(
                    r"\|",
                    field_candidate,
                    maxsplit=1,
                )[0]

                # -------------------------------------
                # Stop at institution separators
                # -------------------------------------

                field_candidate = re.split(
                    r"""
                    \s*-\s*
                    |
                    \s*,\s*
                    (?=
                        university
                        |
                        college
                        |
                        institute
                        |
                        institution
                        |
                        technological
                        |
                        polytechnic
                    )
                    """,
                    field_candidate,
                    maxsplit=1,
                    flags=re.IGNORECASE | re.VERBOSE,
                )[0]

                # -------------------------------------
                # Clean field
                # -------------------------------------

                field_candidate = clean_field(
                    field_candidate
                )

                if field_candidate:

                    return field_candidate

        # =============================================
        # Original logic
        # =============================================

        # Never treat a degree line as a field

        if is_degree_line(line):
            continue

        # ---------------------------------------------
        # Ignore academic metadata
        # ---------------------------------------------

        ignored_patterns = [

            r"^\d{4}\s*[-–—]\s*(?:\d{4}|present)$",

            r"^cgpa",

            r"^gpa",

            r"^sgpa",

            r"^aggregate",

            r"^marks obtained",

            r"^percentage",

            r"^grade",
        ]

        if any(
            re.search(
                pattern,
                lower_line,
            )
            for pattern in ignored_patterns
        ):
            continue

        # ---------------------------------------------
        # Exact field keyword matching
        # ---------------------------------------------

        for keyword in FIELD_KEYWORDS:

            if keyword in lower_line:

                return clean_field(
                    line
                )

    return None


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    examples = [

        [
            "Bachelor of Engineering",
            "PES Institute of Technology",
            "2012-2016",
        ],

        [
            "Bachelor of Engineering",
            "PES Institute of Technology",
            "Computer Science and Engineering",
            "2012-2016",
        ],

        [
            "Bachelor of Technology",
            "Information Technology",
            "2018-2022",
        ],

        [
            "Electronics Communication Engineering 2026",
        ],

        [
            "B.Tech Electronics Communication Engineering 2026",
        ],

        [
            "Electronics Communication Engineering | 2022-2026",
        ],
    ]

    for block in examples:

        print(
            extract_field_of_study(
                block
            )
        )