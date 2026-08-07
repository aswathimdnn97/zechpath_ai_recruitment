"""
description_extractor.py

Responsibilities
----------------
1. Extract job responsibilities/achievements.
2. Ignore title.
3. Ignore company.
4. Ignore dates.
5. Return description lines.
"""

import re

# ----------------------------------------------------
# Date Detection
# ----------------------------------------------------

def is_date(text):

    pattern = (
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
        r"|present"
        r"|current"
        r"|\d{4}"
    )

    return bool(
        re.search(
            pattern,
            text.lower()
        )
    )


# ----------------------------------------------------
# Company Detection
# ----------------------------------------------------

def is_company(text):

    keywords = [

        "inc",
        "llc",
        "ltd",
        "limited",
        "technologies",
        "technology",
        "solutions",
        "software",
        "systems",
        "corporation",
        "corp",
        "university",
        "college",
        "institute",
        "school"

    ]

    lower = text.lower()

    return any(
        keyword in lower
        for keyword in keywords
    )


# ----------------------------------------------------
# Title Detection
# ----------------------------------------------------

def looks_like_title(text):

    title_keywords = [

        "engineer",
        "developer",
        "scientist",
        "manager",
        "analyst",
        "assistant",
        "intern",
        "consultant",
        "specialist",
        "architect",
        "administrator",
        "designer",
        "lead"

    ]

    lower = text.lower()

    return any(
        keyword in lower
        for keyword in title_keywords
    )


# ----------------------------------------------------
# Description Extractor
# ----------------------------------------------------

def extract_description(experience_block):
    """
    Parameters
    ----------
    experience_block : list[str]

    Returns
    -------
    list[str]
    """

    if not experience_block:
        return []

    # Flatten if nested
    if (
        isinstance(experience_block, list)
        and experience_block
        and isinstance(experience_block[0], list)
    ):
        experience_block = experience_block[0]

    descriptions = []

    for line in experience_block:

        if not isinstance(line, str):
            continue

        line = line.strip()

        if not line:
            continue

        # Skip title
        if looks_like_title(line):
            continue

        # Skip company
        if is_company(line):
            continue

        # Skip date line
        if is_date(line):
            continue

        descriptions.append(line)

    return descriptions