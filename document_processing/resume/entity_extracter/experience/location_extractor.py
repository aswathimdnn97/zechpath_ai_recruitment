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

    return any(
        month in lower
        for month in months
    ) or any(
        char.isdigit()
        for char in lower
    )



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



        # Skip dates

        if contains_date(line):

            continue



        # Location dictionary match

        for location in locations:


            if location.lower() in line.lower():


                return location



    return None