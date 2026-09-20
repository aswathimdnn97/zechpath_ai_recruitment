"""
ranking_service.py

Service layer for candidate ranking and shortlisting.

Responsibilities
----------------
1. Load persisted ATS scoring results.
2. Support nested scoring-result storage:

       data/
       └── candidates/
           └── scoring_results/
               ├── CAN_001/
               │   ├── JD_001.json
               │   └── JD_002.json
               └── CAN_002/
                   └── JD_001.json

3. Extract candidate information from scoring results.
4. Rank candidates using the ranking engine.
5. Apply shortlisting rules.
6. Build recruiter-facing responses.

Important
---------
This service does NOT calculate ATS scores.

ATS scores are already calculated by scoring_service.py
and persisted to disk.
"""


from pathlib import Path
import json
import logging
from typing import Any, Dict, List, Optional


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

def load_scoring_results(
    jd_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Load persisted ATS scoring results.

    Scoring results are stored using the structure:

        scoring_results/
            candidate_id/
                jd_id.json

    Example:

        scoring_results/
            CAN_001/
                JD_EVAL_001.json
            CAN_002/
                JD_EVAL_001.json

    Parameters
    ----------
    jd_id:
        Optional job-description ID.

        If supplied, only scoring results belonging
        to that JD are returned.

        If None, all scoring results are returned.

    Returns
    -------
    list[dict]
        Loaded scoring results.
    """

    logger.info(
        "Loading scoring results from: %s",
        SCORING_RESULTS_DIR,
    )

    # --------------------------------------------------------
    # Check directory
    # --------------------------------------------------------

    if not SCORING_RESULTS_DIR.exists():

        logger.warning(
            "Scoring results directory not found: %s",
            SCORING_RESULTS_DIR,
        )

        return []

    # --------------------------------------------------------
    # Normalize JD filter
    # --------------------------------------------------------

    normalized_jd_id = None

    if isinstance(jd_id, str):
        normalized_jd_id = Path(
            jd_id
        ).stem.strip()

        if not normalized_jd_id:
            normalized_jd_id = None

    # --------------------------------------------------------
    # Recursively find scoring files
    # --------------------------------------------------------

    scoring_files = sorted(
        SCORING_RESULTS_DIR.rglob("*.json")
    )

    logger.info(
        "Scoring result files found: count=%s",
        len(scoring_files),
    )

    results: List[Dict[str, Any]] = []

    # --------------------------------------------------------
    # Read each scoring result
    # --------------------------------------------------------

    for scoring_file in scoring_files:

        try:

            with scoring_file.open(
                "r",
                encoding="utf-8",
            ) as file:

                data = json.load(file)

        except json.JSONDecodeError:

            logger.warning(
                "Invalid JSON scoring result ignored: %s",
                scoring_file,
            )

            continue

        except OSError:

            logger.warning(
                "Unable to read scoring result file: %s",
                scoring_file,
            )

            continue

        # ----------------------------------------------------
        # Validate basic structure
        # ----------------------------------------------------

        if not isinstance(
            data,
            dict,
        ):

            logger.warning(
                "Invalid scoring result structure ignored: %s",
                scoring_file,
            )

            continue

        # ----------------------------------------------------
        # Get candidate ID
        # ----------------------------------------------------

        candidate_id = data.get(
            "candidate_id"
        )

        if not isinstance(
            candidate_id,
            str,
        ) or not candidate_id.strip():

            logger.warning(
                "Scoring result missing candidate_id: %s",
                scoring_file,
            )

            continue

        candidate_id = candidate_id.strip()

        # ----------------------------------------------------
        # Get JD ID
        # ----------------------------------------------------

        result_jd_id = data.get(
            "jd_id"
        )

        if isinstance(
            result_jd_id,
            str,
        ):

            result_jd_id = Path(
                result_jd_id
            ).stem.strip()

        else:

            result_jd_id = ""

        # ----------------------------------------------------
        # Fallback JD ID from filename
        # ----------------------------------------------------
        #
        # This makes the loader more robust if an older
        # scoring file does not contain jd_id.
        #
        # Example:
        #
        # CAN_001/JD_EVAL_001.json
        #
        # → JD_EVAL_001
        #
        # ----------------------------------------------------

        if not result_jd_id:

            result_jd_id = scoring_file.stem

            logger.debug(
                "JD ID recovered from filename: "
                "candidate_id=%s jd_id=%s",
                candidate_id,
                result_jd_id,
            )

            data["jd_id"] = result_jd_id

        # ----------------------------------------------------
        # Apply JD filter
        # ----------------------------------------------------

        if (
            normalized_jd_id
            and result_jd_id != normalized_jd_id
        ):

            continue

        # ----------------------------------------------------
        # Store result
        # ----------------------------------------------------

        results.append(
            data
        )

        logger.debug(
            "Scoring result loaded: "
            "candidate_id=%s jd_id=%s file=%s",
            candidate_id,
            result_jd_id,
            scoring_file,
        )

    # --------------------------------------------------------
    # Final logging
    # --------------------------------------------------------

    logger.info(
        "Scoring results loaded: count=%s",
        len(results),
    )

    if normalized_jd_id:

        logger.info(
            "Scoring results filtered by jd_id=%s",
            normalized_jd_id,
        )

    return results


# ============================================================
# GET CANDIDATE ID
# ============================================================

def get_candidate_id(
    candidate: Dict[str, Any],
) -> str:
    """
    Extract candidate ID from a scoring result.
    """

    if not isinstance(
        candidate,
        dict,
    ):
        return ""

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
    Extract candidate name from a scoring result.

    If candidate_name is unavailable, candidate_id
    is used as a fallback.
    """

    if not isinstance(
        candidate,
        dict,
    ):
        return ""

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
    Extract final ATS score from a scoring result.

    Expected structure:

        {
            "candidate_score": {
                "final_score": 87.5
            }
        }

    Invalid or missing scores return 0.0.
    """

    if not isinstance(
        candidate,
        dict,
    ):
        return 0.0

    candidate_score = candidate.get(
        "candidate_score",
        {},
    )

    if not isinstance(
        candidate_score,
        dict,
    ):

        logger.warning(
            "Invalid candidate_score structure: "
            "candidate_id=%s",
            get_candidate_id(candidate),
        )

        return 0.0

    score = candidate_score.get(
        "final_score",
        0.0,
    )

    try:

        numeric_score = float(
            score
        )

    except (
        TypeError,
        ValueError,
    ):

        logger.warning(
            "Invalid candidate score found: "
            "candidate_id=%s score=%s",
            get_candidate_id(candidate),
            score,
        )

        return 0.0

    # --------------------------------------------------------
    # Validate score range
    # --------------------------------------------------------

    if numeric_score < 0:

        logger.warning(
            "Candidate score below 0: "
            "candidate_id=%s score=%s",
            get_candidate_id(candidate),
            numeric_score,
        )

        return 0.0

    if numeric_score > 100:

        logger.warning(
            "Candidate score above 100: "
            "candidate_id=%s score=%s",
            get_candidate_id(candidate),
            numeric_score,
        )

        return 100.0

    return numeric_score


# ============================================================
# RANK CANDIDATES
# ============================================================

def rank_all_candidates(
    shortlist_threshold: float = 80.0,
    review_threshold: float = 60.0,
    jd_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rank all scored candidates and apply
    shortlisting rules.

    Parameters
    ----------
    shortlist_threshold:
        Minimum score required for SHORTLIST.

    review_threshold:
        Minimum score required for REVIEW.

    jd_id:
        Optional JD ID.

        If supplied, candidates are ranked only against
        that specific JD.

    Returns
    -------
    dict
        Recruiter-facing ranking and shortlisting result.
    """

    logger.info(
        "Ranking started: "
        "shortlist_threshold=%s "
        "review_threshold=%s "
        "jd_id=%s",
        shortlist_threshold,
        review_threshold,
        jd_id,
    )

    # ========================================================
    # 1. LOAD SCORING RESULTS
    # ========================================================

    scoring_results = load_scoring_results(
        jd_id=jd_id
    )

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

        if not candidate_id:

            logger.warning(
                "Ranked candidate missing candidate_id; "
                "entry ignored"
            )

            continue

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
    jd_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return ranking information for one candidate.

    The candidate's rank is calculated against all
    scored candidates for the selected JD.

    Parameters
    ----------
    candidate_id:
        Candidate ID to find.

    shortlist_threshold:
        Minimum score for SHORTLIST.

    review_threshold:
        Minimum score for REVIEW.

    jd_id:
        Optional JD ID.

        If supplied, ranking is calculated only against
        candidates scored for that JD.
    """

    logger.info(
        "Candidate ranking lookup started: "
        "candidate_id=%s jd_id=%s",
        candidate_id,
        jd_id,
    )

    # ========================================================
    # VALIDATE CANDIDATE ID
    # ========================================================

    if not isinstance(
        candidate_id,
        str,
    ) or not candidate_id.strip():

        raise RankingError(
            message="Candidate ID is required.",
        )

    candidate_id = candidate_id.strip()

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
        jd_id=jd_id,
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
        "candidate_id=%s jd_id=%s",
        candidate_id,
        jd_id,
    )

    raise RankingError(
        message=(
            f"Candidate '{candidate_id}' "
            f"has no ranking result."
        ),
    )
