"""
Overall semantic scorer.

This scorer is intentionally separate from semantic skill matching.

Overall semantic score:
    whole resume ↔ whole JD

Semantic skill matching:
    individual candidate skill ↔ individual JD skill
"""

from typing import Any, Dict, List, Optional

import numpy as np

from scoring.scoring_normalizer import normalize_similarity


SEMANTIC_MATCH_MIN_THRESHOLD = 0.70


def cosine_similarity(
    vector_a: List[float],
    vector_b: List[float],
) -> float:
    if vector_a is None or vector_b is None:
        return 0.0

    a = np.asarray(vector_a, dtype=float)
    b = np.asarray(vector_b, dtype=float)

    if a.size == 0 or b.size == 0:
        return 0.0

    if a.shape != b.shape:
        raise ValueError(
            "Resume and JD embeddings must have the same dimensions."
        )

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def _generate_embedding(
    text: str,
    embedding_generator: Any,
) -> Optional[List[float]]:
    if not text or embedding_generator is None:
        return None

    embedding = None

    if hasattr(embedding_generator, "generate_embedding"):
        embedding = embedding_generator.generate_embedding(text)
    elif hasattr(embedding_generator, "encode"):
        embedding = embedding_generator.encode(text)
    elif hasattr(embedding_generator, "model"):
        model = embedding_generator.model
        if hasattr(model, "encode"):
            embedding = model.encode(
                text,
                convert_to_numpy=True,
            )

    if embedding is None:
        return None

    if isinstance(embedding, np.ndarray):
        embedding = embedding.tolist()

    if hasattr(embedding, "tolist") and not isinstance(
        embedding, (list, tuple)
    ):
        embedding = embedding.tolist()

    return list(embedding) if embedding is not None else None


def _get_jd_text(jd_profile: Any) -> str:
    if not isinstance(jd_profile, dict):
        return ""

    # Prefer an explicit text field.
    for key in (
        "jd_text",
        "job_description",
        "description",
        "raw_text",
        "text",
    ):
        value = jd_profile.get(key)
        if isinstance(value, str) and value.strip():
            return value

    # Some existing pipeline data stores the structured JD under
    # resume_text. Only use it as structured data, not as literal text.
    nested = jd_profile.get("resume_text")
    if isinstance(nested, dict):
        jd_profile = nested

    parts = []

    for key in (
        "job_title",
        "title",
        "company",
        "summary",
        "responsibilities",
        "requirements",
        "required_skills",
        "preferred_skills",
        "skills",
        "experience",
        "education",
    ):
        value = jd_profile.get(key)

        if value is None:
            continue

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    parts.extend(str(v) for v in item.values())
                else:
                    parts.append(str(item))
        elif isinstance(value, dict):
            parts.extend(str(v) for v in value.values())
        else:
            parts.append(str(value))

    return " ".join(
        part.strip()
        for part in parts
        if part and str(part).strip()
    )


def calculate_semantic_score(
    resume_embedding: Optional[List[float]] = None,
    jd_embedding: Optional[List[float]] = None,
    similarity: Optional[float] = None,
    *,
    resume_text: Optional[str] = None,
    jd_profile: Optional[Dict[str, Any]] = None,
    embedding_generator: Any = None,
) -> Dict[str, Any]:
    """
    Calculate the whole-resume vs whole-JD semantic score.

    Supported modes:

    1. Direct embeddings:
        calculate_semantic_score(
            resume_embedding=[...],
            jd_embedding=[...],
        )

    2. Pre-calculated similarity:
        calculate_semantic_score(
            similarity=0.85,
        )

    3. Generate embeddings from resume/JD text:
        calculate_semantic_score(
            resume_text=...,
            jd_profile=...,
            embedding_generator=...,
        )
    """

    # ---------------------------------------------------------
    # 1. If similarity was explicitly supplied, use it.
    # ---------------------------------------------------------
    if similarity is None:

        # -----------------------------------------------------
        # 2. Generate missing embeddings from text when possible.
        # -----------------------------------------------------
        if resume_embedding is None or jd_embedding is None:
            if resume_text and embedding_generator is not None:
                jd_text = _get_jd_text(jd_profile)

                if jd_text:
                    if resume_embedding is None:
                        resume_embedding = _generate_embedding(
                            resume_text,
                            embedding_generator,
                        )

                    if jd_embedding is None:
                        jd_embedding = _generate_embedding(
                            jd_text,
                            embedding_generator,
                        )

        # -----------------------------------------------------
        # 3. We need both embeddings to calculate similarity.
        # -----------------------------------------------------
        if resume_embedding is None or jd_embedding is None:
            return {
                "score": None,
                "weight": 0.20,
                "similarity": None,
                "status": "no_data",
            }

        # -----------------------------------------------------
        # 4. Calculate cosine similarity.
        #
        # This is the important fix:
        # even when BOTH embeddings are supplied directly,
        # cosine_similarity() must still be called.
        # -----------------------------------------------------
        try:
            similarity = cosine_similarity(
                resume_embedding,
                jd_embedding,
            )
        except (TypeError, ValueError):
            return {
                "score": None,
                "weight": 0.20,
                "similarity": None,
                "status": "invalid_data",
            }

    # ---------------------------------------------------------
    # 5. Validate similarity.
    # ---------------------------------------------------------
    if not isinstance(
        similarity,
        (int, float, np.number),
    ):
        return {
            "score": None,
            "weight": 0.20,
            "similarity": None,
            "status": "invalid_data",
        }

    # ---------------------------------------------------------
    # 6. Keep cosine similarity inside [-1, 1].
    # ---------------------------------------------------------
    similarity = max(
        -1.0,
        min(1.0, float(similarity)),
    )

    # ---------------------------------------------------------
    # 7. Convert similarity to ATS semantic score.
    # ---------------------------------------------------------
    score = normalize_similarity(similarity)

    return {
        "score": round(score, 2),
        "weight": 0.20,
        "similarity": round(similarity, 4),
        "status": "calculated",
    }