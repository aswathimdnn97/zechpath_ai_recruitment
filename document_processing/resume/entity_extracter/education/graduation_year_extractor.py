"""
graduation_year_extractor.py

Responsibilities

1. Extract graduation year from an education block.
2. Return graduation year.
"""

import re


# -------------------------------------------------------
# Extract Graduation Year
# -------------------------------------------------------

def extract_graduation_year(education_block):
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

    # Flatten nested list
    if (
        isinstance(education_block, list)
        and education_block
        and isinstance(education_block[0], list)
    ):
        education_block = education_block[0]

    text = " ".join(education_block)

    # Find all 4-digit years
    years = re.findall(
        r"\b(?:19|20)\d{2}\b",
        text
    )

    if not years:
        return None

    # Return the latest year
    return max(years)
    

# -------------------------------------------------------
# Testing
# -------------------------------------------------------

if __name__ == "__main__":

    education = [

        "Bachelor of Technology in Computer Science",

        "APJ Abdul Kalam Technological University",

        "2019 - 2023"

    ]

    print(extract_graduation_year(education))