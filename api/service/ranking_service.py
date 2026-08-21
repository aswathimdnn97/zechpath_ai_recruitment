from pathlib import Path
import json
from typing import Any, Dict, List

from fastapi import HTTPException

from scoring.ranking.candidate_ranker import (
    rank_candidates,
)

from scoring.ranking.shortlisting_engine import (
    shortlist_candidates,
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

    if not SCORING_RESULTS_DIR.exists():
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

            if isinstance(data, dict):
                results.append(data)

        except (
            json.JSONDecodeError,
            OSError,
        ):
            # Ignore invalid scoring files.
            continue

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

    if isinstance(candidate_id, str):
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

    The scoring service attaches candidate_name
    AFTER ATS scoring.

    Therefore ranking does not need to access
    candidate_identity/.
    """

    candidate_name = candidate.get(
        "candidate_name"
    )

    if (
        isinstance(candidate_name, str)
        and candidate_name.strip()
    ):
        return candidate_name.strip()

    # Fallback to candidate ID if name is unavailable.

    return get_candidate_id(candidate)


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
        return 0.0


# ============================================================
# RANK + SHORTLIST ALL CANDIDATES
# ============================================================

def rank_all_candidates(
    shortlist_threshold: float = 80.0,
    review_threshold: float = 60.0,
) -> Dict[str, Any]:
    """
    Rank all scored candidates.

    Flow:

        scoring_results/
              |
              v
        Load scores
              |
              v
        Rank by final ATS score
              |
              v
        SHORTLIST / REVIEW / REJECT
              |
              v
        Recruiter-friendly response
    """

    # ========================================================
    # 1. LOAD SCORING RESULTS
    # ========================================================

    scoring_results = (
        load_scoring_results()
    )

    if not scoring_results:

        raise HTTPException(
            status_code=404,
            detail="No scored candidates found.",
        )

    # ========================================================
    # 2. RANK CANDIDATES
    # ========================================================

    ranked_candidates = rank_candidates(
        scoring_results
    )

    # ========================================================
    # 3. APPLY SHORTLISTING RULES
    # ========================================================

    ranked_candidates = shortlist_candidates(
        ranked_candidates,
        shortlist_threshold=(
            shortlist_threshold
        ),
        review_threshold=(
            review_threshold
        ),
    )

    # ========================================================
    # 4. BUILD RECRUITER-FACING RESULT
    # ========================================================

    final_candidates: List[
        Dict[str, Any]
    ] = []

    for candidate in ranked_candidates:

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
    # 5. SUMMARY COUNTS
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
    # 6. FINAL RESPONSE
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

    IMPORTANT:

    The candidate's rank is calculated against
    ALL scored candidates.

    Example:

        Candidate A = 90
        Candidate B = 81
        Candidate C = 75

        GET /ranking/CandidateB

        returns:

            rank = 2
    """

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
            candidate.get("candidate_id")
            == candidate_id
        ):

            return {
                "status": "RANKED",

                "candidate": candidate,
            }

    # ========================================================
    # 3. CANDIDATE NOT FOUND
    # ========================================================

    raise HTTPException(
        status_code=404,
        detail=(
            f"Candidate "
            f"'{candidate_id}' "
            f"has no ranking result."
        ),
    )