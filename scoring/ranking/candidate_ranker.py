from typing import Any, Dict, List


def get_candidate_score(candidate: Dict[str, Any]) -> float:
    """
    Extract the final ATS score from the candidate score structure.
    """

    candidate_score = candidate.get("candidate_score", {})

    score = candidate_score.get("final_score", 0.0)

    try:
        return float(score)
    except (TypeError, ValueError):
        return 0.0


def rank_candidates(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Sort candidates by ATS final score in descending order
    and assign rank.
    """

    ranked_candidates = sorted(
        candidates,
        key=get_candidate_score,
        reverse=True
    )

    for rank, candidate in enumerate(ranked_candidates, start=1):
        candidate["rank"] = rank

    return ranked_candidates