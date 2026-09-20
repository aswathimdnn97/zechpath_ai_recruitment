import json
from pathlib import Path
from typing import Any, Dict, Optional


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

JOB_STORAGE_DIR = BASE_DIR / "data" / "jobs"

JOB_STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SAVE JOB
# ============================================================

def save_job(job: Dict[str, Any]) -> None:
    """
    Save a job record as JSON.
    """

    job_id = job["job_id"]

    job_file = JOB_STORAGE_DIR / f"{job_id}.json"

    with open(
        job_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            job,
            file,
            indent=2
        )


# ============================================================
# LOAD JOB
# ============================================================

def load_job(
    job_id: str
) -> Optional[Dict[str, Any]]:
    """
    Load a job by job_id.
    """

    job_file = JOB_STORAGE_DIR / f"{job_id}.json"

    if not job_file.exists():
        return None

    with open(
        job_file,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# UPDATE JOB
# ============================================================

def update_job(
    job_id: str,
    updates: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Update an existing job.
    """

    job = load_job(job_id)

    if job is None:
        return None

    job.update(updates)

    save_job(job)

    return job