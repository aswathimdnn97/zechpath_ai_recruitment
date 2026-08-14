from typing import Any, Dict, List


def _normalize_skill(skill: str) -> str:
    """Normalize skill names for case-insensitive comparison."""

    if not isinstance(skill, str):
        return ""

    return " ".join(
        skill.lower().strip().split()
    )


def _extract_skill_names(skills: Any) -> List[str]:
    """
    Convert candidate/JD skills into normalized names.

    Supports:

        ["Python", "Django"]

    and:

        [
            {"skill": "Python"},
            {"skill": "Django"}
        ]
    """

    if not isinstance(skills, list):
        return []

    result = []

    for skill in skills:

        if isinstance(skill, str):

            name = skill

        elif isinstance(skill, dict):

            name = (
                skill.get("skill")
                or skill.get("name")
                or skill.get("canonical_name")
            )

        else:
            continue

        normalized = _normalize_skill(name)

        if normalized:
            result.append(normalized)

    # Remove duplicates
    return list(dict.fromkeys(result))


def _get_profile_data(
    profile: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(profile, dict):
        return {}

    resume_data = profile.get("resume_text")

    if isinstance(resume_data, dict):
        return resume_data

    return profile


def calculate_skill_score(
    candidate_profile: Dict[str, Any],
    jd_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate ATS skill score.

    Required skills  = 80%
    Preferred skills = 20%
    """

    candidate_data = _get_profile_data(
        candidate_profile
    )

    jd_data = _get_profile_data(
        jd_profile
    )

    # --------------------------------------------------------
    # Candidate skills
    # --------------------------------------------------------

    candidate_skills = _extract_skill_names(
        candidate_data.get("skills", [])
    )

    # --------------------------------------------------------
    # JD skills
    # --------------------------------------------------------

    required_skills = _extract_skill_names(
        jd_data.get("required_skills", [])
    )

    preferred_skills = _extract_skill_names(
        jd_data.get("preferred_skills", [])
    )

    candidate = set(candidate_skills)
    required = set(required_skills)
    preferred = set(preferred_skills)

    # --------------------------------------------------------
    # Required matching
    # --------------------------------------------------------

    matched_required = sorted(
        candidate.intersection(required)
    )

    missing_required = sorted(
        required - candidate
    )

    # --------------------------------------------------------
    # Preferred matching
    # --------------------------------------------------------

    matched_preferred = sorted(
        candidate.intersection(preferred)
    )

    missing_preferred = sorted(
        preferred - candidate
    )

    # --------------------------------------------------------
    # Required score
    # --------------------------------------------------------

    if required:

        required_score = (
            len(matched_required)
            / len(required)
        ) * 100

    else:

        required_score = None

    # --------------------------------------------------------
    # Preferred score
    # --------------------------------------------------------

    if preferred:

        preferred_score = (
            len(matched_preferred)
            / len(preferred)
        ) * 100

    else:

        preferred_score = None

    # --------------------------------------------------------
    # Final skill score
    # --------------------------------------------------------

    if (
        required_score is not None
        and preferred_score is not None
    ):

        final_score = (
            required_score * 0.80
            + preferred_score * 0.20
        )

    elif required_score is not None:

        final_score = required_score

    elif preferred_score is not None:

        final_score = preferred_score

    else:

        final_score = 0.0

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    if not candidate:
        status = "no_data"

    elif not required and not preferred:
        status = "no_requirements"

    else:
        status = "calculated"

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    return {

        "score": round(
            final_score,
            2
        ),

        "required_score": (
            round(required_score, 2)
            if required_score is not None
            else None
        ),

        "preferred_score": (
            round(preferred_score, 2)
            if preferred_score is not None
            else None
        ),

        "required_total": len(required),

        "required_matched": len(
            matched_required
        ),

        "required_match_percentage": (
            round(required_score, 2)
            if required_score is not None
            else None
        ),

        "matched_required_skills":
            matched_required,

        "missing_required_skills":
            missing_required,

        "preferred_total": len(preferred),

        "preferred_matched": len(
            matched_preferred
        ),

        "preferred_match_percentage": (
            round(preferred_score, 2)
            if preferred_score is not None
            else None
        ),

        "matched_preferred_skills":
            matched_preferred,

        "missing_preferred_skills":
            missing_preferred,

        "candidate_skill_count":
            len(candidate),

        "status": status,
    }