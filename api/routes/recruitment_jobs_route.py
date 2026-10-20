from fastapi import APIRouter, HTTPException

from api.schemas.recruitment_job_schema import (
    RecruitmentJobCreateRequest,
    RecruitmentJobResponse,
)

from api.service.recruitment_job_service import (
    create_recruitment_job,
    get_active_recruitment_job_by_jd,
    get_recruitment_job,
)


router = APIRouter(
    prefix="/api/recruitment-jobs",
    tags=["Recruitment Jobs"],
)


@router.get(
    "/by-jd/{jd_id}",
    response_model=RecruitmentJobResponse,
)
def get_recruitment_job_by_jd_api(
    jd_id: str,
):
    """Look up the active recruitment job associated with a JD."""

    jd_id = jd_id.strip()
    if not jd_id:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "ERROR",
                "error_code": "INVALID_JD_ID",
                "message": "jd_id cannot be empty.",
            },
        )

    job = get_active_recruitment_job_by_jd(jd_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "ERROR",
                "error_code": "RECRUITMENT_JOB_NOT_FOUND",
                "message": (
                    f"No active recruitment job was found for JD '{jd_id}'."
                ),
            },
        )

    return job


@router.get(
    "/{job_id}",
    response_model=RecruitmentJobResponse,
)
def get_recruitment_job_api(
    job_id: str,
):
    """Retrieve a recruitment job by its persistent job ID."""

    job = get_recruitment_job(job_id.strip())
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={
                "status": "ERROR",
                "error_code": "RECRUITMENT_JOB_NOT_FOUND",
                "message": f"Recruitment job '{job_id}' was not found.",
            },
        )

    return job


# ============================================================
# CREATE RECRUITMENT JOB
# ============================================================

@router.post(
    "",
    response_model=RecruitmentJobResponse,
)
def create_recruitment_job_api(
    request: RecruitmentJobCreateRequest,
):
    """
    Create a persistent recruitment job.

    The generated job_id represents the actual recruitment
    position and will be shared by all candidates scored
    against this job.
    """

    jd_id = request.jd_id.strip()

    if not jd_id:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "ERROR",
                "error_code": "INVALID_JD_ID",
                "message": "jd_id cannot be empty.",
            },
        )

    try:

        job = create_recruitment_job(
            jd_id=jd_id
        )

        return job

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail={
                "status": "ERROR",
                "error_code": "RECRUITMENT_JOB_CREATION_FAILED",
                "message": str(exc),
            },
        )