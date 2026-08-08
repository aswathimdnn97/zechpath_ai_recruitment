"""
degree_type_extractor.py

Responsibilities

1. Extract degree type from an education block.
2. Return extracted degree.
"""

import re

# -------------------------------------------------------
# Degree Patterns
# -------------------------------------------------------

DEGREE_PATTERNS = [

    r"\bBachelor\s+of\s+Technology\b",
    r"\bBachelor\s+of\s+Engineering\b",
    r"\bBachelor\s+of\s+Science\b",
    r"\bBachelor\s+of\s+Arts\b",
    r"\bBachelor\s+of\s+Commerce\b",

    r"\bMaster\s+of\s+Technology\b",
    r"\bMaster\s+of\s+Engineering\b",
    r"\bMaster\s+of\s+Science\b",
    r"\bMaster\s+of\s+Arts\b",
    r"\bMaster\s+of\s+Computer\s+Applications\b",
    r"\bMaster\s+of\s+Business\s+Administration\b",

    r"\bDoctor\s+of\s+Philosophy\b",

    r"\bB\.?\s*Tech\b",
    r"\bB\.?\s*E\b",
    r"\bB\.?\s*Sc\b",
    r"\bB\.?\s*A\b",
    r"\bB\.?\s*Com\b",

    r"\bM\.?\s*Tech\b",
    r"\bM\.?\s*E\b",
    r"\bM\.?\s*Sc\b",

    r"\bMBA\b",
    r"\bMCA\b",
    r"\bPh\.?D\b",

    r"\bAssociate(?:'s)?\b",
    r"\bDiploma\b"
]

# -------------------------------------------------------
# Extract Degree Type
# -------------------------------------------------------

def extract_degree_type(education_block):
    """
    Parameters
    ----------
    education_block : list[str]

    Returns
    -------
    str | None
    """

    if not education_block:
        return None

    # Flatten nested list if required
    if (
        isinstance(education_block, list)
        and education_block
        and isinstance(education_block[0], list)
    ):
        education_block = education_block[0]

    text = " ".join(education_block)

    for pattern in DEGREE_PATTERNS:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            return match.group().strip()

    return None


# -------------------------------------------------------
# Testing
# -------------------------------------------------------

if __name__ == "__main__":

    education = [

        "Bachelor of Technology in Computer Science",
        "APJ Abdul Kalam Technological University",
        "2019 - 2023"

    ]

    print(extract_degree_type(education))