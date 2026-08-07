"""
duration_extractor.py

Responsibilities
----------------
1. Extract employment duration from one experience block.
2. Support multiple resume date formats.
3. Return raw start and end dates.
"""

import re

# ----------------------------------------------------
# Date Patterns
# ----------------------------------------------------

DATE_PATTERNS = [

    # Jan 2022 - Present
    r"(?P<start>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\s*[-–]\s*(?P<end>Present|Current|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})",

    # 02/2020 - 11/2022
    r"(?P<start>\d{1,2}/\d{4})\s*[-–]\s*(?P<end>\d{1,2}/\d{4}|Present|Current)",

    # 2021 - 2023
    r"(?P<start>\d{4})\s*[-–]\s*(?P<end>\d{4}|Present|Current)"
]


# ----------------------------------------------------
# Duration Extractor
# ----------------------------------------------------

def extract_duration(experience_block):
    """
    Parameters
    ----------
    experience_block : list[str]

    Returns
    -------
    dict
    """

    if not experience_block:
        return {
            "start_date": None,
            "end_date": None
        }

    # Flatten if nested
    if (
        isinstance(experience_block, list)
        and experience_block
        and isinstance(experience_block[0], list)
    ):
        experience_block = experience_block[0]

    for line in experience_block:

        if not isinstance(line, str):
            continue

        line = line.strip()

        for pattern in DATE_PATTERNS:

            match = re.search(
                pattern,
                line,
                flags=re.IGNORECASE
            )

            if match:

                return {

                    "start_date": match.group("start"),

                    "end_date": match.group("end")

                }

    return {

        "start_date": None,

        "end_date": None

    }