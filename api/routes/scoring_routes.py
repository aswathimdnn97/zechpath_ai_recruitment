from fastapi import APIRouter, BackgroundTasks

from api.schemas.scoring_schema import (
    ScoreRequest,
)

from api.service.job_service import (
    create_job,
    CANDIDATE_SCORING,
)

from api.service.scoring_service import (
    load_scoring_result,
)

from api.utils.exception import (
    ScoringError,
)

from workers.ats_workers import (
    run_scoring_job,
)


router = APIRouter(
    prefix="/scoring",
    tags=["Scoring"],
)


# ============================================================
# START SCORING JOB
# ============================================================

@router.post(
    "/candidates/{candidate_id}/score"
)
def score_candidate(
    candidate_id: str,
    request: ScoreRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start an asynchronous candidate scoring job.

    If a scoring result already exists for the same
    candidate + JD combination, the existing result
    is returned instead of creating another job.

    Flow:

        POST scoring request
                |
                v
        Check existing result
             /       \
          EXISTS    NOT EXISTS
            |           |
            v           v
       Return score   Create job
                          |
                          v
                      QUEUED
                          |
                          v
                    Background worker
                          |
                          v
                    Save score result
    """

    jd_id = request.jd_id.strip()

    # ========================================================
    # 1. VALIDATE JD ID
    # ========================================================

    if not jd_id:

        raise ScoringError(
            message="jd_id is required.",
            status_code=422,
        )

    # ========================================================
    # 2. CHECK EXISTING SCORING RESULT
    # ========================================================

    try:

        existing_result = load_scoring_result(
            candidate_id=candidate_id,
            jd_id=jd_id,
        )

        # ----------------------------------------------------
        # Existing result found
        # ----------------------------------------------------

        return {
            "candidate_id": candidate_id,
            "jd_id": jd_id,
            "status": "SCORED",
            "message": (
                "Candidate has already been scored "
                "for this JD."
            ),
            "score": existing_result,
        }

    except ScoringError as error:

        # ----------------------------------------------------
        # 404 means no previous scoring result.
        #
        # This is expected and should NOT stop the request.
        # ----------------------------------------------------

        if error.status_code != 404:
            raise

    # ========================================================
    # 3. CREATE NEW ASYNC SCORING JOB
    # ========================================================

    job = create_job(
        job_type=CANDIDATE_SCORING,
        candidate_id=candidate_id,
        jd_id=jd_id,
    )

    # ========================================================
    # 4. START BACKGROUND SCORING
    # ========================================================

    background_tasks.add_task(
        run_scoring_job,
        job["job_id"],
        candidate_id,
        jd_id,
    )

    # ========================================================
    # 5. RETURN QUEUED RESPONSE
    # ========================================================

    return {
        "job_id": job["job_id"],
        "candidate_id": candidate_id,
        "jd_id": jd_id,
        "job_type": CANDIDATE_SCORING,
        "status": "QUEUED",
    }


# ============================================================
# GET COMPLETED SCORING RESULT
# ============================================================

@router.get(
    "/candidates/{candidate_id}/score"
)
def get_candidate_score(
    candidate_id: str,
    jd_id: str,
):
    """
    Return the saved scoring result for a
    candidate + JD combination.
    """

    # ========================================================
    # 1. VALIDATE JD ID
    # ========================================================

    jd_id = jd_id.strip()

    if not jd_id:

        raise ScoringError(
            message="jd_id is required.",
            status_code=422,
        )

    # ========================================================
    # 2. LOAD SAVED RESULT
    # ========================================================

    score_result = load_scoring_result(
        candidate_id=candidate_id,
        jd_id=jd_id,
    )

    # ========================================================
    # 3. RETURN RESULT
    # ========================================================

    return {
        "candidate_id": candidate_id,
        "jd_id": jd_id,
        "status": "SCORED",
        "score": score_result,
    }
