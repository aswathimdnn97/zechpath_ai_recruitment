"""
location_extractor.py

Responsibilities
----------------
1. Extract candidate job location.
2. Ignore title.
3. Ignore company.
4. Ignore description.
5. Return raw location.
"""

import json
from pathlib import Path


# ----------------------------------------------------
# Project Root
# ----------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ----------------------------------------------------
# Location Dictionary
# ----------------------------------------------------

LOCATION_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "locations"
    / "location_dictionary.json"
)


# ----------------------------------------------------
# Load Locations
# ----------------------------------------------------

def load_locations():

    with open(
        LOCATION_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)



# ----------------------------------------------------
# Date Detection
# ----------------------------------------------------

def contains_date(text):

    months = [

        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec"

    ]

    lower = text.lower()

    # Use word-boundary matching for month abbreviations and 4-digit years
    import re
    pattern = r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b|\b\d{4}\b"

    return bool(re.search(pattern, lower))



# ----------------------------------------------------
# Location Extraction
# ----------------------------------------------------

def extract_location(experience_block):

    """
    Parameters
    ----------
    experience_block : list[str]

    Returns
    -------
    str | None
    """


    if not experience_block:

        return None



    # Flatten nested list

    if (
        isinstance(experience_block, list)
        and isinstance(
            experience_block[0],
            list
        )
    ):

        experience_block = experience_block[0]



    locations = load_locations()



    for line in experience_block:


        if not isinstance(line, str):

            continue


        line = line.strip()


        if not line:

            continue



        # If the line contains a date, strip the date part (common pattern: 'Location | Jan 2020 - Present')
        candidate_line = line

        if "|" in line:
            candidate_line = line.split("|")[0].strip()
        else:
            # remove date tokens if present
            import re
            date_pattern = r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b.*|\b\d{4}\b"
            candidate_line = re.sub(date_pattern, "", line, flags=re.IGNORECASE).strip(" -–—,\t\n")



        # Location dictionary match

        for location in locations:


            if location.lower() in line.lower():


                return location



    return None