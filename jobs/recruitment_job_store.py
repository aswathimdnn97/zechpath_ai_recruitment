import json
from pathlib import Path
from typing import Any, Dict, Optional


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

RECRUITMENT_JOB_STORAGE_DIR = (
    BASE_DIR / "data" / "recruitment_jobs"
)

RECRUITMENT_JOB_STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# SAVE RECRUITMENT JOB
# ============================================================

def save_recruitment_job(
    job: Dict[str, Any]
) -> None:
    """
    Save a persistent recruitment job record as JSON.
    """

    job_id = job["job_id"]

    job_file = (
        RECRUITMENT_JOB_STORAGE_DIR
        / f"{job_id}.json"
    )

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
# LOAD RECRUITMENT JOB
# ============================================================

def load_recruitment_job(
    job_id: str
) -> Optional[Dict[str, Any]]:
    """
    Load a persistent recruitment job by job_id.
    """

    job_file = (
        RECRUITMENT_JOB_STORAGE_DIR
        / f"{job_id}.json"
    )

    if not job_file.exists():
        return None

    with open(
        job_file,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)