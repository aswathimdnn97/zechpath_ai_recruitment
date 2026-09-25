from fastapi import APIRouter, BackgroundTasks

from api.schemas.scoring_schema import ScoreRequest

from api.service.job_service import (
    create_task,
    CANDIDATE_SCORING,
)

from api.service.recruitment_job_service import (
    validate_recruitment_job,
)

from api.service.scoring_service import (
    load_scoring_result,
)

from api.utils.exception import ScoringError

from workers.ats_workers import run_scoring_job


router = APIRouter(
    prefix="/scoring",
    tags=["Scoring"],
)


# ============================================================
# START SCORING TASK
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
    Start an asynchronous candidate scoring task.

    Architecture:

        Recruitment Job
        JOB_XXXXXXXXXXXX
             |
             |-- Candidate 1 -> TASK_XXXXXXXXXXXX
             |-- Candidate 2 -> TASK_XXXXXXXXXXXX
             |-- Candidate 3 -> TASK_XXXXXXXXXXXX

    recruitment_job_id:
        Persistent recruitment job/requisition ID.

    task_id:
        Unique asynchronous scoring execution ID.

    Scoring result identity:

        recruitment_job_id + candidate_id
    """

    # ========================================================
    # 1. READ REQUEST DATA
    # ========================================================

    jd_id = request.jd_id.strip()
    job_id = request.job_id.strip()

    # ========================================================
    # 2. VALIDATE JD ID
    # ========================================================

    if not jd_id:
        raise ScoringError(
            message="jd_id is required.",
            status_code=422,
        )

    # ========================================================
    # 3. VALIDATE RECRUITMENT JOB ID
    # ========================================================

    if not job_id:
        raise ScoringError(
            message="job_id is required.",
            status_code=422,
        )

    # ========================================================
    # 4. VALIDATE RECRUITMENT JOB
    #
    # Confirms:
    #
    #   JOB_XXXXXXXXXXXX exists
    #   JOB is ACTIVE
    #   jd_id belongs to this job
    # ========================================================

    try:

        validate_recruitment_job(
            job_id=job_id,
            jd_id=jd_id,
        )

    except ValueError as exc:

        raise ScoringError(
            message=str(exc),
            status_code=400,
        )

    # ========================================================
    # 5. CHECK EXISTING SCORING RESULT
    #
    # Result identity:
    #
    #       job_id + candidate_id
    #
    # NOT:
    #
    #       jd_id + candidate_id
    # ========================================================

    try:

        existing_result = load_scoring_result(
            candidate_id=candidate_id,
            job_id=job_id,
        )

        # ----------------------------------------------------
        # Existing result found
        # ----------------------------------------------------

        return {
            "candidate_id": candidate_id,
            "jd_id": jd_id,
            "job_id": job_id,
            "status": "SCORED",
            "message": (
                "Candidate has already been scored "
                "for this job."
            ),
            "score": existing_result,
        }

    except ScoringError as error:

        # ----------------------------------------------------
        # 404 means no previous scoring result.
        #
        # This is expected.
        # ----------------------------------------------------

        if error.status_code != 404:
            raise

    # ========================================================
    # 6. CREATE ASYNC TASK
    #
    # IMPORTANT:
    #
    # create_task() generates:
    #
    #       TASK_XXXXXXXXXXXX
    #
    # This is NOT the recruitment job ID.
    # ========================================================

    task = create_task(
        task_type=CANDIDATE_SCORING,
        candidate_id=candidate_id,
        jd_id=jd_id,
        recruitment_job_id=job_id,
    )

    # ========================================================
    # 7. START BACKGROUND SCORING TASK
    # ========================================================

    background_tasks.add_task(
        run_scoring_job,
        task["task_id"],
        candidate_id,
        jd_id,
        job_id,
    )

    # ========================================================
    # 8. RETURN QUEUED RESPONSE
    # ========================================================

    return {
        "task_id": task["task_id"],
        "candidate_id": candidate_id,
        "jd_id": jd_id,
        "job_id": job_id,
        "task_type": CANDIDATE_SCORING,
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
    job_id: str,
):
    """
    Return the saved scoring result for:

        candidate_id + job_id

    job_id:
        Persistent recruitment job/requisition.

    jd_id:
        JD associated with the recruitment job.
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
    # 2. VALIDATE RECRUITMENT JOB ID
    # ========================================================

    job_id = job_id.strip()

    if not job_id:
        raise ScoringError(
            message="job_id is required.",
            status_code=422,
        )

    # ========================================================
    # 3. VALIDATE RECRUITMENT JOB
    # ========================================================

    try:

        validate_recruitment_job(
            job_id=job_id,
            jd_id=jd_id,
        )

    except ValueError as exc:

        raise ScoringError(
            message=str(exc),
            status_code=400,
        )

    # ========================================================
    # 4. LOAD SAVED RESULT
    #
    # Storage:
    #
    # data/candidates/scoring_results/
    #     {job_id}/
    #         {candidate_id}.json
    # ========================================================

    score_result = load_scoring_result(
        candidate_id=candidate_id,
        job_id=job_id,
    )

    # ========================================================
    # 5. RETURN RESULT
    # ========================================================

    return {
        "candidate_id": candidate_id,
        "jd_id": jd_id,
        "job_id": job_id,
        "status": "SCORED",
        "score": score_result,
    }