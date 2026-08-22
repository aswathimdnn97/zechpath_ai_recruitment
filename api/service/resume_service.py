from pathlib import Path
from uuid import uuid4
import logging

from fastapi import UploadFile

from api.utils.exception import (
    ResumeUploadError,
)


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(
    __name__
)


# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RESUME_STORAGE_DIR = (
    BASE_DIR
    / "data"
    / "resumes"
)


# ============================================================
# ALLOWED FILE TYPES
# ============================================================

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


# ============================================================
# SAVE RESUME
# ============================================================

def save_resume(
    file: UploadFile,
) -> dict:
    """
    Validate and save an uploaded resume.

    Expected upload/storage errors are raised as
    ResumeUploadError and handled centrally by FastAPI.

    Returns information about the saved resume.
    """

    logger.info(
        "Resume upload started"
    )

    # ========================================================
    # 1. VALIDATE FILENAME
    # ========================================================

    if not file.filename:

        logger.warning(
            "Resume upload rejected: "
            "filename is missing"
        )

        raise ResumeUploadError(
            message="Filename is required.",
            status_code=400,
        )

    # ========================================================
    # 2. GET FILE EXTENSION
    # ========================================================

    file_extension = (
        Path(file.filename)
        .suffix
        .lower()
    )

    # ========================================================
    # 3. VALIDATE FILE TYPE
    # ========================================================

    if file_extension not in ALLOWED_EXTENSIONS:

        logger.warning(
            "Resume upload rejected: "
            "unsupported file type=%s",
            file_extension,
        )

        raise ResumeUploadError(
            message=(
                "Only PDF and DOCX "
                "resumes are supported."
            ),
            status_code=400,
        )

    # ========================================================
    # 4. GENERATE UNIQUE RESUME ID
    # ========================================================

    resume_id = (
        f"RES_{uuid4().hex[:12].upper()}"
    )

    logger.info(
        "Resume ID generated: resume_id=%s",
        resume_id,
    )

    # ========================================================
    # 5. CREATE STORAGE DIRECTORY
    # ========================================================

    try:

        RESUME_STORAGE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

    except Exception:

        logger.exception(
            "Failed to create resume storage "
            "directory"
        )

        raise ResumeUploadError(
            message=(
                "Failed to prepare resume storage."
            ),
            status_code=500,
        )

    # ========================================================
    # 6. CREATE SAFE STORED FILENAME
    # ========================================================

    stored_filename = (
        f"{resume_id}{file_extension}"
    )

    # ========================================================
    # 7. CREATE COMPLETE FILE PATH
    # ========================================================

    file_path = (
        RESUME_STORAGE_DIR
        / stored_filename
    )

    # ========================================================
    # 8. SAVE UPLOADED FILE
    # ========================================================

    try:

        with file_path.open(
            "wb"
        ) as buffer:

            while chunk := file.file.read(
                1024 * 1024
            ):
                buffer.write(chunk)

    except Exception:

        logger.exception(
            "Resume upload failed: "
            "resume_id=%s",
            resume_id,
        )

        # Remove partially written file if it exists.
        try:

            if file_path.exists():
                file_path.unlink()

        except Exception:

            logger.exception(
                "Failed to remove partially "
                "uploaded resume: resume_id=%s",
                resume_id,
            )

        raise ResumeUploadError(
            message="Failed to save resume.",
            status_code=500,
        )

    # ========================================================
    # 9. SUCCESS LOG
    # ========================================================

    logger.info(
        "Resume uploaded successfully: "
        "resume_id=%s file_type=%s",
        resume_id,
        file_extension,
    )

    # ========================================================
    # 10. RETURN RESUME INFORMATION
    # ========================================================

    return {
        "resume_id": resume_id,
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "file_path": str(file_path),
        "status": "UPLOADED",
    }