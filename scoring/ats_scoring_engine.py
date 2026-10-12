"""
ATS Scoring Engine

Pipeline
--------
Resume
    ↓
Candidate Profile
    ↓
Bias Mitigation
    ↓
Skill Score
    ↓
Experience Score
    ↓
Education Score
    ↓
Overall Semantic Score
    ↓
Final ATS Score

This module is the orchestration layer. Individual scorers remain
responsible for their own calculations.
"""

from typing import Any, Dict, Optional

from scoring.skill_score import calculate_skill_score
from scoring.experince_score import calculate_experience_score
from scoring.education_score import calculate_education_score
from scoring.semantic_scorer import calculate_semantic_score
from scoring.score_generator import generate_candidate_score
from embeddings.embedding_generator import EmbeddingGenerator
from scoring.bias_mitigation.personal_attribute_masker import (
    mask_personal_attributes,
)


def _get_resume_text(candidate_profile: Any) -> str:
    if not isinstance(candidate_profile, dict):
        return ""

    value = (
        candidate_profile.get("resume_text")
        or candidate_profile.get("raw_text")
        or candidate_profile.get("text")
        or ""
    )
    return value if isinstance(value, str) else str(value)


def _get_jd_data(jd_profile: Any) -> Dict[str, Any]:
    return jd_profile if isinstance(jd_profile, dict) else {}


def _extract_candidate_skills(candidate_profile: Any):
    if not isinstance(candidate_profile, dict):
        return []

    skills = candidate_profile.get("skills", [])
    return skills if isinstance(skills, list) else []


def _extract_candidate_roles(candidate_profile: Any):
    if not isinstance(candidate_profile, dict):
        return []

    experience = candidate_profile.get("experience", [])
    if not isinstance(experience, list):
        return []

    roles = []
    for record in experience:
        if not isinstance(record, dict):
            continue

        role = (
            record.get("role")
            or record.get("job_title")
            or record.get("title")
        )
        if role:
            roles.append(role)

    return roles


def _extract_candidate_education(candidate_profile: Any):
    if not isinstance(candidate_profile, dict):
        return []

    education = candidate_profile.get("education", [])
    return education if isinstance(education, list) else []


def _extract_job_title(jd_profile: Dict[str, Any]) -> str:
    value = (
        jd_profile.get("job_title")
        or jd_profile.get("title")
        or jd_profile.get("position")
        or ""
    )
    return value if isinstance(value, str) else str(value)


def _format_experience_result_for_ats(
    experience_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Adapt the low-level experience scorer result to the richer
    structure exposed by the ATS engine.

    The low-level experience scorer intentionally keeps component
    scores numeric for backward compatibility with its direct tests.
    The ATS API exposes score + weight for the weighted components.
    """
    if not isinstance(experience_result, dict):
        return {}

    component_scores = experience_result.get("component_scores", {})
    weights = experience_result.get("weights", {})

    if not isinstance(component_scores, dict):
        component_scores = {}

    if not isinstance(weights, dict):
        weights = {}

    formatted_components = dict(component_scores)

    if "years" in component_scores:
        formatted_components["years"] = {
            "score": component_scores["years"],
            "weight": weights.get("years", 0.0),
        }

    if "role" in component_scores:
        formatted_components["role"] = {
            "score": component_scores["role"],
            "weight": weights.get("role", 0.0),
        }

    # Keep technology numeric because the ATS tests and existing
    # consumers expect technology to remain a direct score.
    if "technology" in component_scores:
        formatted_components["technology"] = component_scores["technology"]

    return {
        **experience_result,
        "component_scores": formatted_components,
    }

def calculate_ats_score(
    candidate_profile: Any,
    jd_profile: Any,
    embedding_generator: Optional[EmbeddingGenerator] = None,
    resume_embedding=None,
    jd_embedding=None,
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Calculate the complete ATS score.

    Component weights are owned by score_generator.py / weight_config.py.
    The engine does not recalculate the final score itself.

    resume_embedding and jd_embedding are optional compatibility inputs.
    If supplied, the semantic scorer uses them directly.
    """

    if embedding_generator is None:
        embedding_generator = EmbeddingGenerator()

    candidate_profile = (
        candidate_profile
        if isinstance(candidate_profile, dict)
        else {}
    )
    jd_profile = _get_jd_data(jd_profile)

    candidate_id = candidate_profile.get("candidate_id")

    masked_candidate_profile = mask_personal_attributes(
        candidate_profile
    )

    if not isinstance(masked_candidate_profile, dict):
        masked_candidate_profile = candidate_profile.copy()

    # Candidate ID is an identifier, not a scoring attribute.
    if candidate_id is not None:
        masked_candidate_profile["candidate_id"] = candidate_id

    candidate_skills = _extract_candidate_skills(
        masked_candidate_profile
    )
    candidate_roles = _extract_candidate_roles(
        masked_candidate_profile
    )
    candidate_education = _extract_candidate_education(
        masked_candidate_profile
    )

    # 1. Skill score
    skill_result = calculate_skill_score(
        masked_candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    # 2. Experience score
    # Skill matching is owned by SkillScore. ExperienceScore receives
    # the result instead of independently rematching JD skills.
    experience_result = calculate_experience_score(
        masked_candidate_profile,
        jd_profile,
        skill_result=skill_result,
    )

    # 3. Education score
    education_result = calculate_education_score(
        masked_candidate_profile,
        jd_profile,
    )

    # 4. Overall semantic score
    resume_text = _get_resume_text(masked_candidate_profile)

    semantic_result = calculate_semantic_score(
        resume_text=resume_text,
        jd_profile=jd_profile,
        embedding_generator=embedding_generator,
        resume_embedding=resume_embedding,
        jd_embedding=jd_embedding,
    )

    # 5. Final weighted score
    candidate_score = generate_candidate_score(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        semantic_result=semantic_result,
        job_title=_extract_job_title(jd_profile),
        custom_weights=custom_weights,
    )

    metadata = {
        "candidate_id": candidate_id,
        "candidate_skills": candidate_skills,
        "candidate_roles": candidate_roles,
        "candidate_education": candidate_education,
        "candidate_years": experience_result.get(
            "candidate_years",
            0.0,
        ),
    }

    return {
        "candidate_id": candidate_id,
        "candidate_score": candidate_score,
        "component_scores": {
            "skill": skill_result,
            "experience": _format_experience_result_for_ats(
                experience_result
            ),
            "education": education_result,
            "semantic": semantic_result,
        },
                "metadata": metadata,
        "bias_mitigation": {
            "applied": True,
        },
    }
