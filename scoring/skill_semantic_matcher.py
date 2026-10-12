from typing import Any, List, Optional
import numpy as np

SEMANTIC_MATCH_MIN_THRESHOLD = 0.70


def cosine_similarity(a, b) -> float:
    if a is None or b is None:
        return 0.0
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size == 0 or b.size == 0:
        return 0.0
    if a.shape != b.shape:
        raise ValueError("Embedding vectors must have the same dimensions.")
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _generate_embedding(text: str, generator: Any) -> Optional[List[float]]:
    if not text or generator is None:
        return None
    if hasattr(generator, "generate_embedding"):
        e = generator.generate_embedding(text)
    elif hasattr(generator, "encode"):
        e = generator.encode(text)
    elif hasattr(generator, "model") and hasattr(generator.model, "encode"):
        e = generator.model.encode(text, convert_to_numpy=True)
    else:
        return None
    if e is None:
        return None
    if isinstance(e, np.ndarray):
        return e.tolist()
    if hasattr(e, "tolist"):
        return e.tolist()
    return list(e)


def find_semantic_skill_matches(
    candidate_skills: List[str],
    required_skills: Optional[List[str]] = None,
    embedding_generator: Any = None,
    threshold: float = SEMANTIC_MATCH_MIN_THRESHOLD,
    *,
    jd_skills: Optional[List[str]] = None,
) -> List[dict]:
    """
    Find semantic matches between candidate skills and JD skills.

    Compatibility:
        required_skills -> existing/internal API
        jd_skills       -> JD/test-friendly API

    Related skills do not automatically receive semantic credit.
    A skill only becomes a semantic match when its embedding
    similarity reaches the configured threshold.
    """

    # Support both parameter names.
    if required_skills is None:
        required_skills = jd_skills

    if (
        not candidate_skills
        or not required_skills
        or embedding_generator is None
    ):
        return []

    try:
        threshold = max(
            0.0,
            min(1.0, float(threshold)),
        )
    except (TypeError, ValueError):
        threshold = SEMANTIC_MATCH_MIN_THRESHOLD

    candidate_embeddings = {}

    for candidate_skill in candidate_skills:
        if not isinstance(candidate_skill, str):
            continue

        candidate_skill = candidate_skill.strip()

        if not candidate_skill:
            continue

        embedding = _generate_embedding(
            candidate_skill,
            embedding_generator,
        )

        if embedding is not None:
            candidate_embeddings[candidate_skill] = embedding

    matches = []
    used_candidate_skills = set()

    for required_skill in required_skills:
        if not isinstance(required_skill, str):
            continue

        required_skill = required_skill.strip()

        if not required_skill:
            continue

        required_embedding = _generate_embedding(
            required_skill,
            embedding_generator,
        )

        if required_embedding is None:
            continue

        best_candidate = None
        best_similarity = -1.0

        for candidate_skill, candidate_embedding in candidate_embeddings.items():

            if candidate_skill in used_candidate_skills:
                continue

            try:
                similarity = cosine_similarity(
                    candidate_embedding,
                    required_embedding,
                )
            except (TypeError, ValueError):
                continue

            if similarity > best_similarity:
                best_similarity = similarity
                best_candidate = candidate_skill

        if (
            best_candidate is not None
            and best_similarity >= threshold
        ):
            matches.append(
                {
                    "jd_skill": required_skill,
                    "required_skill": required_skill,
                    "candidate_skill": best_candidate,
                    "matched_skill": best_candidate,
                    "similarity": round(
                        best_similarity,
                        4,
                    ),
                    "score": round(
                        best_similarity * 100,
                        2,
                    ),
                    "match_type": "semantic",
                    "matched": True,
                }
            )

            used_candidate_skills.add(
                best_candidate
            )

    return matches