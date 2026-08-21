from pathlib import Path
from uuid import uuid4
import json

from fastapi import HTTPException

from document_processing.resume.resume_pipeline import resume_pipeline


BASE_DIR = Path(__file__).resolve().parents[2]

RESUME_STORAGE_DIR = BASE_DIR / "data" / "resumes"
CANDIDATE_STORAGE_DIR = BASE_DIR / "data" / "candidates"/"candidate_profile"


def parse_resume_by_id(resume_id: str) -> dict:
    """
    Find a saved resume, parse it using the existing
    resume pipeline, save the parsed candidate data,
    and return the candidate ID.
    """

    # 1. Find the saved resume
    matching_files = list(
        RESUME_STORAGE_DIR.glob(f"{resume_id}.*")
    )

    if not matching_files:
        raise HTTPException(
            status_code=404,
            detail=f"Resume '{resume_id}' not found."
        )

    resume_path = matching_files[0]

    # 2. Parse the resume
    try:
        parsed_data = resume_pipeline(
            str(resume_path)
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to parse resume."
        ) from exc

    # 3. Generate candidate ID
    candidate_id = parsed_data["candidate_id"]

    # 4. Create candidate storage directory
    CANDIDATE_STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # 5. Create candidate file path
    candidate_file = (
        CANDIDATE_STORAGE_DIR /
        f"{candidate_id}.json"
    )

    # 6. Save parsed candidate data
    try:
        with candidate_file.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                parsed_data,
                file,
                indent=4,
                ensure_ascii=False,
                default=str
            )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to save parsed candidate data."
        ) from exc

    
    # 7. Return result
    return {
        "resume_id": resume_id,
        "candidate_id": candidate_id,
        "status": "PARSED",
        "candidate": parsed_data
    }