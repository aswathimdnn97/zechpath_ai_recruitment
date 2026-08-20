from typing import Any, Dict, List
import numpy as np
from scoring.scoring_normalizer import normalize_similarity


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
    # Cosine similarity
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

    Cosine similarity:
        -1 = completely opposite
         0 = unrelated
         1 = identical direction

    Converted ATS score:

        ((similarity + 1) / 2) * 100
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