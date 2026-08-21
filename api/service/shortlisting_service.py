from typing import Any, Dict, List

from fastapi import HTTPException

from api.service.ranking_service import (
    load_scoring_results,
    get_candidate_id,
    get_candidate_name,
    get_candidate_score,
)

from scoring.ranking.candidate_ranker import (
    rank_candidates,
)

from scoring.ranking.shortlisting_engine import (
    shortlist_candidates,
)


# ============================================================
# SHORTLIST ALL CANDIDATES
# ============================================================

def shortlist_all_candidates(
    shortlist_threshold: float = 80.0,
    review_threshold: float = 60.0,
) -> Dict[str, Any]:
    """
    Shortlist all scored candidates.

    Flow:

        scoring_results/
              |
              v
        Load scoring results
              |
              v
        Rank candidates
              |
              v
        Apply shortlisting rules
              |
              v
        SHORTLIST / REVIEW / REJECT
              |
              v
        Build API response
    """

    # ========================================================
    # 1. VALIDATE THRESHOLDS
    # ========================================================

    if shortlist_threshold < review_threshold:
        raise HTTPException(
            status_code=400,
            detail=(
                "shortlist_threshold must be "
                "greater than or equal to review_threshold."
            ),
        )

    # ========================================================
    # 2. LOAD SCORING RESULTS
    # ========================================================

    scoring_results = load_scoring_results()

    if not scoring_results:
        raise HTTPException(
            status_code=404,
            detail="No scored candidates found.",
        )

    # ========================================================
    # 3. RANK CANDIDATES
    # ========================================================

    ranked_candidates = rank_candidates(
        scoring_results
    )

    # ========================================================
    # 4. APPLY SHORTLISTING RULES
    # ========================================================

    shortlisted_candidates = shortlist_candidates(
        ranked_candidates,
        shortlist_threshold=shortlist_threshold,
        review_threshold=review_threshold,
    )

    # ========================================================
    # 5. BUILD API RESPONSE
    # ========================================================

    final_candidates: List[Dict[str, Any]] = []

    for candidate in shortlisted_candidates:

        final_candidates.append(
            {
                "rank": candidate.get(
                    "rank"
                ),

                "candidate_id": get_candidate_id(
                    candidate
                ),

                "candidate_name": get_candidate_name(
                    candidate
                ),

                "score": get_candidate_score(
                    candidate
                ),

                "decision": candidate.get(
                    "decision",
                    "UNKNOWN",
                ),
            }
        )

    # ========================================================
    # 6. SUMMARY COUNTS
    # ========================================================

    shortlisted_count = sum(
        1
        for candidate in final_candidates
        if candidate["decision"] == "SHORTLIST"
    )

    review_count = sum(
        1
        for candidate in final_candidates
        if candidate["decision"] == "REVIEW"
    )

    rejected_count = sum(
        1
        for candidate in final_candidates
        if candidate["decision"] == "REJECT"
    )

    # ========================================================
    # 7. FINAL RESPONSE
    # ========================================================

    return {
        "status": "SHORTLISTED",

        "total_candidates": len(
            final_candidates
        ),

        "shortlisted": shortlisted_count,

        "review": review_count,

        "rejected": rejected_count,

        "thresholds": {
            "shortlist": shortlist_threshold,
            "review": review_threshold,
        },

        "candidates": final_candidates,
    }