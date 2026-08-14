from typing import Any, Dict, List, Optional

from scoring.skill_score import calculate_skill_score
from scoring.experince_score import calculate_experience_score
from scoring.education_score import calculate_education_score
from scoring.semantic_scorer import calculate_semantic_score
from scoring.score_generator import generate_candidate_score


def _get_resume_text(
    candidate_profile: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(candidate_profile, dict):
        return {}

    resume_text = candidate_profile.get("resume_text")

    if isinstance(resume_text, dict):
        return resume_text

    return candidate_profile


def _get_jd_data(
    jd_profile: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(jd_profile, dict):
        return {}

    jd_data = jd_profile.get("resume_text")

    if isinstance(jd_data, dict):
        return jd_data

    return jd_profile


def _extract_candidate_skills(
    candidate_data: Dict[str, Any]
) -> List[Any]:

    skills = candidate_data.get("skills", [])

    if isinstance(skills, list):
        return skills

    return []


def _extract_candidate_years(
    candidate_data: Dict[str, Any]
) -> float:

    experience = candidate_data.get(
        "experience",
        []
    )

    if not isinstance(experience, list):
        return 0.0

    total_years = 0.0

    for item in experience:

        if not isinstance(item, dict):
            continue

        total_experience = item.get(
            "total_experience",
            {}
        )

        if isinstance(total_experience, dict):

            years = total_experience.get(
                "total_years"
            )

            if isinstance(
                years,
                (int, float)
            ):
                total_years = max(
                    total_years,
                    float(years)
                )

    return total_years


def _extract_candidate_roles(
    candidate_data: Dict[str, Any]
) -> List[str]:

    experience = candidate_data.get(
        "experience",
        []
    )

    if not isinstance(experience, list):
        return []

    roles = []

    for item in experience:

        if not isinstance(item, dict):
            continue

        title = (
            item.get("title")
            or item.get("job_title")
            or item.get("role")
        )

        # -----------------------------------------
        # Case 1: title is a string
        # -----------------------------------------

        if isinstance(title, str):

            if title.strip():
                roles.append(title.strip())

        # -----------------------------------------
        # Case 2: title is structured dictionary
        # -----------------------------------------

        elif isinstance(title, dict):

            title_name = (
                title.get("title")
                or title.get("name")
                or title.get("job_title")
            )

            if (
                isinstance(title_name, str)
                and title_name.strip()
            ):
                roles.append(
                    title_name.strip()
                )

    # Remove duplicates while preserving order

    return list(
        dict.fromkeys(roles)
    )


def _extract_candidate_education(
    candidate_data: Dict[str, Any]
) -> str:

    education = candidate_data.get(
        "education",
        []
    )

    if isinstance(education, str):
        return education

    if not isinstance(education, list):
        return ""

    education_parts = []

    for item in education:

        if isinstance(item, str):

            education_parts.append(item)

        elif isinstance(item, dict):

            for key in (
                "degree",
                "course",
                "field",
                "institution",
                "name",
            ):

                value = item.get(key)

                if (
                    isinstance(value, str)
                    and value.strip()
                ):
                    education_parts.append(
                        value.strip()
                    )

    return " ".join(
        education_parts
    )


def calculate_ats_score(
    candidate_profile: Dict[str, Any],
    jd_profile: Dict[str, Any],
    resume_embedding: Optional[List[float]] = None,
    jd_embedding: Optional[List[float]] = None,
    custom_weights: Optional[
        Dict[str, float]
    ] = None,
) -> Dict[str, Any]:
    """
    Calculate the complete ATS score.

    Pipeline:

        Candidate + JD
              |
              +-- Skill scorer
              |
              +-- Experience scorer
              |
              +-- Education scorer
              |
              +-- Semantic scorer
              |
              v
        Score generator
              |
              v
        Final ATS result
    """

    candidate_data = _get_resume_text(
        candidate_profile
    )

    jd_data = _get_jd_data(
        jd_profile
    )

    # ========================================================
    # Candidate data
    # ========================================================

    candidate_skills = (
        _extract_candidate_skills(
            candidate_data
        )
    )

    candidate_years = (
        _extract_candidate_years(
            candidate_data
        )
    )

    candidate_roles = (
        _extract_candidate_roles(
            candidate_data
        )
    )

    candidate_education = (
        _extract_candidate_education(
            candidate_data
        )
    )

    # ========================================================
    # JD data
    # ========================================================

    job_title = jd_data.get(
        "job_title",
        ""
    )

    if not isinstance(job_title, str):
        job_title = ""

    required_skills = jd_data.get(
        "required_skills",
        []
    )

    if not isinstance(required_skills, list):
        required_skills = []

    preferred_skills = jd_data.get(
        "preferred_skills",
        []
    )

    if not isinstance(preferred_skills, list):
        preferred_skills = []

    jd_experience = jd_data.get(
        "experience",
        []
    )

    if not isinstance(jd_experience, list):
        jd_experience = []

    jd_education = jd_data.get(
        "education",
        []
    )

    if not isinstance(jd_education, list):
        jd_education = []

    # ========================================================
    # 1. Skill score
    # ========================================================

    skill_result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )


    # ========================================================
    # 2. Experience score
    # ========================================================

    experience_result = calculate_experience_score(
        candidate_profile,
        jd_profile,
    )


    # ========================================================
    # 3. Education score
    # ========================================================

    education_result = calculate_education_score(
    candidate_profile,
    jd_profile,
)


    # ========================================================
    # 4. Semantic score
    # ========================================================

    semantic_result = calculate_semantic_score(
        resume_embedding=resume_embedding,
        jd_embedding=jd_embedding,
    )


    # ========================================================
    # 5. Generate final ATS score
    # ========================================================

    final_result = generate_candidate_score(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        semantic_result=semantic_result,
        job_title=job_title,
        custom_weights=custom_weights,
    )
    # ========================================================
    # Final output
    # ========================================================

    return {
        "candidate_score": final_result,

        "component_scores": {
            "skill": skill_result,
            "experience": experience_result,
            "education": education_result,
            "semantic": semantic_result,
        },

        "metadata": {
            "job_title": job_title,

            "required_skills_count":
                len(required_skills),

            "preferred_skills_count":
                len(preferred_skills),

            "candidate_skills_count":
                len(candidate_skills),

            "candidate_years":
                candidate_years,

            "candidate_roles":
                candidate_roles,
        },
    }