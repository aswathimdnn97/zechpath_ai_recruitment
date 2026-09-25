from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from jobs.job_store import (
    load_job,
    save_job,
    update_job,
)


# ============================================================
# TASK STATUS
# ============================================================

TASK_QUEUED = "QUEUED"
TASK_PROCESSING = "PROCESSING"
TASK_COMPLETED = "COMPLETED"
TASK_FAILED = "FAILED"


# ============================================================
# TASK TYPES
# ============================================================

RESUME_PARSING = "RESUME_PARSING"
CANDIDATE_SCORING = "CANDIDATE_SCORING"
JD_PARSING = "JD_PARSING"


# ============================================================
# CREATE TASK
# ============================================================

def create_task(
    task_type: str,
    candidate_id: Optional[str] = None,
    jd_id: Optional[str] = None,
    recruitment_job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an asynchronous task.

    task_id:
        Unique execution ID.

    recruitment_job_id:
        Persistent recruitment job/requisition ID.
    """

    task_id = f"TASK_{uuid4().hex[:12].upper()}"

    now = datetime.now(timezone.utc).isoformat()

    task = {
        "task_id": task_id,
        "task_type": task_type,
        "candidate_id": candidate_id,
        "jd_id": jd_id,
        "recruitment_job_id": recruitment_job_id,
        "status": TASK_QUEUED,
        "progress": 0,
        "created_at": now,
        "started_at": None,
        "completed_at": None,
        "result_reference": None,
        "error": None,
    }

    save_job(task)

    return task


# ============================================================
# GET TASK
# ============================================================

def get_task(
    task_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a task using its task_id.
    """

    return load_job(task_id)


# ============================================================
# MARK TASK PROCESSING
# ============================================================

def mark_task_processing(
    task_id: str,
    progress: int = 0,
) -> Optional[Dict[str, Any]]:
    """
    Mark task as PROCESSING.
    """

    return update_job(
        task_id,
        {
            "status": TASK_PROCESSING,
            "progress": progress,
            "started_at": datetime.now(
                timezone.utc
            ).isoformat(),
        },
    )


# ============================================================
# UPDATE TASK PROGRESS
# ============================================================

def update_task_progress(
    task_id: str,
    progress: int,
) -> Optional[Dict[str, Any]]:
    """
    Update task progress.

    Progress is always limited to 0-100.
    """

    progress = max(
        0,
        min(progress, 100),
    )

    return update_job(
        task_id,
        {
            "progress": progress,
        },
    )


# ============================================================
# MARK TASK COMPLETED
# ============================================================

def mark_task_completed(
    task_id: str,
    result_reference: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Mark task as COMPLETED.
    """

    return update_job(
        task_id,
        {
            "status": TASK_COMPLETED,
            "progress": 100,
            "completed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "result_reference": result_reference,
            "error": None,
        },
    )


# ============================================================
# MARK TASK FAILED
# ============================================================

def mark_task_failed(
    task_id: str,
    error_code: str,
    message: str,
) -> Optional[Dict[str, Any]]:
    """
    Mark task as FAILED.
    """

    return update_job(
        task_id,
        {
            "status": TASK_FAILED,
            "error": {
                "error_code": error_code,
                "message": message,
            },
        },
    )