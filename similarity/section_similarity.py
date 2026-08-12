from typing import Any, Dict, Optional

import numpy as np

from embeddings.section_embedding import (
    generate_resume_section_embeddings,
    generate_jd_section_embeddings
)


# ============================================================
# Cosine Similarity
# ============================================================

def cosine_similarity(
    resume_embedding,
    jd_embedding
) -> Optional[float]:
    """
    Calculate cosine similarity between two embeddings.
    """

    if resume_embedding is None or jd_embedding is None:
        return None

    resume = np.asarray(
        resume_embedding,
        dtype=float
    )

    jd = np.asarray(
        jd_embedding,
        dtype=float
    )

    if resume.size == 0 or jd.size == 0:
        return None

    resume_norm = np.linalg.norm(resume)
    jd_norm = np.linalg.norm(jd)

    if resume_norm == 0 or jd_norm == 0:
        return None

    similarity = np.dot(
        resume,
        jd
    ) / (
        resume_norm * jd_norm
    )

    return float(similarity)


# ============================================================
# Section Similarities
# ============================================================

def calculate_section_similarities(
    candidate_profile: Dict[str, Any],
    job_description: Dict[str, Any]
) -> Dict[str, Optional[float]]:
    """
    Calculate semantic similarity for:

        skills
        experience
        projects
    """

    resume_embeddings = (
        generate_resume_section_embeddings(
            candidate_profile
        )
    )

    jd_embeddings = (
        generate_jd_section_embeddings(
            job_description
        )
    )

    section_scores = {}

    for section in [
        "skills",
        "experience",
        "projects"
    ]:

        resume_embedding = (
            resume_embeddings.get(section)
        )

        jd_embedding = (
            jd_embeddings.get(section)
        )

        section_scores[section] = cosine_similarity(
            resume_embedding,
            jd_embedding
        )

    return section_scores