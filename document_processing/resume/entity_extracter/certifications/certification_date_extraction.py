"""
certification_date_extraction.py

Extract and normalize dates from certification/training records.

Supported record types:

    certification
    training

Certification examples
-----------------------

    Microsoft Certified: Azure Developer Associate
    Microsoft (2024)

    -> issue_date = 2024


    AWS Certified Developer
    Issued: March 2024
    Expires: March 2027

    -> issue_date = March 2024
    -> expiration_date = March 2027


    AWS Certified Developer
    Amazon Web Services (2024 - 2027)

    -> issue_date = 2024
    -> expiration_date = 2027


Training examples
-----------------

    Java With SpringBoot |
    ROGERSOFT Technology Private Limited
    May 2022 - July 2022

    -> course_start_date = May 2022
    -> course_end_date = July 2022


    Python Full-Stack Development |
    ROGERSOFT Technology Private Limited
    May 2026 - Present

    -> course_start_date = May 2026
    -> course_end_date = Present
"""


import re


# ============================================================
# BASIC PATTERNS
# ============================================================

YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)


MONTH_PATTERN = (
    r"(?:"
    r"Jan(?:uary)?|"
    r"Feb(?:ruary)?|"
    r"Mar(?:ch)?|"
    r"Apr(?:il)?|"
    r"May|"
    r"Jun(?:e)?|"
    r"Jul(?:y)?|"
    r"Aug(?:ust)?|"
    r"Sep(?:tember)?|"
    r"Oct(?:ober)?|"
    r"Nov(?:ember)?|"
    r"Dec(?:ember)?"
    r")"
)


# ============================================================
# DATE VALUE
#
# Supports:
#
# 2024
# March 2024
# March, 2024
# 03/2024
# 03-2024
# ============================================================

DATE_VALUE_PATTERN = rf"""
(?:
    {MONTH_PATTERN}
    \s*,?\s*
    (?:19|20)\d{{2}}

    |

    \d{{1,2}}[/-](?:19|20)\d{{2}}

    |

    (?:19|20)\d{{2}}
)
"""


# ============================================================
# EXPLICIT ISSUE DATE
# ============================================================

ISSUE_DATE_PATTERN = re.compile(
    rf"""
    (?:
        issued?
        |
        issue\s+date
        |
        awarded
        |
        awarded\s+on
        |
        completed
        |
        completion\s+date
    )
    \s*
    [:\-]?
    \s*
    (?P<date>{DATE_VALUE_PATTERN})
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# EXPLICIT EXPIRATION DATE
# ============================================================

EXPIRATION_DATE_PATTERN = re.compile(
    rf"""
    (?:
        expires?
        |
        expiry
        |
        expiry\s+date
        |
        expiration
        |
        expiration\s+date
        |
        valid\s+until
        |
        valid\s+through
    )
    \s*
    [:\-]?
    \s*
    (?P<date>{DATE_VALUE_PATTERN})
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# DATE RANGE
#
# 2024 - 2027
# May 2022 - July 2022
# May 2026 - Present
# ============================================================

DATE_RANGE_PATTERN = re.compile(
    rf"""
    (?P<start>
        {DATE_VALUE_PATTERN}
    )
    \s*
    [-–—]
    \s*
    (?P<end>
        {DATE_VALUE_PATTERN}
        |
        Present
        |
        Current
        |
        Ongoing
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# PARENTHESIZED DATE RANGE
#
# Microsoft (2024 - 2027)
# Microsoft (2024 - Present)
# ============================================================

PARENTHESIZED_DATE_RANGE_PATTERN = re.compile(
    rf"""
    \(
        \s*
        (?P<start>
            {DATE_VALUE_PATTERN}
        )
        \s*
        [-–—]
        \s*
        (?P<end>
            {DATE_VALUE_PATTERN}
            |
            Present
            |
            Current
            |
            Ongoing
        )
        \s*
    \)
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# PARENTHESIZED SINGLE DATE
#
# Microsoft (2024)
# IBM (2021)
# TensorFlow (2022)
# ============================================================

PARENTHESIZED_DATE_PATTERN = re.compile(
    rf"""
    \(
        \s*
        (?P<date>{DATE_VALUE_PATTERN})
        \s*
    \)
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# CLEAN DATE
# ============================================================

def clean_date(value):
    """
    Normalize extracted date text.
    """

    if not value:
        return None

    value = value.strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    value = value.rstrip(
        ".,;:"
    )

    return value


# ============================================================
# EXPLICIT ISSUE DATE
# ============================================================

def extract_explicit_issue_date(lines):
    """
    Extract explicit issue date.

    Examples:

        Issued: March 2024
        Issue Date: 2024
        Awarded: 03/2024
    """

    for line in lines:

        match = ISSUE_DATE_PATTERN.search(
            line
        )

        if match:

            return clean_date(
                match.group("date")
            )

    return None


# ============================================================
# EXPLICIT EXPIRATION DATE
# ============================================================

def extract_explicit_expiration_date(lines):
    """
    Extract explicit expiration date.

    Examples:

        Expires: March 2027
        Expiration Date: 2027
        Valid Until: 2028
    """

    for line in lines:

        match = EXPIRATION_DATE_PATTERN.search(
            line
        )

        if match:

            return clean_date(
                match.group("date")
            )

    return None


# ============================================================
# DATE RANGE
# ============================================================

def extract_date_range(lines):
    """
    Detect a date range.

    Returns:

        {
            "start": "...",
            "end": "..."
        }

    This function does NOT decide whether the range is:

        certification validity

    or:

        course/training period.
    """

    for line in lines:

        match = DATE_RANGE_PATTERN.search(
            line
        )

        if not match:
            continue

        return {
            "start": clean_date(
                match.group("start")
            ),

            "end": clean_date(
                match.group("end")
            ),
        }

    return None


# ============================================================
# PARENTHESIZED DATE RANGE
# ============================================================

def extract_parenthesized_date_range(lines):
    """
    Detect:

        Microsoft (2024 - 2027)

        Microsoft (2024 - Present)
    """

    for line in lines:

        match = (
            PARENTHESIZED_DATE_RANGE_PATTERN.search(
                line
            )
        )

        if not match:
            continue

        return {
            "start": clean_date(
                match.group("start")
            ),

            "end": clean_date(
                match.group("end")
            ),
        }

    return None


# ============================================================
# PARENTHESIZED SINGLE DATE
# ============================================================

def extract_parenthesized_date(lines):
    """
    Detect:

        Microsoft (2024)
        IBM (2021)
        TensorFlow (2022)
    """

    for line in lines:

        match = PARENTHESIZED_DATE_PATTERN.search(
            line
        )

        if match:

            return clean_date(
                match.group("date")
            )

    return None


# ============================================================
# STANDALONE YEAR
# ============================================================

def extract_standalone_year(lines):
    """
    Extract a year from anywhere in the block.

    Preferred:

        [
            "2024",
            "Microsoft Certified: Azure Developer Associate"
        ]

    Also supports:

        [
            "Microsoft Certified: Azure Developer Associate",
            "Microsoft",
            "2024"
        ]
    """

    # --------------------------------------------------------
    # First preference:
    # entire line is a year
    # --------------------------------------------------------

    for line in lines:

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        # Never treat an explicit expiration line
        # as an issue date.
        if any(
            keyword in lower
            for keyword in [
                "expire",
                "expiry",
                "expiration",
                "valid until",
                "valid through",
            ]
        ):
            continue

        if YEAR_PATTERN.fullmatch(line):

            return line

    # --------------------------------------------------------
    # Second preference:
    # year appears somewhere in the line
    # --------------------------------------------------------

    for line in lines:

        lower = line.lower()

        if any(
            keyword in lower
            for keyword in [
                "expire",
                "expiry",
                "expiration",
                "valid until",
                "valid through",
            ]
        ):
            continue

        match = YEAR_PATTERN.search(
            line
        )

        if match:

            return match.group(0)

    return None


# ============================================================
# MAIN FUNCTION
# ============================================================

def extract_certification_date(
    block,
    record_type="certification"
):
    """
    Extract and normalize certification/training dates.

    Parameters
    ----------
    block : list[str]
        Certification/training block.

    record_type : str
        Either:

            "certification"

        or:

            "training"


    Returns
    -------

    Certification:

        {
            "issue_date": "2024",
            "expiration_date": "2027",
            "course_start_date": None,
            "course_end_date": None
        }


    Training:

        {
            "issue_date": None,
            "expiration_date": None,
            "course_start_date": "May 2022",
            "course_end_date": "July 2022"
        }
    """

    result = {
        "issue_date": None,
        "expiration_date": None,
        "course_start_date": None,
        "course_end_date": None,
    }

    # --------------------------------------------------------
    # Validate record type
    # --------------------------------------------------------

    record_type = (
        str(record_type)
        .strip()
        .lower()
    )

    if record_type not in {
        "certification",
        "training",
    }:

        raise ValueError(
            "record_type must be "
            "'certification' or 'training'"
        )

    # --------------------------------------------------------
    # Validate block
    # --------------------------------------------------------

    if not block:

        return result

    # --------------------------------------------------------
    # Normalize block
    # --------------------------------------------------------

    lines = []

    for line in block:

        if not isinstance(line, str):
            continue

        line = line.strip()

        if line:

            lines.append(line)

    if not lines:

        return result

    # ========================================================
    # 1. Explicit issue date
    # ========================================================

    issue_date = (
        extract_explicit_issue_date(
            lines
        )
    )

    if issue_date:

        result["issue_date"] = issue_date

    # ========================================================
    # 2. Explicit expiration date
    # ========================================================

    expiration_date = (
        extract_explicit_expiration_date(
            lines
        )
    )

    if expiration_date:

        result["expiration_date"] = (
            expiration_date
        )

    # ========================================================
    # 3. Date range
    #
    # Try normal range first.
    # ========================================================

    date_range = (
        extract_date_range(
            lines
        )
    )

    # ========================================================
    # 4. Parenthesized date range
    #
    # Example:
    #
    # Amazon Web Services (2024 - 2027)
    # ========================================================

    if not date_range:

        date_range = (
            extract_parenthesized_date_range(
                lines
            )
        )

    # ========================================================
    # 5. Handle date range according to record type
    # ========================================================

    if date_range:

        start_date = date_range["start"]

        end_date = date_range["end"]

        # ----------------------------------------------------
        # TRAINING
        # ----------------------------------------------------

        if record_type == "training":

            result["course_start_date"] = (
                start_date
            )

            result["course_end_date"] = (
                end_date
            )

        # ----------------------------------------------------
        # CERTIFICATION
        # ----------------------------------------------------

        elif record_type == "certification":

            # Do not overwrite explicit issue date.
            if not result["issue_date"]:

                result["issue_date"] = (
                    start_date
                )

            # Do not overwrite explicit expiration.
            if not result["expiration_date"]:

                result["expiration_date"] = (
                    end_date
                )

        # ----------------------------------------------------
        # IMPORTANT
        #
        # Stop here.
        #
        # Otherwise the 2024 from:
        #
        #     (2024 - 2027)
        #
        # could incorrectly be extracted again
        # as a standalone issue year.
        # ----------------------------------------------------

        return result

    # ========================================================
    # 6. Parenthesized single date
    #
    # Only certification records use this as issue date.
    #
    # Example:
    #
    # Microsoft (2024)
    # ========================================================

    if (
        record_type == "certification"
        and not result["issue_date"]
    ):

        parenthesized_date = (
            extract_parenthesized_date(
                lines
            )
        )

        if parenthesized_date:

            result["issue_date"] = (
                parenthesized_date
            )

    # ========================================================
    # 7. Standalone year
    #
    # Search the entire block.
    # ========================================================

    if (
        record_type == "certification"
        and not result["issue_date"]
    ):

        standalone_year = (
            extract_standalone_year(
                lines
            )
        )

        if standalone_year:

            result["issue_date"] = (
                standalone_year
            )

    # ========================================================
    # Final result
    # ========================================================

    return result


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    # ========================================================
    # CERTIFICATION TESTS
    # ========================================================

    certification_tests = [

        [
            "Microsoft Certified: Azure Developer Associate",
            "Microsoft (2024)",
        ],

        [
            "Microsoft Certified: Azure AI Fundamentals",
            "Microsoft (2023)",
        ],

        [
            "Google Cloud Professional Data Engineer",
        ],

        [
            "Machine Learning Specialization",
            "Coursera / Deep Learning.AI (2022)",
        ],

        [
            "TensorFlow Developer Certificate",
            "TensorFlow (2022)",
        ],

        [
            "Python for Data Science",
            "IBM (2021)",
        ],

        [
            "AWS Certified Developer",
            "2024",
            "Amazon Web Services",
        ],

        [
            "AWS Certified Developer",
            "Amazon Web Services",
            "2024",
        ],

        [
            "AWS Certified Developer",
            "Issued: March 2024",
        ],

        [
            "AWS Certified Developer",
            "Issued: March 2024",
            "Expires: March 2027",
        ],

        [
            "AWS Certified Developer",
            "2024 - 2027",
        ],

        [
            "AWS Certified Developer",
            "Amazon Web Services (2024 - 2027)",
        ],

        [
            "AWS Certified Developer",
            "Amazon Web Services (2024 - Present)",
        ],
    ]

    print(
        "\n========== CERTIFICATION ==========\n"
    )

    for block in certification_tests:

        print(
            "BLOCK:",
            block
        )

        result = extract_certification_date(
            block,
            record_type="certification"
        )

        print(
            "DATE:",
            result
        )

        print(
            "----------------------------------"
        )

    # ========================================================
    # TRAINING TESTS
    # ========================================================

    training_tests = [

        [
            "Java With SpringBoot | "
            "ROGERSOFT Technology Private Limited "
            "May 2022 – July 2022"
        ],

        [
            "Python Full-Stack Development | "
            "ROGERSOFT Technology Private Limited "
            "May 2026 – Present"
        ],

        [
            "Python Training",
            "May 2024 - June 2024",
        ],
    ]

    print(
        "\n========== TRAINING ==========\n"
    )

    for block in training_tests:

        print(
            "BLOCK:",
            block
        )

        result = extract_certification_date(
            block,
            record_type="training"
        )

        print(
            "DATE:",
            result
        )

        print(
            "----------------------------------"
        )
