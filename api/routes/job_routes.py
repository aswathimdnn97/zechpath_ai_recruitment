from fastapi import APIRouter, HTTPException

from api.schemas.job_schema import JobResponse
from api.service.job_service import get_task


router = APIRouter(
    prefix="/api",
    tags=["Tasks"]
)


# ============================================================
# GET TASK STATUS
# ============================================================

@router.get(
    "/tasks/{task_id}",
    response_model=JobResponse
)
def get_task_status(task_id: str):

    task = get_task(task_id)

    if task is None:

        raise HTTPException(
            status_code=404,
            detail={
                "status": "ERROR",
                "error_code": "TASK_NOT_FOUND",
                "message": (
                    f"Task '{task_id}' was not found."
                )
            }
        )

    return task