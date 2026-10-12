from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from jobs.recruitment_job_store import (
    RECRUITMENT_JOB_STORAGE_DIR,
    load_recruitment_job,
    save_recruitment_job,
)


# ============================================================
# RECRUITMENT JOB STATUS
# ============================================================

RECRUITMENT_JOB_ACTIVE = "ACTIVE"
RECRUITMENT_JOB_CLOSED = "CLOSED"


# ============================================================
# CREATE RECRUITMENT JOB
# ============================================================

def create_recruitment_job(
    jd_id: str,
) -> Dict[str, Any]:
    """
    Create a persistent recruitment job.

    One recruitment job represents one actual job/requisition.

    The generated job_id is stable and must be reused when
    scoring multiple candidates against the same job.
    """

    jd_id = jd_id.strip()

    if not jd_id:
        raise ValueError(
            "jd_id cannot be empty."
        )

    existing_job = get_active_recruitment_job_by_jd(
        jd_id
    )
    if existing_job is not None:
        return existing_job

    # Generate the actual recruitment job ID.
    job_id = f"JOB_{uuid4().hex[:12].upper()}"

    now = datetime.now(timezone.utc).isoformat()

    job = {
        "job_id": job_id,
        "jd_id": jd_id,
        "status": RECRUITMENT_JOB_ACTIVE,
        "created_at": now,
        "closed_at": None,
    }

    save_recruitment_job(job)

    return job


# ============================================================
# GET RECRUITMENT JOB
# ============================================================

def get_recruitment_job(
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve an existing recruitment job by job_id.
    """

    if not job_id:
        return None

    return load_recruitment_job(job_id)


def get_active_recruitment_job_by_jd(
    jd_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Return the canonical active recruitment job for a JD.

    Older data may contain multiple active records for one JD.
    Select the earliest created record so lookup remains stable;
    new API requests reuse that record instead of creating more.
    """

    if not isinstance(jd_id, str) or not jd_id.strip():
        return None

    normalized_jd_id = jd_id.strip().casefold()
    matching_jobs = []

    if not RECRUITMENT_JOB_STORAGE_DIR.exists():
        return None

    for job_file in RECRUITMENT_JOB_STORAGE_DIR.glob("JOB_*.json"):
        job = load_recruitment_job(job_file.stem)
        if not isinstance(job, dict):
            continue

        if (
            str(job.get("jd_id", "")).strip().casefold()
            == normalized_jd_id
            and job.get("status") == RECRUITMENT_JOB_ACTIVE
        ):
            matching_jobs.append(job)

    if not matching_jobs:
        return None

    return min(
        matching_jobs,
        key=lambda job: (
            str(job.get("created_at") or ""),
            str(job.get("job_id") or ""),
        ),
    )


def resolve_recruitment_job_id(
    job_id: Optional[str],
    jd_id: str,
) -> str:
    """
    Resolve an absent or unknown job ID using its JD association.

    A known ID must be active and associated with the supplied JD.
    Duplicate active IDs for the same JD resolve to one canonical ID.
    """

    job_id = (job_id or "").strip()

    if job_id and get_recruitment_job(job_id) is not None:
        validate_recruitment_job(
            job_id=job_id,
            jd_id=jd_id,
        )

    job = get_active_recruitment_job_by_jd(jd_id)
    if job is None:
        raise ValueError(
            f"No active recruitment job was found for JD '{jd_id}'. "
            "Create or retrieve it through /api/recruitment-jobs first."
        )

    return str(job["job_id"])


# ============================================================
# VALIDATE RECRUITMENT JOB
# ============================================================

def validate_recruitment_job(
    job_id: str,
    jd_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate that a recruitment job exists and is active.

    If jd_id is provided, also verify that the JD belongs
    to the specified recruitment job.
    """

    job = get_recruitment_job(job_id)

    if job is None:
        raise ValueError(
            f"Recruitment job '{job_id}' was not found."
        )

    if job.get("status") != RECRUITMENT_JOB_ACTIVE:
        raise ValueError(
            f"Recruitment job '{job_id}' is not active."
        )

    if jd_id is not None:

        jd_id = jd_id.strip()

        stored_jd_id = job.get("jd_id")

        if (
            str(stored_jd_id or "").strip().casefold()
            != jd_id.casefold()
        ):
            raise ValueError(
                f"JD '{jd_id}' does not belong to "
                f"recruitment job '{job_id}'. "
                f"Expected JD '{stored_jd_id}'."
            )

    return job


# ============================================================
# CLOSE RECRUITMENT JOB
# ============================================================

def close_recruitment_job(
    job_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Close an active recruitment job.

    A closed recruitment job should no longer be used
    for new candidate scoring.
    """

    job = get_recruitment_job(job_id)

    if job is None:
        return None

    if job.get("status") == RECRUITMENT_JOB_CLOSED:
        return job

    job["status"] = RECRUITMENT_JOB_CLOSED
    job["closed_at"] = datetime.now(
        timezone.utc
    ).isoformat()

    save_recruitment_job(job)

    return job