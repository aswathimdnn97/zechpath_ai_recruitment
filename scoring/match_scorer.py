from typing import Dict, Optional


# ============================================================
# Default Weights
# ============================================================

DEFAULT_WEIGHTS = {
    "overall": 0.30,
    "skills": 0.35,
    "experience": 0.20,
    "projects": 0.15,
}


# ============================================================
# Default Thresholds
# ============================================================

DEFAULT_THRESHOLDS = {
    "strong": 0.70,
    "moderate": 0.55,
    "weak": 0.40,
}


# ============================================================
# Helper Functions
# ============================================================

def _safe_score(value: Optional[float]) -> float:
    """
    Convert a similarity value into a safe score.

    Returns:
        Float between 0.0 and 1.0.
    """

    if value is None:
        return 0.0

    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(1.0, score))


def _validate_weights(
    weights: Dict[str, float]
) -> None:
    """
    Validate scoring weights.

    All required weights must exist and their
    total must equal approximately 1.0.
    """

    required = {
        "overall",
        "skills",
        "experience",
        "projects",
    }

    missing = required - weights.keys()

    if missing:
        raise ValueError(
            f"Missing scoring weights: {missing}"
        )

    total = sum(
        float(weights[key])
        for key in required
    )

    if abs(total - 1.0) > 0.001:
        raise ValueError(
            f"Weights must sum to 1.0. "
            f"Current total: {total:.4f}"
        )


# ============================================================
# Calculate Weighted Match Score
# ============================================================

def calculate_match_score(
    overall_similarity: float,
    section_similarity: Dict[str, Optional[float]],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Calculate final weighted candidate-JD match score.

    Returns:
        Float between 0.0 and 1.0.
    """

    if weights is None:
        weights = DEFAULT_WEIGHTS.copy()

    _validate_weights(weights)

    overall = _safe_score(
        overall_similarity
    )

    skills = _safe_score(
        section_similarity.get("skills")
    )

    experience = _safe_score(
        section_similarity.get("experience")
    )

    projects = _safe_score(
        section_similarity.get("projects")
    )

    final_score = (
        overall * weights["overall"]
        + skills * weights["skills"]
        + experience * weights["experience"]
        + projects * weights["projects"]
    )

    return round(
        _safe_score(final_score),
        4
    )


# ============================================================
# Match Classification
# ============================================================

def classify_match(
    score: float,
    thresholds: Optional[Dict[str, float]] = None,
) -> str:
    """
    Convert match score into a category.

    Default:

        >= 0.70 -> Strong Match
        >= 0.55 -> Moderate Match
        >= 0.40 -> Weak Match
        <  0.40 -> Poor Match
    """

    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()

    strong = _safe_score(
        thresholds.get("strong")
    )

    moderate = _safe_score(
        thresholds.get("moderate")
    )

    weak = _safe_score(
        thresholds.get("weak")
    )

    if not (
        strong >= moderate >= weak
    ):
        raise ValueError(
            "Thresholds must satisfy: "
            "strong >= moderate >= weak"
        )

    score = _safe_score(score)

    if score >= strong:
        return "Strong Match"

    if score >= moderate:
        return "Moderate Match"

    if score >= weak:
        return "Weak Match"

    return "Poor Match"


# ============================================================
# Complete Match Scoring
# ============================================================

def score_match(
    overall_similarity: float,
    section_similarity: Dict[str, Optional[float]],
    weights: Optional[Dict[str, float]] = None,
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    Calculate complete candidate-JD match result.

    Returns:
        {
            "match_score": 0.XXXX,
            "match_percentage": XX.XX,
            "match_category": "Strong Match"
        }
    """

    final_score = calculate_match_score(
        overall_similarity=overall_similarity,
        section_similarity=section_similarity,
        weights=weights,
    )

    category = classify_match(
        score=final_score,
        thresholds=thresholds,
    )

    return {
        "match_score": final_score,

        "match_percentage": round(
            final_score * 100,
            2
        ),

        "match_category": category,
    }