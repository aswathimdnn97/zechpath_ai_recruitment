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

        if re.search(pattern, text):
            return True

    return False


def clean_field(field):
    """
    Clean extracted field text.
    """

    if not field:
        return None

    field = field.strip()

    field = re.sub(
        r"\s+",
        " ",
        field
    )

    field = field.strip(
        " ,.;:-"
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

        if not isinstance(line, str):
            continue

        line = line.strip()

        if not line:
            continue

        # ---------------------------------------------
        # Never treat a degree line as a field
        # ---------------------------------------------

        if is_degree_line(line):
            continue

        lower_line = line.lower()

        # ---------------------------------------------
        # Ignore academic metadata
        # ---------------------------------------------

        ignored_patterns = [

            r"^\d{4}\s*[-–]\s*(?:\d{4}|present)$",
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
                lower_line
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
    ]

    for block in examples:

        print(
            extract_field_of_study(
                block
            )
        )



if __name__ == "__main__":

    block = [

        "2012-2016 Bachelor of Engineering (B.E), P.E.S Institute of Technology",
        "Visvesvaraya Technological University",
        "Computer Science and Engineering",
        "Aggregate Score : 64.2"

    ]

    print(extract_field_of_study(block))