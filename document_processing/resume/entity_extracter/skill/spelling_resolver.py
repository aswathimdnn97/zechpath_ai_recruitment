"""
spelling_resolver.py

Correct misspelled candidate skills using
spelling_dictionary.json.
"""

import json
from pathlib import Path


# -------------------------------------------------------
# Locate spelling_dictionary.json
# -------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

SPELLING_FILE = PROJECT_ROOT / "data"/"resume"/ "skills" / "spelling_dictionary.json"


# -------------------------------------------------------
# Load spelling dictionary
# -------------------------------------------------------

def load_spelling_dictionary():
    """
    Load spelling corrections.

    Returns
    -------
    dict
    """

    with open(SPELLING_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# -------------------------------------------------------
# Correct candidate skills
# -------------------------------------------------------

def resolve_spelling(candidate_skills):
    """
    Correct misspelled skills.

    Parameters
    ----------
    candidate_skills : list[str]

    Returns
    -------
    list[str]
    """

    if not candidate_skills:
        return []

    spelling_dict = load_spelling_dictionary()

    # Case-insensitive lookup
    lookup = {
        wrong.lower(): correct
        for wrong, correct in spelling_dict.items()
    }

    corrected_skills = []

    for skill in candidate_skills:

        skill = skill.strip()

        corrected_skill = lookup.get(
            skill.lower(),
            skill
        )

        corrected_skills.append(corrected_skill)

    # Remove duplicates while preserving order
    return list(dict.fromkeys(corrected_skills))


# -------------------------------------------------------
# Test
# -------------------------------------------------------

if __name__ == "__main__":

    skills = [
        "Pyhton",
        "ReactJS",
        "Aws",
        "Dockerr",
        "Git"
    ]

    print(resolve_spelling(skills))