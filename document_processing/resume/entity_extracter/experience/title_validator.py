"""
title_validator.py

Responsibilities
----------------
1. Load master_job_titles.json
2. Validate extracted job titles
3. Exact matching
4. Fuzzy matching
5. Return structured title objects
"""

import json
from pathlib import Path

from rapidfuzz import process, fuzz


# ----------------------------------------------------
# Project Root
# ----------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ----------------------------------------------------
# Title Dictionary
# ----------------------------------------------------

TITLE_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "job_titles"
    / "master_job_titles.json"
)


# ----------------------------------------------------
# Load Titles
# ----------------------------------------------------

def load_job_titles():

    with open(
        TITLE_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)



# ----------------------------------------------------
# Validate Title
# ----------------------------------------------------

def validate_title(candidate_title, threshold=85):
    """
    Parameters
    ----------
    candidate_title : str

    Returns
    -------
    dict
    """

    if not candidate_title:

        return None


    candidate_title = candidate_title.strip()


    titles = load_job_titles()


    # -------------------------------
    # Exact Lookup
    # -------------------------------

    title_lookup = {

        title["name"].lower(): title

        for title in titles

    }


    # -------------------------------
    # Exact Match
    # -------------------------------

    if candidate_title.lower() in title_lookup:

        title = title_lookup[
            candidate_title.lower()
        ]

        return {

            "title_id":
                title["title_id"],

            "title":
                title["name"],

            "category":
                title.get(
                    "category",
                    "Unknown"
                ),

            "matched_by":
                "exact",

            "confidence":
                100
        }



    # -------------------------------
    # Fuzzy Match
    # -------------------------------

    title_names = [

        title["name"]

        for title in titles

    ]


    result = process.extractOne(

        candidate_title,

        title_names,

        scorer=fuzz.WRatio

    )


    if result:

        best_title = result[0]

        score = result[1]


        if score >= threshold:

            title = title_lookup[
                best_title.lower()
            ]


            return {

                "title_id":
                    title["title_id"],

                "title":
                    title["name"],

                "category":
                    title.get(
                        "category",
                        "Unknown"
                    ),

                "matched_by":
                    "fuzzy",

                "confidence":
                    round(score)

            }



    # -------------------------------
    # Unknown Title
    # -------------------------------

    return {

        "title_id": None,

        "title": candidate_title,

        "category": "Unknown",

        "matched_by": "none",

        "confidence": 0

    }