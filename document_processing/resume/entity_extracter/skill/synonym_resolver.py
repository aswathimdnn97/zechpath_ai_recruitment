import json
from pathlib import Path


# -------------------------------------------------------
# Project Root
# -------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ALIAS_FILE = (
    PROJECT_ROOT /
   "data"/"resume"/"skills"/"skill_aliases.json"
)


# -------------------------------------------------------
# Load Alias Dictionary
# -------------------------------------------------------

def load_skill_aliases():
    """
    Load skill alias dictionary.

    Returns
    -------
    dict
    """

    with open(ALIAS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# -------------------------------------------------------
# Resolve Synonyms
# -------------------------------------------------------

def resolve_synonyms(candidate_skills):
    """
    Convert skill aliases into canonical skill names.

    Parameters
    ----------
    candidate_skills : list[str]

    Returns
    -------
    list[str]
    """

    if not isinstance(candidate_skills, list):
        raise TypeError(
            "candidate_skills must be a list."
        )

    aliases = load_skill_aliases()

    resolved = []

    for skill in candidate_skills:

        if not isinstance(skill, str):
            continue

        original = skill.strip()

        if not original:
            continue

        lookup = original.lower()

        canonical = aliases.get(
            lookup,
            original
        )

        resolved.append(canonical)

    return resolved


# -------------------------------------------------------
# Testing
# -------------------------------------------------------

if __name__ == "__main__":

    skills = [

        "MERN Stack",
        "javascript (es6 )",
        "ReactJS",
        "NodeJS",
        "Mongo DB",
        "REST APIs",
        "JWT Authentication",
        "GitHub",
        "Python3"

    ]

    result = resolve_synonyms(skills)

    print(result)
    
print(Path(__file__).resolve())
print(PROJECT_ROOT)
print(ALIAS_FILE)