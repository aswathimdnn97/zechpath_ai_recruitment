from typing import Any, Dict, List
import logging

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
# LOGGER
# ============================================================

logger = logging.getLogger(
    __name__
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

    logger.info(
        "Candidate shortlisting started: "
        "shortlist_threshold=%s review_threshold=%s",
        shortlist_threshold,
        review_threshold,
    )

    try:

        # ====================================================
        # 1. VALIDATE THRESHOLDS
        # ====================================================

        if shortlist_threshold < review_threshold:

            logger.warning(
                "Invalid shortlisting thresholds: "
                "shortlist_threshold=%s "
                "review_threshold=%s",
                shortlist_threshold,
                review_threshold,
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    "shortlist_threshold must be "
                    "greater than or equal to "
                    "review_threshold."
                ),
            )

        # ====================================================
        # 2. LOAD SCORING RESULTS
        # ====================================================

        logger.info(
            "Loading scoring results for shortlisting"
        )

        scoring_results = (
            load_scoring_results()
        )

        if not scoring_results:

            logger.warning(
                "Shortlisting failed: "
                "no scored candidates found"
            )

            raise HTTPException(
                status_code=404,
                detail="No scored candidates found.",
            )

        logger.info(
            "Scoring results loaded for shortlisting: "
            "count=%s",
            len(scoring_results),
        )

        # ====================================================
        # 3. RANK CANDIDATES
        # ====================================================

        logger.info(
            "Ranking candidates before shortlisting: "
            "count=%s",
            len(scoring_results),
        )

        ranked_candidates = rank_candidates(
            scoring_results
        )

        logger.info(
            "Candidate ranking completed for shortlisting: "
            "count=%s",
            len(ranked_candidates),
        )

        # ====================================================
        # 4. APPLY SHORTLISTING RULES
        # ====================================================

        logger.info(
            "Applying shortlisting rules: "
            "shortlist_threshold=%s "
            "review_threshold=%s",
            shortlist_threshold,
            review_threshold,
        )

        shortlisted_candidates = (
            shortlist_candidates(
                ranked_candidates,
                shortlist_threshold=(
                    shortlist_threshold
                ),
                review_threshold=(
                    review_threshold
                ),
            )
        )

        # ====================================================
        # 5. BUILD API RESPONSE
        # ====================================================

        final_candidates: List[
            Dict[str, Any]
        ] = []

        for candidate in shortlisted_candidates:

            final_candidates.append(
                {
                    "rank": candidate.get(
                        "rank"
                    ),

                    "candidate_id": (
                        get_candidate_id(
                            candidate
                        )
                    ),

                    "candidate_name": (
                        get_candidate_name(
                            candidate
                        )
                    ),

                    "score": (
                        get_candidate_score(
                            candidate
                        )
                    ),

                    "decision": candidate.get(
                        "decision",
                        "UNKNOWN",
                    ),
                }
            )

        # ====================================================
        # 6. SUMMARY COUNTS
        # ====================================================

        shortlisted_count = sum(
            1
            for candidate in final_candidates
            if candidate["decision"]
            == "SHORTLIST"
        )

        review_count = sum(
            1
            for candidate in final_candidates
            if candidate["decision"]
            == "REVIEW"
        )

        rejected_count = sum(
            1
            for candidate in final_candidates
            if candidate["decision"]
            == "REJECT"
        )

        # ====================================================
        # 7. LOG SUMMARY
        # ====================================================

        logger.info(
            "Candidate shortlisting completed: "
            "total=%s shortlisted=%s review=%s rejected=%s",
            len(final_candidates),
            shortlisted_count,
            review_count,
            rejected_count,
        )

        # ====================================================
        # 8. FINAL RESPONSE
        # ====================================================

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

    except HTTPException:
        # ----------------------------------------------------
        # Expected API errors are re-raised.
        # ----------------------------------------------------

        raise

    except Exception:

        # ----------------------------------------------------
        # Unexpected shortlisting errors
        # ----------------------------------------------------

        logger.exception(
            "Unexpected candidate shortlisting failure"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to shortlist candidates."
            ),
        )