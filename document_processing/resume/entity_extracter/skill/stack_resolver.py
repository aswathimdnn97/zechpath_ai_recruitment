"""
stack_resolver.py

Responsibilities
-----------------
1. Keep the original detected skill.
2. Expand known technology stacks.
3. Validate expanded skills against the master skill dictionary.
4. Preserve master skill metadata.
5. Preserve source evidence.
6. Prevent duplicate skills.
7. Support case-insensitive stack matching.

Pipeline position
-----------------
master_skill_validator.py
        ↓
stack_resolver.py
        ↓
final candidate skills
"""

import json
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]


STACK_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "skill_stacks.json"
)


MASTER_SKILL_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "master_skill_dictionary.json"
)


# ============================================================
# LOAD SKILL STACKS
# ============================================================

def load_skill_stacks():
    """
    Load technology stack definitions.

    Example:

        {
            "MERN": [
                "MongoDB",
                "Express",
                "React",
                "Node.js"
            ]
        }

    Returns
    -------
    dict
    """

    if not STACK_FILE.exists():
        return {}

    with open(
        STACK_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    if not isinstance(data, dict):
        return {}

    return data


# ============================================================
# LOAD MASTER SKILLS
# ============================================================

def load_master_skills():
    """
    Load active skills from the master skill dictionary.

    Returns
    -------
    list[dict]
    """

    if not MASTER_SKILL_FILE.exists():
        return []

    with open(
        MASTER_SKILL_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    if not isinstance(data, list):
        return []

    return [
        skill
        for skill in data
        if isinstance(skill, dict)
        and skill.get("status") == "active"
        and skill.get("skill_id")
        and skill.get("name")
    ]


# ============================================================
# NORMALIZE TEXT
# ============================================================

def _normalize(value):
    """
    Normalize a skill name for comparison.
    """

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


# ============================================================
# BUILD STACK MAP
# ============================================================

def _build_stack_map(stack_dictionary):
    """
    Build case-insensitive stack lookup.

    Example:

        {
            "mern": [
                "MongoDB",
                "Express",
                "React",
                "Node.js"
            ]
        }
    """

    stack_map = {}

    for stack_name, stack_skills in stack_dictionary.items():

        normalized_stack = _normalize(
            stack_name
        )

        if not normalized_stack:
            continue

        if not isinstance(
            stack_skills,
            list
        ):
            continue

        stack_map[
            normalized_stack
        ] = stack_skills

    return stack_map


# ============================================================
# BUILD MASTER SKILL LOOKUP
# ============================================================

def _build_master_skill_lookup(master_skills):
    """
    Build:

        normalized skill name
            ↓
        master skill object
    """

    lookup = {}

    for skill in master_skills:

        name = skill.get("name")

        normalized_name = _normalize(
            name
        )

        if not normalized_name:
            continue

        lookup[
            normalized_name
        ] = skill

    return lookup


# ============================================================
# BUILD EXPANDED SKILL OBJECT
# ============================================================

def _build_expanded_skill(
    master_skill,
    source_skill,
    source_section,
    confidence
):
    """
    Build a normal ATS skill object for a skill
    produced by stack expansion.
    """

    return {

        "skill_id":
            master_skill.get(
                "skill_id"
            ),

        "skill":
            master_skill.get(
                "name"
            ),

        "category":
            master_skill.get(
                "category",
                "Unknown"
            ),

        "subcategory":
            master_skill.get(
                "subcategory",
                "Unknown"
            ),

        "matched_by":
            "stack",

        "confidence":
            confidence,

        "source_section":
            source_section,

        "source_skill":
            source_skill
    }


# ============================================================
# EXPAND SKILL STACKS
# ============================================================

def expand_skill_stacks(validated_skills):
    """
    Expand technology stack names into individual
    master-dictionary skills.

    The original stack is always preserved.

    Example
    -------

    Input:

        [
            {
                "skill_id": "TECH100",
                "skill": "MERN",
                "category": "Technical",
                "subcategory": "Full Stack",
                "matched_by": "exact",
                "confidence": 100,
                "source_section": "projects"
            }
        ]

    Output:

        [
            {
                "skill_id": "TECH100",
                "skill": "MERN",
                ...
            },
            {
                "skill_id": "TECH101",
                "skill": "MongoDB",
                "matched_by": "stack",
                "source_skill": "MERN",
                ...
            },
            ...
        ]

    Parameters
    ----------
    validated_skills : list[dict]

    Returns
    -------
    list[dict]
    """

    if not isinstance(
        validated_skills,
        list
    ):
        return []

    if not validated_skills:
        return []

    # --------------------------------------------------------
    # Load dictionaries
    # --------------------------------------------------------

    stack_dictionary = load_skill_stacks()

    master_skills = load_master_skills()

    # --------------------------------------------------------
    # Build lookups
    # --------------------------------------------------------

    stack_map = _build_stack_map(
        stack_dictionary
    )

    master_lookup = _build_master_skill_lookup(
        master_skills
    )

    expanded = []

    # Prevent duplicate master skills
    seen_skill_ids = set()

    # Also protect against duplicate names
    seen_skill_names = set()

    # ========================================================
    # PROCESS VALIDATED SKILLS
    # ========================================================

    for skill_object in validated_skills:

        if not isinstance(
            skill_object,
            dict
        ):
            continue

        skill_name = skill_object.get(
            "skill"
        )

        if not skill_name:
            continue

        skill_name = str(
            skill_name
        ).strip()

        if not skill_name:
            continue

        normalized_skill = _normalize(
            skill_name
        )

        # ----------------------------------------------------
        # Source information
        # ----------------------------------------------------

        source_section = (
            skill_object.get(
                "source_section",
                "unknown"
            )
        )

        confidence = (
            skill_object.get(
                "confidence",
                0
            )
        )

        # ====================================================
        # 1. KEEP ORIGINAL SKILL
        # ====================================================

        skill_id = skill_object.get(
            "skill_id"
        )

        if skill_id:

            if skill_id not in seen_skill_ids:

                expanded.append(
                    skill_object
                )

                seen_skill_ids.add(
                    skill_id
                )

                seen_skill_names.add(
                    normalized_skill
                )

        else:

            # ------------------------------------------------
            # Fallback for a skill without ID.
            # ------------------------------------------------

            if normalized_skill not in seen_skill_names:

                expanded.append(
                    skill_object
                )

                seen_skill_names.add(
                    normalized_skill
                )

        # ====================================================
        # 2. CHECK WHETHER IT IS A STACK
        # ====================================================

        stack_skills = stack_map.get(
            normalized_skill,
            []
        )

        if not stack_skills:
            continue

        # ====================================================
        # 3. EXPAND STACK
        # ====================================================

        for stack_skill in stack_skills:

            if not stack_skill:
                continue

            stack_skill = str(
                stack_skill
            ).strip()

            if not stack_skill:
                continue

            normalized_stack_skill = _normalize(
                stack_skill
            )

            # ------------------------------------------------
            # Prevent duplicate
            # ------------------------------------------------

            if (
                normalized_stack_skill
                in seen_skill_names
            ):
                continue

            # ------------------------------------------------
            # Find expanded skill in master dictionary
            # ------------------------------------------------

            master_skill = master_lookup.get(
                normalized_stack_skill
            )

            # ------------------------------------------------
            # IMPORTANT:
            #
            # Do not add unknown stack skills.
            #
            # The master dictionary remains the
            # single source of truth.
            # ------------------------------------------------

            if not master_skill:
                continue

            expanded_skill = _build_expanded_skill(
                master_skill=master_skill,
                source_skill=skill_name,
                source_section=source_section,
                confidence=confidence
            )

            expanded.append(
                expanded_skill
            )

            # ------------------------------------------------
            # Track duplicates
            # ------------------------------------------------

            expanded_skill_id = (
                master_skill.get(
                    "skill_id"
                )
            )

            if expanded_skill_id:
                seen_skill_ids.add(
                    expanded_skill_id
                )

            seen_skill_names.add(
                normalized_stack_skill
            )

    return expanded


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    validated = [

        {
            "skill_id": "TECH100",
            "skill": "MERN",
            "category": "Technical",
            "subcategory": "Full Stack",
            "matched_by": "exact",
            "confidence": 100,
            "source_section": "projects"
        },

        {
            "skill_id": "TECH001",
            "skill": "Python",
            "category": "Technical",
            "subcategory": "Programming Language",
            "matched_by": "exact",
            "confidence": 100,
            "source_section": "experience"
        }
    ]

    result = expand_skill_stacks(
        validated
    )

    print(
        "\n========== EXPANDED SKILLS ==========\n"
    )

    for skill in result:
        print(skill)
