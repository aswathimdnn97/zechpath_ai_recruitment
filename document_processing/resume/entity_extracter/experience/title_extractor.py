"""
title_extractor.py

Responsibilities
----------------
1. Extract raw job titles from one experience block
2. Remove dates
3. Ignore company names
4. Ignore description lines
5. Return candidate job titles

No validation is performed here.
"""

import json
import re
from pathlib import Path

# ----------------------------------------------------
# Project Root
# ----------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

# ----------------------------------------------------
# Company Dictionary
# ----------------------------------------------------

COMPANY_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "companies"
    / "company_dictionary.json"
)

# ----------------------------------------------------
# Load Companies
# ----------------------------------------------------

def load_companies():

    with open(COMPANY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ----------------------------------------------------
# Remove Date
# ----------------------------------------------------

def remove_date(text):
    """
    Removes trailing date information.

    Example
    -------
    Software Engineer Jan 2022 - Present

    becomes

    Software Engineer
    """

    pattern = (
        r"\s*"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r".*"
    )

    return re.sub(
        pattern,
        "",
        text,
        flags=re.IGNORECASE
    ).strip()


# ----------------------------------------------------
# Description Detection
# ----------------------------------------------------

def is_description(text):

    keywords = [

        "developed",
        "worked",
        "responsible",
        "implemented",
        "created",
        "designed",
        "using",
        "maintained",
        "improved",
        "enhanced",
        "built",
        "communicate",
        "assess",
        "troubleshoot",
        "contributed",
        "explored",
        "presented",
        "wrote",
        "managed",
        "tested"

    ]

    text = text.lower()

    return any(
        word in text
        for word in keywords
    )


# ----------------------------------------------------
# Extract Titles
# ----------------------------------------------------

def extract_titles(experience_block):
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

    # Flatten one level if needed
    if (
        isinstance(experience_block, list)
        and experience_block
        and isinstance(experience_block[0], list)
    ):
        experience_block = experience_block[0]

    company_lookup = {

        company["name"].lower()

        for company in load_companies()

    }

    titles = []

    seen = set()

    for line in experience_block:

        line = line.strip()

        if not line:
            continue

        # Skip description lines
        if is_description(line):
            continue

        # Remove dates
        line = remove_date(line)

        if not line:
            continue

        lower = line.lower()

        # Skip if exactly a company
        if lower in company_lookup:
            continue

        # Skip if location-like
        if "," in line and len(line.split()) > 2:
            continue

        if lower not in seen:

            seen.add(lower)

            titles.append(line)

    return titles