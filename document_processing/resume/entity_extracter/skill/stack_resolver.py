"""
stack_resolver.py

Expand technology stacks into their individual skills.
"""

import json
from pathlib import Path


# -------------------------------------------------------
# Project Root
# -------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

STACK_FILE = (
    PROJECT_ROOT /
    "data" /
    "skills" /
    "skill_stacks.json"
)


# -------------------------------------------------------
# Load Stack Dictionary
# -------------------------------------------------------

def load_skill_stacks():
    """
    Load skill stacks.

    Returns
    -------
    dict
    """

    with open(STACK_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# -------------------------------------------------------
# Expand Skill Stacks
# -------------------------------------------------------

def expand_skill_stacks(validated_skills):
    """
    Expand stack names into individual skills.

    Parameters
    ----------
    validated_skills : list[dict]

    Returns
    -------
    list[dict]
    """

    stack_dictionary = load_skill_stacks()

    expanded = []

    added = set()

    for skill_object in validated_skills:

        skill_name = skill_object["skill"]

        # ---------------------------------------
        # Add original skill
        # ---------------------------------------

        if skill_name.lower() not in added:

            expanded.append(skill_object)

            added.add(skill_name.lower())

        # ---------------------------------------
        # Expand stack
        # ---------------------------------------

        if skill_name in stack_dictionary:

            for stack_skill in stack_dictionary[skill_name]:

                if stack_skill.lower() in added:
                    continue

                expanded.append({

                    "skill_id": None,

                    "skill": stack_skill,

                    "category": "Technical",

                    "subcategory": "Stack Technology",

                    "matched_by": "stack",

                    "confidence": skill_object["confidence"]

                })

                added.add(stack_skill.lower())

    return expanded


# -------------------------------------------------------
# Testing
# -------------------------------------------------------

if __name__ == "__main__":

    validated = [

        {
            "skill_id": "TECH100",
            "skill": "MERN",
            "category": "Technical",
            "subcategory": "Full Stack",
            "matched_by": "exact",
            "confidence": 100
        },

        {
            "skill_id": "TECH001",
            "skill": "Python",
            "category": "Technical",
            "subcategory": "Programming Language",
            "matched_by": "exact",
            "confidence": 100
        }

    ]

    result = expand_skill_stacks(validated)

    for skill in result:
        print(skill)
        
from pathlib import Path

path = Path(__file__).resolve()

print(path)

print("STACK_RESOLVER FILE:", __file__)
print("PROJECT_ROOT:", PROJECT_ROOT)
print("STACK_FILE:", STACK_FILE)
print("STACK_FILE:", STACK_FILE)
print("Exists:", STACK_FILE.exists())