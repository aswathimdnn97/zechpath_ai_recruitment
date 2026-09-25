from typing import Any, Dict, List, Optional
import numpy as np

from scoring.scoring_normalizer import normalize_similarity


# ============================================================
# Configuration
# ============================================================

SEMANTIC_MATCH_MIN_THRESHOLD = 0.70


# ============================================================
# Cosine Similarity
# ============================================================

def cosine_similarity(
    vector_a: List[float],
    vector_b: List[float]
) -> float:
    """
    Calculate cosine similarity between two embeddings.

    Returns:
        Value between -1 and 1.

    Raises:
        ValueError if embedding dimensions differ.
    """

    if vector_a is None or vector_b is None:
        return 0.0

    if len(vector_a) == 0 or len(vector_b) == 0:
        return 0.0

    a = np.asarray(
        vector_a,
        dtype=float
    )

    b = np.asarray(
        vector_b,
        dtype=float
    )

    # --------------------------------------------------------
    # Validate dimensions
    # --------------------------------------------------------

    if a.shape != b.shape:
        raise ValueError(
            "Resume and JD embeddings "
            "must have the same dimensions."
        )

    # --------------------------------------------------------
    # Calculate vector norms
    # --------------------------------------------------------

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    # --------------------------------------------------------
    # Prevent division by zero
    # --------------------------------------------------------

    if norm_a == 0 or norm_b == 0:
        return 0.0

    # --------------------------------------------------------
    # Cosine Similarity
    # --------------------------------------------------------

    return float(
        np.dot(a, b)
        / (norm_a * norm_b)
    )


# ============================================================
# Semantic Score
# ============================================================

def calculate_semantic_score(
    resume_embedding: List[float] = None,
    jd_embedding: List[float] = None,
    similarity: float = None
) -> Dict[str, Any]:
    """
    Calculate semantic similarity score.

    If similarity is not supplied, it is calculated
    from the resume and JD embeddings.
    """

    # ========================================================
    # Case 1: Similarity was not supplied
    # ========================================================

    if similarity is None:

        if (
            resume_embedding is None
            or jd_embedding is None
        ):

            return {
                "score": None,
                "similarity": None,
                "status": "no_data"
            }

        similarity = cosine_similarity(
            resume_embedding,
            jd_embedding
        )

    # ========================================================
    # Validate similarity
    # ========================================================

    if not isinstance(
        similarity,
        (int, float)
    ):

        return {
            "score": None,
            "similarity": None,
            "status": "invalid_data"
        }

    # ========================================================
    # Clamp similarity
    # ========================================================

    similarity = max(
        -1.0,
        min(1.0, float(similarity))
    )

    # ========================================================
    # Convert similarity to 0-100 score
    # ========================================================

    score = normalize_similarity(similarity)

    # ========================================================
    # Return explainable result
    # ========================================================

    return {
        "score": round(
            score,
            2
        ),

        "similarity": round(
            similarity,
            4
        ),

        "status": "calculated"
    }


# ============================================================
# Skill Text Embedding Helper
# ============================================================

def _generate_embedding(
    text: str,
    embedding_generator: Any
) -> Optional[List[float]]:
    """
    Generate an embedding for a skill using the project's
    existing embedding generator.

    The function supports common embedding-generator
    interfaces without changing the existing generator.
    """

    if not text:
        return None

    if embedding_generator is None:
        return None

    # --------------------------------------------------------
    # Interface 1:
    # generate_embedding(text)
    # --------------------------------------------------------

    if hasattr(
        embedding_generator,
        "generate_embedding"
    ):

        embedding = (
            embedding_generator.generate_embedding(text)
        )

    # --------------------------------------------------------
    # Interface 2:
    # encode(text)
    # --------------------------------------------------------

    elif hasattr(
        embedding_generator,
        "encode"
    ):

        embedding = (
            embedding_generator.encode(text)
        )

    else:
        return None

    # --------------------------------------------------------
    # Convert numpy array to list
    # --------------------------------------------------------

    if isinstance(
        embedding,
        np.ndarray
    ):

        embedding = embedding.tolist()

    return embedding


# ============================================================
# Semantic Skill Matching
# ============================================================

def find_semantic_skill_matches(
    candidate_skills: List[str],
    required_skills: List[str],
    embedding_generator: Any = None,
    threshold: float = SEMANTIC_MATCH_MIN_THRESHOLD
) -> Dict[str, Any]:
    """
    Find semantic matches between candidate skills and
    required skills using embedding similarity.

    This function is used by skill_score.py.

    Matching is performed only when the semantic similarity
    reaches the configured threshold.

    Returns an explainable structure containing:

        semantic_matches
        unmatched_required_skills
        scores
    """

    # ========================================================
    # Validate input
    # ========================================================

    if not candidate_skills:
        return {
            "semantic_matches": [],
            "unmatched_required_skills": list(
                required_skills or []
            ),
            "scores": {}
        }

    if not required_skills:
        return {
            "semantic_matches": [],
            "unmatched_required_skills": [],
            "scores": {}
        }

    if embedding_generator is None:
        return {
            "semantic_matches": [],
            "unmatched_required_skills": list(
                required_skills
            ),
            "scores": {}
        }

    # ========================================================
    # Normalize threshold
    # ========================================================

    threshold = max(
        0.0,
        min(
            1.0,
            float(threshold)
        )
    )

    # ========================================================
    # Generate candidate skill embeddings
    # ========================================================

    candidate_embeddings = {}

    for candidate_skill in candidate_skills:

        if not candidate_skill:
            continue

        embedding = _generate_embedding(
            candidate_skill,
            embedding_generator
        )

        if embedding is not None:
            candidate_embeddings[
                candidate_skill
            ] = embedding

    # ========================================================
    # Generate required skill embeddings
    # ========================================================

    required_embeddings = {}

    for required_skill in required_skills:

        if not required_skill:
            continue

        embedding = _generate_embedding(
            required_skill,
            embedding_generator
        )

        if embedding is not None:
            required_embeddings[
                required_skill
            ] = embedding

    # ========================================================
    # Find best semantic match
    # ========================================================

    semantic_matches = []
    matched_required_skills = set()
    scores = {}

    for required_skill, required_embedding in (
        required_embeddings.items()
    ):

        best_candidate = None
        best_similarity = -1.0

        for candidate_skill, candidate_embedding in (
            candidate_embeddings.items()
        ):

            try:

                similarity = cosine_similarity(
                    candidate_embedding,
                    required_embedding
                )

            except ValueError:
                continue

            if similarity > best_similarity:

                best_similarity = similarity
                best_candidate = candidate_skill

        # ----------------------------------------------------
        # Accept only above threshold
        # ----------------------------------------------------

        if (
            best_candidate is not None
            and best_similarity >= threshold
        ):

            semantic_matches.append({
                "candidate_skill": best_candidate,
                "required_skill": required_skill,
                "similarity": round(
                    best_similarity,
                    4
                ),
                "score": round(
                    normalize_similarity(
                        best_similarity
                    ),
                    2
                )
            })

            matched_required_skills.add(
                required_skill
            )

            scores[required_skill] = round(
                best_similarity,
                4
            )

    # ========================================================
    # Determine unmatched required skills
    # ========================================================

    unmatched_required_skills = [
        skill
        for skill in required_skills
        if skill not in matched_required_skills
    ]

    # ========================================================
    # Return explainable result
    # ========================================================

    return {
        "semantic_matches": semantic_matches,
        "unmatched_required_skills": (
            unmatched_required_skills
        ),
        "scores": scores
    }