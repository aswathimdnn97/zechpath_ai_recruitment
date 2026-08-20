from typing import Any, Dict, List

import numpy as np


# ============================================================
# Configuration
# ============================================================

SEMANTIC_MATCH_THRESHOLD = 0.70


# ============================================================
# Cosine Similarity
# ============================================================

def _cosine_similarity(
    vector_a: np.ndarray,
    vector_b: np.ndarray,
) -> float:
    """
    Calculate cosine similarity between two embeddings.
    """

    if vector_a is None or vector_b is None:
        return 0.0

    norm_a = np.linalg.norm(vector_a)
    norm_b = np.linalg.norm(vector_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(
        np.dot(vector_a, vector_b)
        / (norm_a * norm_b)
    )


# ============================================================
# Semantic Skill Matching
# ============================================================

def find_semantic_skill_matches(
    candidate_skills: List[str],
    jd_skills: List[str],
    embedding_generator: Any,
    threshold: float = SEMANTIC_MATCH_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Find semantically similar candidate skills for JD skills.

    Only JD skills that are not already exact matches should
    normally be passed to this function.

    Returns explainable semantic matches.
    """

    if not candidate_skills or not jd_skills:
        return []

    if embedding_generator is None:
        return []

    # --------------------------------------------------------
    # Generate candidate skill embeddings
    # --------------------------------------------------------

    candidate_embeddings = {}

    for skill in candidate_skills:

        if not isinstance(skill, str):
            continue

        skill = skill.strip()

        if not skill:
            continue

        embedding = embedding_generator.model.encode(
            skill,
            convert_to_numpy=True,
        )

        candidate_embeddings[skill] = embedding

    # --------------------------------------------------------
    # Generate JD skill embeddings
    # --------------------------------------------------------

    jd_embeddings = {}

    for skill in jd_skills:

        if not isinstance(skill, str):
            continue

        skill = skill.strip()

        if not skill:
            continue

        embedding = embedding_generator.model.encode(
            skill,
            convert_to_numpy=True,
        )

        jd_embeddings[skill] = embedding

    # --------------------------------------------------------
    # Compare skills
    # --------------------------------------------------------

    matches = []

    for jd_skill, jd_embedding in jd_embeddings.items():

        best_candidate_skill = None
        best_similarity = 0.0

        for (
            candidate_skill,
            candidate_embedding
        ) in candidate_embeddings.items():

            similarity = _cosine_similarity(
                candidate_embedding,
                jd_embedding,
            )

            if similarity > best_similarity:

                best_similarity = similarity
                best_candidate_skill = (
                    candidate_skill
                )

        # ----------------------------------------------------
        # Accept semantic match
        # ----------------------------------------------------

        if (
            best_candidate_skill is not None
            and best_similarity >= threshold
        ):

            matches.append(
                {
                    "jd_skill": jd_skill,
                    "candidate_skill":
                        best_candidate_skill,
                    "similarity":
                        round(best_similarity, 4),
                    "match_type":
                        "semantic",
                }
            )

    return matches