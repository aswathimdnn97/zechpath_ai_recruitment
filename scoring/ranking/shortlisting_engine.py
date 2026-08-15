from typing import Any, Dict, List

from .candidate_ranker import get_candidate_score


DEFAULT_SHORTLIST_THRESHOLD = 80.0
DEFAULT_REVIEW_THRESHOLD = 60.0


def classify_candidate(
    score: float,
    shortlist_threshold: float = DEFAULT_SHORTLIST_THRESHOLD,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
) -> str:
    """
    Classify a candidate based on their final ATS score.

    Score >= shortlist_threshold -> SHORTLIST
    Score >= review_threshold   -> REVIEW
    Score < review_threshold    -> REJECT
    """

    if shortlist_threshold < review_threshold:
        raise ValueError(
            "shortlist_threshold must be greater than or equal to "
            "review_threshold"
        )

    if score >= shortlist_threshold:
        return "SHORTLIST"

    if score >= review_threshold:
        return "REVIEW"

    return "REJECT"


def shortlist_candidates(
    candidates: List[Dict[str, Any]],
    shortlist_threshold: float = DEFAULT_SHORTLIST_THRESHOLD,
    review_threshold: float = DEFAULT_REVIEW_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Assign SHORTLIST, REVIEW, or REJECT to every candidate.
    """

    shortlisted_candidates = []

    for candidate in candidates:

        # Use the same score extraction logic as ranking.
        score = get_candidate_score(candidate)

        decision = classify_candidate(
            score=score,
            shortlist_threshold=shortlist_threshold,
            review_threshold=review_threshold,
        )

        candidate_result = candidate.copy()

        candidate_result["rank"] = candidate.get("rank")

        candidate_result["decision"] = decision

        shortlisted_candidates.append(
            candidate_result
        )

    return shortlisted_candidates