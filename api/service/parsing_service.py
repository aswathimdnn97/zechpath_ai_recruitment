from pathlib import Path
import json
import logging

from document_processing.resume.resume_pipeline import (
    resume_pipeline,
)

from api.utils.exception import (
    ResumeParsingError,
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

CANDIDATE_STORAGE_DIR = (
    BASE_DIR
    / "data"
    / "candidates"
    / "candidate_profile"
)


# ============================================================
# PARSE RESUME BY ID
# ============================================================

def parse_resume_by_id(
    resume_id: str,
) -> dict:
    """
    Find a saved resume, parse it using the existing
    resume pipeline, save the parsed candidate data,
    and return the candidate ID.

    Expected resume parsing failures are raised as
    ResumeParsingError and handled centrally by FastAPI.
    """

    logger.info(
        "Resume parsing started: resume_id=%s",
        resume_id,
    )

    # ========================================================
    # 1. FIND THE SAVED RESUME
    # ========================================================

    matching_files = list(
        RESUME_STORAGE_DIR.glob(
            f"{resume_id}.*"
        )
    )

    if not matching_files:

        logger.warning(
            "Resume not found: resume_id=%s",
            resume_id,
        )

        raise ResumeParsingError(
            message=(
                f"Resume '{resume_id}' not found."
            ),
            status_code=404,
        )

    resume_path = matching_files[0]

    logger.info(
        "Resume found: resume_id=%s path=%s",
        resume_id,
        resume_path,
    )

    # ========================================================
    # 2. PARSE THE RESUME
    # ========================================================

    logger.info(
        "Resume pipeline started: resume_id=%s",
        resume_id,
    )

    try:

        parsed_data = resume_pipeline(
            str(resume_path)
        )

    except ResumeParsingError:
        # Preserve an already classified parsing error.
        raise

    except Exception:

        logger.exception(
            "Resume parsing pipeline failed: "
            "resume_id=%s",
            resume_id,
        )

        raise ResumeParsingError(
            message="Failed to parse resume.",
        )

    logger.info(
        "Resume pipeline completed: resume_id=%s",
        resume_id,
    )

    # ========================================================
    # 3. VALIDATE PARSED DATA
    # ========================================================

    if not isinstance(
        parsed_data,
        dict,
    ):
        logger.error(
            "Resume pipeline returned invalid data: "
            "resume_id=%s",
            resume_id,
        )

        raise ResumeParsingError(
            message=(
                "Resume parser returned invalid data."
            ),
        )

    candidate_id = parsed_data.get(
        "candidate_id"
    )

    if not candidate_id:

        logger.error(
            "Candidate ID missing from parsed data: "
            "resume_id=%s",
            resume_id,
        )

        raise ResumeParsingError(
            message=(
                "Failed to generate candidate ID "
                "from resume."
            ),
        )

    logger.info(
        "Candidate profile generated: "
        "resume_id=%s candidate_id=%s",
        resume_id,
        candidate_id,
    )

    # ========================================================
    # 4. CREATE CANDIDATE STORAGE DIRECTORY
    # ========================================================

    try:

        CANDIDATE_STORAGE_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

    except Exception:

        logger.exception(
            "Failed to create candidate storage "
            "directory: candidate_id=%s",
            candidate_id,
        )

        raise ResumeParsingError(
            message=(
                "Failed to prepare candidate storage."
            ),
        )

    # ========================================================
    # 5. CREATE CANDIDATE FILE PATH
    # ========================================================

    candidate_file = (
        CANDIDATE_STORAGE_DIR
        / f"{candidate_id}.json"
    )

    # ========================================================
    # 6. SAVE PARSED CANDIDATE DATA
    # ========================================================

    try:

        with candidate_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                parsed_data,
                file,
                indent=4,
                ensure_ascii=False,
                default=str,
            )

    except Exception:

        logger.exception(
            "Failed to save parsed candidate data: "
            "resume_id=%s candidate_id=%s",
            resume_id,
            candidate_id,
        )

        raise ResumeParsingError(
            message=(
                "Failed to save parsed "
                "candidate data."
            ),
        )

    logger.info(
        "Parsed candidate data saved: "
        "candidate_id=%s",
        candidate_id,
    )

    # ========================================================
    # 7. RETURN RESULT
    # ========================================================

    logger.info(
        "Resume parsing completed successfully: "
        "resume_id=%s candidate_id=%s",
        resume_id,
        candidate_id,
    )

    return {
        "resume_id": resume_id,
        "candidate_id": candidate_id,
        "status": "PARSED",
        "candidate": parsed_data,
    }