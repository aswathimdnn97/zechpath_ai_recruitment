from pathlib import Path
import json
import logging
from document_processing.resume.resume_pipeline import (
    resume_pipeline,
)

from api.utils.exception import (
    ResumeParsingError,
)

from api.service.candidate_deduplication_service import (
    calculate_resume_hash,
    find_duplicate_by_hash,
    find_duplicate_by_identity,
)

logger = logging.getLogger(__name__)


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
    Find a saved resume, calculate its hash, detect exact or
    identity-based duplicates, and parse/save only when the
    resume belongs to a new candidate.

    Duplicate detection order:

        1. Exact file hash
        2. Parsed identity fields
           (email / phone / LinkedIn)

    A modified resume can therefore reuse the existing
    candidate_id instead of creating a duplicate candidate.
    """

    logger.info(
        "Resume parsing started: resume_id=%s",
        resume_id,
    )

    # ========================================================
    # 1. FIND SAVED RESUME
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
            message=f"Resume '{resume_id}' not found.",
            status_code=404,
        )

    resume_path = matching_files[0]

    logger.info(
        "Resume found: resume_id=%s path=%s",
        resume_id,
        resume_path,
    )

    # ========================================================
    # 2. CALCULATE EXACT FILE HASH
    # ========================================================

    try:
        resume_hash = calculate_resume_hash(
            resume_path
        )

    except Exception:
        logger.exception(
            "Failed to calculate resume hash: "
            "resume_id=%s",
            resume_id,
        )

        raise ResumeParsingError(
            message="Failed to identify resume.",
        )

    logger.info(
        "Resume hash generated: resume_id=%s hash=%s",
        resume_id,
        resume_hash[:12],
    )

    # ========================================================
    # 3. EXACT DUPLICATE CHECK
    # ========================================================

    try:
        duplicate = find_duplicate_by_hash(
            resume_hash
        )

    except Exception:
        logger.exception(
            "Exact duplicate check failed: "
            "resume_id=%s",
            resume_id,
        )

        raise ResumeParsingError(
            message="Failed to check for duplicate resume.",
        )

    if duplicate:
        candidate_id = duplicate["candidate_id"]

        logger.info(
            "Exact duplicate detected: resume_id=%s "
            "candidate_id=%s",
            resume_id,
            candidate_id,
        )

        return {
            "resume_id": resume_id,
            "candidate_id": candidate_id,
            "status": "DUPLICATE",
            "duplicate_type": "EXACT_HASH",
            "message": (
                "This resume has already been processed."
            ),
        }

    # ========================================================
    # 4. PARSE RESUME
    # ========================================================
    #
    # Identity-based duplicate detection must happen after
    # parsing because email/phone/LinkedIn are extracted by
    # the resume pipeline.
    # ========================================================

    logger.info(
        "Resume pipeline started: resume_id=%s",
        resume_id,
    )

    try:
        parsed_data = resume_pipeline(
            str(resume_path)
        )

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

        # ====================================================
        # 5. MODIFIED-RESUME / IDENTITY DUPLICATE CHECK
        # ====================================================

        duplicate = find_duplicate_by_identity(
            parsed_data
        )

        if duplicate:
            candidate_id = duplicate["candidate_id"]

            logger.info(
                "Modified resume duplicate detected: "
                "resume_id=%s candidate_id=%s "
                "matched_fields=%s",
                resume_id,
                candidate_id,
                duplicate.get("matched_fields", []),
            )

            return {
                "resume_id": resume_id,
                "candidate_id": candidate_id,
                "status": "DUPLICATE",
                "duplicate_type": "IDENTITY",
                "matched_fields": duplicate.get(
                    "matched_fields",
                    [],
                ),
                "message": (
                    "A candidate with the same identity "
                    "already exists."
                ),
            }

    except ResumeParsingError:
        raise

    except Exception:
        logger.exception(
            "Resume parsing pipeline or identity "
            "duplicate check failed: resume_id=%s",
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
    # 6. VALIDATE CANDIDATE ID
    # ========================================================

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

    # ========================================================
    # 7. STORE RESUME HASH
    # ========================================================

    parsed_data["resume_hash"] = resume_hash

    logger.info(
        "Candidate profile generated: "
        "resume_id=%s candidate_id=%s",
        resume_id,
        candidate_id,
    )

    # ========================================================
    # 8. CREATE CANDIDATE STORAGE DIRECTORY
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
    # 9. CREATE CANDIDATE FILE PATH
    # ========================================================

    candidate_file = (
        CANDIDATE_STORAGE_DIR
        / f"{candidate_id}.json"
    )

    # ========================================================
    # 10. SAVE PARSED CANDIDATE DATA
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
        "Parsed candidate data saved: candidate_id=%s",
        candidate_id,
    )

    # ========================================================
    # 11. RETURN RESULT
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