"""
master_skill_validator.py

Responsibilities
----------------
1. Load master_skill_dictionary.json
2. Validate extracted skills
3. Exact matching
4. Fuzzy matching
5. Calculate confidence score
6. Return structured skill objects
"""

import json
from pathlib import Path

from rapidfuzz import process, fuzz


# -------------------------------------------------------
# Project Root
# -------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

MASTER_SKILL_FILE = (
    PROJECT_ROOT /
    "data"/
    "skills" /
    "master_skill_dictionary.json"
)


# -------------------------------------------------------
# Load Master Skill Dictionary
# -------------------------------------------------------

def load_master_skill_dictionary():
    """
    Returns
    -------
    list[dict]
    """

    with open(
        MASTER_SKILL_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# -------------------------------------------------------
# Validate Skills
# -------------------------------------------------------

def validate_skills(
    candidate_skills,
    threshold=90
):
    """
    Validate extracted skills.

    Parameters
    ----------
    candidate_skills : list[str]

    threshold : int

    Returns
    -------
    list[dict]
    """

    master_skills = load_master_skill_dictionary()

    # Dictionary for Exact Match

    exact_lookup = {}

    for skill in master_skills:

        exact_lookup[
            skill["name"].lower()
        ] = skill

    # List of Canonical Skill Names

    skill_names = [
        skill["name"]
        for skill in master_skills
    ]

    validated = []

    for candidate in candidate_skills:

        candidate = candidate.strip()

        # ----------------------------------------
        # Exact Match
        # ----------------------------------------

        if candidate.lower() in exact_lookup:

            skill = exact_lookup[
                candidate.lower()
            ]

            validated.append({

                "skill_id":
                    skill["skill_id"],

                "skill":
                    skill["name"],

                "category":
                    skill["category"],

                "subcategory":
                    skill["subcategory"],

                "matched_by":
                    "exact",

                "confidence":
                    100

            })

            continue

        # ----------------------------------------
        # Fuzzy Match
        # ----------------------------------------

        result = process.extractOne(

            candidate,

            skill_names,

            scorer=fuzz.WRatio

        )

        if result:

            best_skill = result[0]

            score = result[1]

            if score >= threshold:

                skill = exact_lookup[
                    best_skill.lower()
                ]

                validated.append({

                    "skill_id":
                        skill["skill_id"],

                    "skill":
                        skill["name"],

                    "category":
                        skill["category"],

                    "subcategory":
                        skill["subcategory"],

                    "matched_by":
                        "fuzzy",

                    "confidence":
                        round(score)

                })

                continue

        # ----------------------------------------
        # Unknown Skill
        # ----------------------------------------

        validated.append({

            "skill_id": None,

            "skill": candidate,

            "category": "Unknown",

            "subcategory": "Unknown",

            "matched_by": "none",

            "confidence": 0

        })

    return validated