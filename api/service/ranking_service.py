from pathlib import Path
import json
import logging
from typing import Any, Dict, List

from scoring.ranking.candidate_ranker import (
    rank_candidates,
)

from scoring.ranking.shortlisting_engine import (
    shortlist_candidates,
)

from api.utils.exception import (
    RankingError,
    ShortlistingError,
)


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(
    __name__
)


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

SCORING_RESULTS_DIR = (
    BASE_DIR
    / "data"
    / "candidates"
    / "scoring_results"
)


# ============================================================
# LOAD ALL SCORING RESULTS
# ============================================================

def load_scoring_results() -> List[Dict[str, Any]]:
    """
    Load all persisted ATS scoring results.

    Ranking does NOT recalculate ATS scores.

    It reads the already calculated results from:

        data/candidates/scoring_results/
    """

    logger.info(
        "Loading scoring results from: %s",
        SCORING_RESULTS_DIR,
    )

    if not SCORING_RESULTS_DIR.exists():

        logger.warning(
            "Scoring results directory not found: %s",
            SCORING_RESULTS_DIR,
        )

        return []

    results: List[Dict[str, Any]] = []

    for scoring_file in sorted(
        SCORING_RESULTS_DIR.glob("*.json")
    ):

        try:

            with scoring_file.open(
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

            if isinstance(
                data,
                dict,
            ):
                results.append(data)

        except (
            json.JSONDecodeError,
            OSError,
        ):

            logger.warning(
                "Invalid scoring result file ignored: %s",
                scoring_file.name,
            )

            continue

    logger.info(
        "Scoring results loaded: count=%s",
        len(results),
    )

    return results


# ============================================================
# GET CANDIDATE ID
# ============================================================

def get_candidate_id(
    candidate: Dict[str, Any],
) -> str:
    """
    Extract candidate ID from scoring result.
    """

    candidate_id = candidate.get(
        "candidate_id"
    )

    if isinstance(
        candidate_id,
        str,
    ):
        return candidate_id.strip()

    return ""


# ============================================================
# GET CANDIDATE NAME
# ============================================================

def get_candidate_name(
    candidate: Dict[str, Any],
) -> str:
    """
    Extract candidate name from the persisted
    scoring result.
    """

    candidate_name = candidate.get(
        "candidate_name"
    )

    if (
        isinstance(
            candidate_name,
            str,
        )
        and candidate_name.strip()
    ):
        return candidate_name.strip()

    return get_candidate_id(
        candidate
    )


# ============================================================
# GET CANDIDATE SCORE
# ============================================================

def get_candidate_score(
    candidate: Dict[str, Any],
) -> float:
    """
    Extract final ATS score from scoring result.
    """

    candidate_score = candidate.get(
        "candidate_score",
        {},
    )

    if not isinstance(
        candidate_score,
        dict,
    ):
        return 0.0

    score = candidate_score.get(
        "final_score",
        0.0,
    )

    try:

        return float(score)

    except (
        TypeError,
        ValueError,
    ):

        logger.warning(
            "Invalid candidate score found: candidate_id=%s",
            get_candidate_id(candidate),
        )

        return 0.0


# ============================================================
# RANK CANDIDATES
# ============================================================

def rank_all_candidates(
    shortlist_threshold: float = 80.0,
    review_threshold: float = 60.0,
) -> Dict[str, Any]:
    """
    Rank all scored candidates and apply
    shortlisting rules.

    Ranking and shortlisting errors are handled
    separately so that the API can return the
    correct error category.
    """

    logger.info(
        "Ranking started: shortlist_threshold=%s "
        "review_threshold=%s",
        shortlist_threshold,
        review_threshold,
    )

    # ========================================================
    # 1. LOAD SCORING RESULTS
    # ========================================================

    scoring_results = load_scoring_results()

    if not scoring_results:

        logger.warning(
            "Ranking failed: no scored candidates found"
        )

        raise RankingError(
            message="No scored candidates found.",
           
        )

    # ========================================================
    # 2. RANK CANDIDATES
    # ========================================================

    logger.info(
        "Ranking candidates: count=%s",
        len(scoring_results),
    )

    try:

        ranked_candidates = rank_candidates(
            scoring_results
        )

    except RankingError:
        # Preserve an already classified ranking error.
        raise

    except Exception:

        logger.exception(
            "Candidate ranking engine failed"
        )

        raise RankingError(
            message="Failed to rank candidates.",
            status_code=500,
        )

    logger.info(
        "Candidate ranking completed: count=%s",
        len(ranked_candidates),
    )

    # ========================================================
    # 3. VALIDATE RANKING RESULT
    # ========================================================

    if not isinstance(
        ranked_candidates,
        list,
    ):

        logger.error(
            "Ranking engine returned invalid result"
        )

        raise RankingError(
            message=(
                "Ranking engine returned "
                "an invalid result."
            ),
            status_code=500,
        )

    # ========================================================
    # 4. APPLY SHORTLISTING RULES
    # ========================================================

    logger.info(
        "Applying shortlisting rules: "
        "shortlist_threshold=%s "
        "review_threshold=%s",
        shortlist_threshold,
        review_threshold,
    )

    try:

        ranked_candidates = shortlist_candidates(
            ranked_candidates,
            shortlist_threshold=(
                shortlist_threshold
            ),
            review_threshold=(
                review_threshold
            ),
        )

    except ShortlistingError:
        # Preserve an already classified shortlisting error.
        raise

    except Exception:

        logger.exception(
            "Candidate shortlisting engine failed"
        )

        raise ShortlistingError(
            message=(
                "Failed to apply "
                "shortlisting rules."
            ),
            status_code=500,
        )

    # ========================================================
    # 5. VALIDATE SHORTLISTING RESULT
    # ========================================================

    if not isinstance(
        ranked_candidates,
        list,
    ):

        logger.error(
            "Shortlisting engine returned invalid result"
        )

        raise ShortlistingError(
            message=(
                "Shortlisting engine returned "
                "an invalid result."
            ),
            status_code=500,
        )

    # ========================================================
    # 6. BUILD RECRUITER-FACING RESULT
    # ========================================================

    final_candidates: List[
        Dict[str, Any]
    ] = []

    for candidate in ranked_candidates:

        if not isinstance(
            candidate,
            dict,
        ):

            logger.warning(
                "Invalid candidate ranking entry ignored"
            )

            continue

        candidate_id = get_candidate_id(
            candidate
        )

        candidate_name = get_candidate_name(
            candidate
        )

        final_candidates.append(
            {
                "rank": candidate.get(
                    "rank"
                ),

                "candidate_id": candidate_id,

                "candidate_name": candidate_name,

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
    # 7. VALIDATE FINAL CANDIDATE LIST
    # ========================================================

    if not final_candidates:

        logger.warning(
            "Ranking completed but produced "
            "no valid candidate results"
        )

        raise RankingError(
            message=(
                "No valid ranked candidates found."
            ),
            status_code=422,
        )

    # ========================================================
    # 8. SUMMARY COUNTS
    # ========================================================

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

    # ========================================================
    # 9. LOG SUMMARY
    # ========================================================

    logger.info(
        "Ranking and shortlisting completed: "
        "total=%s shortlisted=%s review=%s rejected=%s",
        len(final_candidates),
        shortlisted_count,
        review_count,
        rejected_count,
    )

    # ========================================================
    # 10. FINAL RESPONSE
    # ========================================================

    return {
        "status": "RANKED",

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


# ============================================================
# GET ONE CANDIDATE RANKING
# ============================================================

def get_candidate_ranking(
    candidate_id: str,
    shortlist_threshold: float = 80.0,
    review_threshold: float = 60.0,
) -> Dict[str, Any]:
    """
    Return ranking information for one candidate.

    The candidate's rank is calculated against
    ALL scored candidates.
    """

    logger.info(
        "Candidate ranking lookup started: "
        "candidate_id=%s",
        candidate_id,
    )

    # ========================================================
    # 1. RANK ALL CANDIDATES
    # ========================================================

    ranking_result = rank_all_candidates(
        shortlist_threshold=(
            shortlist_threshold
        ),
        review_threshold=(
            review_threshold
        ),
    )

    # ========================================================
    # 2. FIND REQUESTED CANDIDATE
    # ========================================================

    candidates = ranking_result[
        "candidates"
    ]

    for candidate in candidates:

        if (
            candidate.get(
                "candidate_id"
            )
            == candidate_id
        ):

            logger.info(
                "Candidate ranking found: "
                "candidate_id=%s rank=%s",
                candidate_id,
                candidate.get("rank"),
            )

            return {
                "status": "RANKED",
                "candidate": candidate,
            }

    # ========================================================
    # 3. CANDIDATE NOT FOUND
    # ========================================================

    logger.warning(
        "Candidate ranking not found: "
        "candidate_id=%s",
        candidate_id,
    )

    raise RankingError(
        message=(
            f"Candidate '{candidate_id}' "
            f"has no ranking result."
        ),
        status_code=404,
    )