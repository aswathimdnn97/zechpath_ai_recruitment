
"""
question_scoring_service.py

Responsibilities:
1. Calculate weighted scores for individual screening questions.
2. Validate dimension scores.
3. Normalize the final question score.
4. Generate explainable scoring output.
"""

import math
from typing import Any

from api.service.scoring_config_service import (
    ScoringConfig,
    load_scoring_config,
)


DIMENSION_NAMES = (
    "clarity",
    "relevance",
    "completeness",
    "consistency",
)


class QuestionScoringError(Exception):
    """Raised when question scoring fails."""


def validate_dimension_scores(
    dimension_scores: dict[str, float],
) -> None:
    """Validate that all four dimensions have scores from 0 to 100."""

    if not isinstance(dimension_scores, dict):
        raise QuestionScoringError(
            "Dimension scores must be a dictionary."
        )

    missing = set(DIMENSION_NAMES) - set(dimension_scores)
    extra = set(dimension_scores) - set(DIMENSION_NAMES)

    if missing:
        raise QuestionScoringError(
            f"Missing dimension scores: {sorted(missing)}"
        )

    if extra:
        raise QuestionScoringError(
            f"Unexpected dimensions: {sorted(extra)}"
        )

    for dimension, score in dimension_scores.items():

        if isinstance(score, bool) or not isinstance(
            score, (int, float)
        ):
            raise QuestionScoringError(
                f"{dimension} score must be numeric."
            )

        if not math.isfinite(score):
            raise QuestionScoringError(
                f"{dimension} score must be finite."
            )

        if not 0 <= score <= 100:
            raise QuestionScoringError(
                f"{dimension} score must be between 0 and 100."
            )


def calculate_weighted_score(
    dimension_scores: dict[str, float],
    config: ScoringConfig,
) -> tuple[float, dict[str, float]]:
    """
    Calculate the weighted score and each dimension's contribution.
    """

    validate_dimension_scores(dimension_scores)

    contributions = {}

    for dimension in DIMENSION_NAMES:
        weight = getattr(
            config.dimensions,
            dimension
        ).weight

        contributions[dimension] = (
            dimension_scores[dimension] * weight
        )

    total_score = sum(contributions.values())

    return total_score, contributions


def score_question(
    question_id: str,
    dimension_scores: dict[str, float],
    explanations: dict[str, str] | None = None,
    config: ScoringConfig | None = None,
) -> dict[str, Any]:
    """
    Generate an explainable score for one screening question.

    Dimension scores must be calculated by the answer assessment
    logic before calling this function.
    """

    if not isinstance(question_id, str) or not question_id.strip():
        raise QuestionScoringError(
            "Question ID must be a non-empty string."
        )

    config = config or load_scoring_config()

    total_score, contributions = calculate_weighted_score(
        dimension_scores,
        config,
    )

    precision = config.normalization.precision

    dimension_details = {}

    for dimension in DIMENSION_NAMES:

        weight = getattr(
            config.dimensions,
            dimension
        ).weight

        dimension_details[dimension] = {
            "score": round(
                dimension_scores[dimension],
                precision,
            ),
            "weight": weight,
            "weighted_contribution": round(
                contributions[dimension],
                precision,
            ),
            "explanation": (
                explanations.get(dimension, "")
                if explanations else ""
            ),
        }

    normalized_score = round(
        total_score,
        precision,
    )

    return {
        "question_id": question_id,
        "scoring_version": config.scoring_version,
        "dimension_scores": dimension_details,
        "total_score": normalized_score,
        "max_score": 100,
        "score_percentage": normalized_score,
        "normalization_method": config.normalization.method,
    }
