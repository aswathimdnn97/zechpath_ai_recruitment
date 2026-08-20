"""
master_skill_validator.py

Responsibilities
----------------
1. Load master_skill_dictionary.json
2. Validate extracted skills
3. Perform exact matching
4. Perform fuzzy matching
5. Calculate confidence score
6. Return only valid master skills
7. Reject unknown/non-skill text
"""

import json
from pathlib import Path

from rapidfuzz import process, fuzz


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]


MASTER_SKILL_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "master_skill_dictionary.json"
)


# ============================================================
# LOAD MASTER SKILL DICTIONARY
# ============================================================

def load_master_skill_dictionary():
    """
    Load active skills from master_skill_dictionary.json.

    Returns
    -------
    list[dict]
        Active master skill records.
    """

    if not MASTER_SKILL_FILE.exists():
        raise FileNotFoundError(
            f"Master skill dictionary not found: "
            f"{MASTER_SKILL_FILE}"
        )

    with open(
        MASTER_SKILL_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)


    if not isinstance(data, list):
        raise ValueError(
            "master_skill_dictionary.json "
            "must contain a list of skills."
        )


    active_skills = []

    for skill in data:

        if not isinstance(skill, dict):
            continue

        if skill.get("status") != "active":
            continue

        if not skill.get("skill_id"):
            continue

        if not skill.get("name"):
            continue

        active_skills.append(skill)


    return active_skills


# ============================================================
# NORMALIZE SKILL TEXT
# ============================================================

def normalize_skill_text(skill):
    """
    Normalize extracted skill text before matching.
    """

    if not isinstance(skill, str):
        return ""

    return " ".join(
        skill.strip().split()
    ).lower()


# ============================================================
# BUILD EXACT LOOKUP
# ============================================================

def build_exact_lookup(master_skills):
    """
    Build:

        normalized skill name -> master skill
    """

    lookup = {}

    for skill in master_skills:

        name = skill.get("name")

        normalized_name = normalize_skill_text(
            name
        )

        if normalized_name:
            lookup[normalized_name] = skill

    return lookup


# ============================================================
# CREATE STRUCTURED RESULT
# ============================================================

def build_validated_skill(
    skill,
    matched_by,
    confidence
):
    """
    Convert master dictionary entry into
    ATS-ready skill object.
    """

    return {
        "skill_id": skill["skill_id"],
        "skill": skill["name"],
        "category": skill["category"],
        "subcategory": skill["subcategory"],
        "matched_by": matched_by,
        "confidence": confidence
    }


# ============================================================
# VALIDATE SKILLS
# ============================================================

def validate_skills(
    candidate_skills,
    threshold=90
):
    """
    Validate extracted skills against the
    master skill dictionary.

    Unknown skills are discarded.

    Parameters
    ----------
    candidate_skills : list[str]

    threshold : int
        Minimum fuzzy matching score.

    Returns
    -------
    list[dict]
        Only validated master skills.
    """

    if not candidate_skills:
        return []


    if not isinstance(
        candidate_skills,
        (list, tuple, set)
    ):
        raise TypeError(
            "candidate_skills must be a list, "
            "tuple, or set."
        )


    master_skills = load_master_skill_dictionary()


    # ========================================================
    # EXACT LOOKUP
    # ========================================================

    exact_lookup = build_exact_lookup(
        master_skills
    )


    # ========================================================
    # CANONICAL SKILL NAMES
    # ========================================================

    skill_names = [
        skill["name"]
        for skill in master_skills
    ]


    validated = []


    # Used to prevent duplicate skills
    seen_skill_ids = set()


    # ========================================================
    # PROCESS CANDIDATE SKILLS
    # ========================================================

    for candidate in candidate_skills:

        if not isinstance(
            candidate,
            str
        ):
            continue


        candidate = candidate.strip()


        if not candidate:
            continue


        normalized_candidate = normalize_skill_text(
            candidate
        )


        if not normalized_candidate:
            continue


        # ====================================================
        # EXACT MATCH
        # ====================================================

        if normalized_candidate in exact_lookup:

            skill = exact_lookup[
                normalized_candidate
            ]


            skill_id = skill["skill_id"]


            if skill_id in seen_skill_ids:
                continue


            validated.append(
                build_validated_skill(
                    skill=skill,
                    matched_by="exact",
                    confidence=100
                )
            )


            seen_skill_ids.add(
                skill_id
            )


            continue


        # ====================================================
        # FUZZY MATCH
        # ====================================================

        result = process.extractOne(
            candidate,
            skill_names,
            scorer=fuzz.WRatio
        )


        if result:

            best_skill_name = result[0]

            score = result[1]


            if score >= threshold:

                best_skill = exact_lookup[
                    normalize_skill_text(
                        best_skill_name
                    )
                ]


                skill_id = best_skill[
                    "skill_id"
                ]


                if skill_id in seen_skill_ids:
                    continue


                validated.append(
                    build_validated_skill(
                        skill=best_skill,
                        matched_by="fuzzy",
                        confidence=round(score)
                    )
                )


                seen_skill_ids.add(
                    skill_id
                )


                continue


        # ====================================================
        # UNKNOWN SKILL
        # ====================================================
        #
        # IMPORTANT:
        #
        # DO NOT append unknown skills.
        #
        # Example:
        #
        # "Won 4/4 hackathons"
        #
        # should NOT become:
        #
        # {
        #     "skill": "Won 4/4 hackathons",
        #     "category": "Unknown"
        # }
        #
        # ====================================================

        continue


    return validated