import json
from pathlib import Path
from typing import Any, Dict, Optional


BASE_DIR = Path(__file__).resolve().parents[1]

JOB_STORAGE_DIR = (
    BASE_DIR / "data" / "jobs"
)

JOB_STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def save_job(
    job: Dict[str, Any],
) -> None:

    task_id = job["task_id"]

    job_file = (
        JOB_STORAGE_DIR
        / f"{task_id}.json"
    )

    with open(
        job_file,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            job,
            file,
            indent=2,
        )


def load_job(
    task_id: str,
) -> Optional[Dict[str, Any]]:

    job_file = (
        JOB_STORAGE_DIR
        / f"{task_id}.json"
    )

    if not job_file.exists():
        return None

    with open(
        job_file,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


def update_job(
    task_id: str,
    updates: Dict[str, Any],
) -> Optional[Dict[str, Any]]:

    job = load_job(task_id)

    if job is None:
        return None

    job.update(updates)

    save_job(job)

    return job