from typing import Dict, List, Any


# ============================================================
# Skill Group Weights
# ============================================================

REQUIRED_WEIGHT = 0.80
PREFERRED_WEIGHT = 0.20


# ============================================================
# Helper
# ============================================================

def normalize_skill(skill: Any) -> str:
    """
    Convert a skill value into normalized string form.

    Supports:
        "Python"
        {"name": "Python"}
        {"skill": "Python"}
        {"canonical_name": "Python"}
    """

    if skill is None:
        return ""

    if isinstance(skill, dict):

        skill = (
            skill.get("name")
            or skill.get("skill")
            or skill.get("canonical_name")
            or ""
        )

    return str(skill).strip().lower()


# ============================================================
# Extract Skill Names
# ============================================================

def normalize_skill_list(
    skills: List[Any]
) -> List[str]:

    if not skills:
        return []

    normalized = []

    for skill in skills:

        name = normalize_skill(skill)

        if name:
            normalized.append(name)

    return normalized


# ============================================================
# Build JD Skill Importance
# ============================================================

def build_skill_weights(
    required_skills: List[Any],
    preferred_skills: List[Any],
) -> Dict[str, float]:
    """
    Assign importance based on JD skill groups.

    Required skills collectively receive 80%.
    Preferred skills collectively receive 20%.

    This function does NOT hardcode any technology.
    """

    required = normalize_skill_list(
        required_skills
    )

    preferred = normalize_skill_list(
        preferred_skills
    )

    weights = {}

    # --------------------------------------------------------
    # Required skills
    # --------------------------------------------------------

    if required:

        required_skill_weight = (
            REQUIRED_WEIGHT / len(required)
        )

        for skill in required:

            weights[skill] = required_skill_weight

    # --------------------------------------------------------
    # Preferred skills
    # --------------------------------------------------------

    if preferred:

        preferred_skill_weight = (
            PREFERRED_WEIGHT / len(preferred)
        )

        for skill in preferred:

            # Don't overwrite a required skill.
            if skill not in weights:

                weights[skill] = (
                    preferred_skill_weight
                )

    return weights


# ============================================================
# Build Detailed Importance Information
# ============================================================

def get_skill_importance_details(
    required_skills: List[Any],
    preferred_skills: List[Any],
) -> Dict[str, Any]:

    required = normalize_skill_list(
        required_skills
    )

    preferred = normalize_skill_list(
        preferred_skills
    )

    weights = build_skill_weights(
        required,
        preferred,
    )

    return {
        "required_weight": REQUIRED_WEIGHT,
        "preferred_weight": PREFERRED_WEIGHT,

        "required_skill_count": len(required),

        "preferred_skill_count": len(preferred),

        "skill_weights": weights,
    }