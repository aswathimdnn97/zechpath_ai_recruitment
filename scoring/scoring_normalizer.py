from typing import Optional


def normalize_score(
    score: Optional[float],
    min_value: float = 0.0,
    max_value: float = 100.0,
) -> float:
    """
    Normalize a score from a given range to 0-100.

    Example:
        normalize_score(0.5, 0, 1)
        -> 50.0

        normalize_score(50, 0, 100)
        -> 50.0
    """

    if score is None:
        return 0.0

    try:
        score = float(score)
        min_value = float(min_value)
        max_value = float(max_value)
    except (TypeError, ValueError):
        return 0.0

    if max_value <= min_value:
        raise ValueError(
            "max_value must be greater than min_value"
        )

    # Clamp input
    score = max(
        min_value,
        min(score, max_value)
    )

    normalized_score = (
        (score - min_value)
        / (max_value - min_value)
    ) * 100.0

    return round(normalized_score, 2)


def normalize_percentage(
    score: Optional[float]
) -> float:
    """
    Validate and clamp a score that is already
    expected to be between 0 and 100.
    """

    if score is None:
        return 0.0

    try:
        score = float(score)
    except (TypeError, ValueError):
        return 0.0

    return round(
        max(0.0, min(score, 100.0)),
        2
    )


def normalize_similarity(
    similarity: Optional[float]
) -> float:
    """
    Convert cosine similarity from [-1, 1]
    to ATS score [0, 100].

    Formula:
        ((similarity + 1) / 2) * 100
    """

    if similarity is None:
        return 0.0

    try:
        similarity = float(similarity)
    except (TypeError, ValueError):
        return 0.0

    similarity = max(
        -1.0,
        min(similarity, 1.0)
    )

    return round(
        ((similarity + 1.0) / 2.0) * 100.0,
        2
    )