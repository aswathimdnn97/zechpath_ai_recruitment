from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from jobs.job_store import (
    load_job,
    save_job,
    update_job,
)


# ============================================================
# JOB STATUS
# ============================================================

JOB_QUEUED = "QUEUED"
JOB_PROCESSING = "PROCESSING"
JOB_COMPLETED = "COMPLETED"
JOB_FAILED = "FAILED"


# ============================================================
# JOB TYPES
# ============================================================

RESUME_PARSING = "RESUME_PARSING"
CANDIDATE_SCORING = "CANDIDATE_SCORING"


# ============================================================
# CREATE JOB
# ============================================================

def create_job(
    job_type: str,
    candidate_id: Optional[str] = None,
    jd_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new asynchronous job.
    """

    job_id = (
        f"JOB_"
        f"{uuid4().hex[:12].upper()}"
    )

    now = datetime.now(timezone.utc).isoformat()

    job = {
        "job_id": job_id,
        "job_type": job_type,
        "candidate_id": candidate_id,
        "jd_id": jd_id,

        "status": JOB_QUEUED,

        "progress": 0,

        "created_at": now,
        "started_at": None,
        "completed_at": None,

        "result_reference": None,

        "error": None,
    }

    save_job(job)

    return job


# ============================================================
# GET JOB
# ============================================================

def get_job(
    job_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get job information.
    """

    return load_job(job_id)


# ============================================================
# MARK JOB AS PROCESSING
# ============================================================

def mark_job_processing(
    job_id: str,
    progress: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Mark job as PROCESSING.
    """

    return update_job(
        job_id,
        {
            "status": JOB_PROCESSING,
            "progress": progress,
            "started_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
    )


# ============================================================
# UPDATE JOB PROGRESS
# ============================================================

def update_job_progress(
    job_id: str,
    progress: int
) -> Optional[Dict[str, Any]]:
    """
    Update processing progress.
    """

    progress = max(
        0,
        min(progress, 100)
    )

    return update_job(
        job_id,
        {
            "progress": progress
        }
    )


# ============================================================
# MARK JOB AS COMPLETED
# ============================================================

def mark_job_completed(
    job_id: str,
    result_reference: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Mark job as completed.
    """

    return update_job(
        job_id,
        {
            "status": JOB_COMPLETED,
            "progress": 100,
            "completed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "result_reference": result_reference,
            "error": None,
        }
    )


# ============================================================
# MARK JOB AS FAILED
# ============================================================

def mark_job_failed(
    job_id: str,
    error_code: str,
    message: str
) -> Optional[Dict[str, Any]]:
    """
    Mark job as failed.
    """

    return update_job(
        job_id,
        {
            "status": JOB_FAILED,
            "error": {
                "error_code": error_code,
                "message": message,
            },
        }
    )