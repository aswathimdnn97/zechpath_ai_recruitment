"""
department_extractor.py

Responsibilities
----------------
1. Identify department from experience block.
2. Use title and description keywords.
3. Return structured department object.
"""

import json
from pathlib import Path


# ----------------------------------------------------
# Project Root
# ----------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ----------------------------------------------------
# Department Dictionary
# ----------------------------------------------------

DEPARTMENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "department"
    / "department_dictionary.json"
)

# ----------------------------------------------------
# Load Departments
# ----------------------------------------------------

def load_departments():

    with open(
        DEPARTMENT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)



# ----------------------------------------------------
# Extract Department
# ----------------------------------------------------

def extract_department(experience_block):

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

            "department_id": None,

            "department": "Unknown",

            "confidence": 0

        }


    # Flatten nested list

    if (
        isinstance(experience_block, list)
        and isinstance(
            experience_block[0],
            list
        )
    ):

        experience_block = experience_block[0]


    departments = load_departments()


    # Combine block text

    text = " ".join(
        experience_block
    ).lower()



    best_match = None

    highest_score = 0



    for department in departments:


        score = 0


        for keyword in department["keywords"]:


            if keyword.lower() in text:

                score += 1



        if score > highest_score:

            highest_score = score

            best_match = department



    if best_match:


        confidence = min(
            highest_score * 25,
            100
        )


        return {

            "department_id":
                best_match["department_id"],

            "department":
                best_match["name"],

            "matched_by":
                "keyword",

            "confidence":
                confidence

        }



    return {

        "department_id": None,

        "department": "Unknown",

        "matched_by": "none",

        "confidence": 0

    }