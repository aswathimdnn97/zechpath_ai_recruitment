"""
skill_extractor_from_experience.py

Responsibilities
-----------------
1. Extract skills from experience description.
2. Match against master skill dictionary.
3. Resolve skill aliases.
4. Return structured skills.
"""

import json
import re
from pathlib import Path


# ----------------------------------------------------
# Project Root
# ----------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ----------------------------------------------------
# Skill Dictionary
# ----------------------------------------------------

SKILL_FILE = (
    PROJECT_ROOT
    / "data"
    / "skills"
    / "master_skill_dictionary.json"
)


ALIAS_FILE = (
    PROJECT_ROOT
    / "data"
    / "skills"
    / "skill_aliases.json"
)


# ----------------------------------------------------
# Load Skills
# ----------------------------------------------------

def load_skills():

    with open(
        SKILL_FILE,
        encoding="utf-8"
    ) as file:

        return json.load(file)



def load_aliases():

    with open(
        ALIAS_FILE,
        encoding="utf-8"
    ) as file:

        return json.load(file)



# ----------------------------------------------------
# Normalize Text
# ----------------------------------------------------

def normalize_text(text):

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9+#.]",
        " ",
        text
    )

    return text



# ----------------------------------------------------
# Find Skill Details
# ----------------------------------------------------

def get_skill_details(skill_name, skills):

    for skill in skills:

        if (
            skill["name"].lower()
            ==
            skill_name.lower()
        ):

            return skill

    return None



# ----------------------------------------------------
# Skill Match
# ----------------------------------------------------

def skill_exists(text, skill):

    pattern = (
        r"\b"
        +
        re.escape(
            skill.lower()
        )
        +
        r"\b"
    )

    return bool(
        re.search(
            pattern,
            text
        )
    )



# ----------------------------------------------------
# Extract Skills
# ----------------------------------------------------

def extract_skills_from_experience(experience_block):

    """
    Parameters
    ----------
    experience_block : list[str]

    Returns
    -------
    list[dict]
    """


    if not experience_block:

        return []


    # Flatten nested list

    if (
        isinstance(experience_block, list)
        and isinstance(
            experience_block[0],
            list
        )
    ):

        experience_block = experience_block[0]



    skills = load_skills()

    aliases = load_aliases()



    # Combine description

    text = " ".join(
        experience_block
    )


    text = normalize_text(text)



    extracted = []

    seen = set()



    # --------------------------------
    # Alias Matching
    # --------------------------------

    for alias, canonical in aliases.items():


        if skill_exists(
            text,
            alias
        ):


            if canonical.lower() in seen:

                continue



            seen.add(
                canonical.lower()
            )


            skill_details = get_skill_details(
                canonical,
                skills
            )


            if skill_details:


                extracted.append({

                    "skill_id":
                        skill_details["skill_id"],

                    "skill":
                        skill_details["name"],

                    "category":
                        skill_details.get(
                            "category",
                            "Unknown"
                        ),

                    "matched_by":
                        "alias",

                    "confidence":
                        95

                })


            else:


                extracted.append({

                    "skill_id":
                        None,

                    "skill":
                        canonical,

                    "category":
                        "Unknown",

                    "matched_by":
                        "alias",

                    "confidence":
                        95

                })



    # --------------------------------
    # Exact Master Dictionary Matching
    # --------------------------------

    for skill in skills:


        name = skill["name"]


        if skill_exists(
            text,
            name
        ):


            if name.lower() in seen:

                continue



            seen.add(
                name.lower()
            )


            extracted.append({

                "skill_id":
                    skill["skill_id"],

                "skill":
                    name,

                "category":
                    skill.get(
                        "category",
                        "Unknown"
                    ),

                "matched_by":
                    "exact",

                "confidence":
                    100

            })


    return extracted