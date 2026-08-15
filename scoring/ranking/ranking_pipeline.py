from typing import Any, Dict, List

from scoring.ranking.candidate_ranker import rank_candidates
from scoring.ranking.shortlisting_engine import shortlist_candidates


def rank_and_shortlist(
    candidates: List[Dict[str, Any]],
    shortlist_threshold: float = 80.0,
    review_threshold: float = 60.0,
) -> List[Dict[str, Any]]:
    """
    Rank candidates by overall score and classify them
    into SHORTLIST, REVIEW, or REJECT.
    """

    # Step 1: Rank candidates
    ranked_candidates = rank_candidates(candidates)

    # Step 2: Apply shortlisting rules
    final_candidates = shortlist_candidates(
        ranked_candidates,
        shortlist_threshold=shortlist_threshold,
        review_threshold=review_threshold,
    )

    return final_candidates