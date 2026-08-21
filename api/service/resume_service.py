from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, HTTPException


# Project root directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Resume storage directory
RESUME_STORAGE_DIR = BASE_DIR / "data" / "resumes"

# Allowed resume file types
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def save_resume(file: UploadFile) -> dict:
    """
    Validate and save an uploaded resume.

    Returns information about the saved resume.
    """

    # 1. Validate filename
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required."
        )

    # 2. Get file extension
    file_extension = Path(file.filename).suffix.lower()

    # 3. Validate file type
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX resumes are supported."
        )

    # 4. Generate unique resume ID
    resume_id = f"RES_{uuid4().hex[:12].upper()}"

    # 5. Create storage directory if it doesn't exist
    RESUME_STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # 6. Create safe stored filename
    stored_filename = f"{resume_id}{file_extension}"

    # 7. Create complete file path
    file_path = RESUME_STORAGE_DIR / stored_filename

    # 8. Save uploaded file
    try:
        with file_path.open("wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                buffer.write(chunk)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to save resume."
        ) from exc

    # 9. Return resume information
    return {
        "resume_id": resume_id,
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "file_path": str(file_path),
        "status": "UPLOADED"
    }