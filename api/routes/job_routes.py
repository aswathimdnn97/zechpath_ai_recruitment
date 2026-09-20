from fastapi import APIRouter, HTTPException

from api.schemas.job_schema import JobResponse
from api.service.job_service import get_job


router = APIRouter(
    prefix="/api",
    tags=["Jobs"]
)


# ============================================================
# GET JOB STATUS
# ============================================================

@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse
)
def get_job_status(job_id: str):

    job = get_job(job_id)

    if job is None:

        raise HTTPException(
            status_code=404,
            detail={
                "status": "ERROR",
                "error_code": "JOB_NOT_FOUND",
                "message": (
                    f"Job '{job_id}' was not found."
                )
            }
        )

    return job