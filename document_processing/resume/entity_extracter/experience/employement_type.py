"""
employment_type_extractor.py

Responsibilities
----------------
1. Extract employment type from experience block.
2. Detect keywords.
3. Return structured employment type.
"""

import json
from pathlib import Path


# ----------------------------------------------------
# Project Root
# ----------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ----------------------------------------------------
# Employment Type File
# ----------------------------------------------------

EMPLOYMENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "employment"
    / "employment_types.json"
)


# ----------------------------------------------------
# Load Employment Types
# ----------------------------------------------------

def load_employment_types():

    with open(
        EMPLOYMENT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)



# ----------------------------------------------------
# Extract Employment Type
# ----------------------------------------------------

def extract_employment_type(experience_block):

    """
    Parameters
    ----------
    experience_block : list[str]

    Returns
    -------
    dict | None
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



    employment_types = load_employment_types()



    keyword_map = {

        "intern": "Internship",

        "internship": "Internship",

        "full time": "Full-time",

        "full-time": "Full-time",

        "part time": "Part-time",

        "part-time": "Part-time",

        "contract": "Contract",

        "freelance": "Freelance",

        "consultant": "Contract",

        "volunteer": "Volunteer",

        "training": "Training",

        "bootcamp": "Training",

        "research assistant": "Research"

    }



    for line in experience_block:


        if not isinstance(line, str):

            continue


        text = line.lower()



        for keyword, value in keyword_map.items():


            if keyword in text:


                for emp in employment_types:


                    if emp["name"] == value:


                        return {

                            "type_id":
                                emp["type_id"],

                            "employment_type":
                                emp["name"],

                            "matched_by":
                                "keyword",

                            "confidence":
                                100

                        }


    return {

        "type_id": None,

        "employment_type": "Unknown",

        "matched_by": "none",

        "confidence": 0

    }