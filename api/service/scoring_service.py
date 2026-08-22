from pathlib import Path
import json
import logging
from typing import Any, Dict

from scoring.ats_scoring_engine import calculate_ats_score

from embeddings.embedding_generator import (
    EmbeddingGenerator,
)

from embeddings.embedding_text_builder import (
    profile_to_embedding_text,
    build_jd_embedding_text,
)

from api.utils.exception import (
    ScoringError,
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

CANDIDATE_STORAGE_DIR = (
    BASE_DIR
    / "data"
    / "candidates"
    / "candidate_profile"
)

SCORING_RESULTS_DIR = (
    BASE_DIR
    / "data"
    / "candidates"
    / "scoring_results"
)

JD_FILE = (
    BASE_DIR
    / "data"
    / "extracted"
    / "jd_python_developer.json"
)


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

SCORING_RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# EMBEDDING GENERATOR
# ============================================================

embedding_generator = EmbeddingGenerator()


# ============================================================
# LOAD CANDIDATE PROFILE
# ============================================================

def load_candidate(
    candidate_id: str,
) -> dict:
    """
    Load candidate profile from candidate_profile storage.

    Scoring-related errors are raised as ScoringError and
    handled centrally by FastAPI.
    """

    logger.info(
        "Loading candidate profile: candidate_id=%s",
        candidate_id,
    )

    candidate_file = (
        CANDIDATE_STORAGE_DIR
        / f"{candidate_id}.json"
    )

    if not candidate_file.exists():

        logger.warning(
            "Candidate profile not found: "
            "candidate_id=%s",
            candidate_id,
        )

        raise ScoringError(
            message=(
                f"Candidate '{candidate_id}' not found."
            ),
            status_code=404,
        )

    try:

        with candidate_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            candidate_data = json.load(file)

    except json.JSONDecodeError:

        logger.exception(
            "Invalid candidate JSON: "
            "candidate_id=%s",
            candidate_id,
        )

        raise ScoringError(
            message=(
                "Candidate JSON file is invalid."
            ),
            status_code=500,
        )

    except OSError:

        logger.exception(
            "Failed to read candidate profile: "
            "candidate_id=%s",
            candidate_id,
        )

        raise ScoringError(
            message=(
                "Failed to load candidate profile."
            ),
            status_code=500,
        )

    if not isinstance(
        candidate_data,
        dict,
    ):

        logger.error(
            "Invalid candidate profile structure: "
            "candidate_id=%s",
            candidate_id,
        )

        raise ScoringError(
            message=(
                "Invalid candidate profile structure."
            ),
            status_code=500,
        )

    logger.info(
        "Candidate profile loaded successfully: "
        "candidate_id=%s",
        candidate_id,
    )

    return candidate_data


# ============================================================
# EXTRACT MASKED PROFILE
# ============================================================

def get_masked_profile(
    candidate_data: Dict[str, Any],
) -> dict:
    """
    Extract the masked candidate profile.
    """

    if not isinstance(
        candidate_data,
        dict,
    ):
        return {}

    masked_profile = candidate_data.get(
        "masked_profile"
    )

    if isinstance(
        masked_profile,
        dict,
    ):
        return masked_profile

    # --------------------------------------------------------
    # Backward compatibility
    # --------------------------------------------------------

    return candidate_data


# ============================================================
# EXTRACT CANDIDATE NAME
# ============================================================

def get_candidate_name(
    candidate_data: Dict[str, Any],
) -> str:
    """
    Extract candidate name from the original profile.

    Candidate name is used only for API/output purposes
    and is never passed to the ATS scoring engine.
    """

    if not isinstance(
        candidate_data,
        dict,
    ):
        return ""

    original_profile = candidate_data.get(
        "original_profile"
    )

    if not isinstance(
        original_profile,
        dict,
    ):
        return ""

    personal_information = (
        original_profile.get(
            "personal_information"
        )
    )

    if not isinstance(
        personal_information,
        dict,
    ):
        return ""

    candidate_name = (
        personal_information.get(
            "name"
        )
    )

    if not isinstance(
        candidate_name,
        str,
    ):
        return ""

    return candidate_name.strip()


# ============================================================
# LOAD JOB DESCRIPTION
# ============================================================

def load_job_description() -> dict:
    """
    Load the extracted job description.
    """

    logger.info(
        "Loading job description"
    )

    if not JD_FILE.exists():

        logger.warning(
            "Job description file not found: %s",
            JD_FILE,
        )

        raise ScoringError(
            message=(
                "Job description file not found."
            ),
            status_code=404,
        )

    try:

        with JD_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            jd_data = json.load(file)

    except json.JSONDecodeError:

        logger.exception(
            "Invalid job description JSON"
        )

        raise ScoringError(
            message=(
                "Job description JSON file is invalid."
            ),
            status_code=500,
        )

    except OSError:

        logger.exception(
            "Failed to read job description"
        )

        raise ScoringError(
            message=(
                "Failed to load job description."
            ),
            status_code=500,
        )

    if not isinstance(
        jd_data,
        dict,
    ):

        logger.error(
            "Invalid job description structure"
        )

        raise ScoringError(
            message=(
                "Invalid job description structure."
            ),
            status_code=500,
        )

    resume_text = jd_data.get(
        "resume_text"
    )

    if isinstance(
        resume_text,
        dict,
    ):
        return resume_text

    return jd_data


# ============================================================
# SAVE SCORING RESULT
# ============================================================

def save_scoring_result(
    candidate_id: str,
    score_result: dict,
) -> None:
    """
    Persist the ATS scoring result.
    """

    scoring_file = (
        SCORING_RESULTS_DIR
        / f"{candidate_id}.json"
    )

    try:

        with scoring_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                score_result,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

    except OSError:

        logger.exception(
            "Failed to save scoring result: "
            "candidate_id=%s",
            candidate_id,
        )

        raise ScoringError(
            message=(
                "Failed to save scoring result."
            ),
            status_code=500,
        )

    logger.info(
        "Scoring result saved: candidate_id=%s",
        candidate_id,
    )


# ============================================================
# SCORE CANDIDATE
# ============================================================

def score_candidate(
    candidate_id: str,
) -> dict:
    """
    Complete candidate scoring pipeline.

    Only the masked candidate profile is passed
    to the ATS scoring engine.
    """

    logger.info(
        "Candidate scoring started: "
        "candidate_id=%s",
        candidate_id,
    )

    # ========================================================
    # 1. LOAD CANDIDATE PROFILE
    # ========================================================

    candidate_data = load_candidate(
        candidate_id
    )

    # ========================================================
    # 2. EXTRACT MASKED PROFILE
    # ========================================================

    candidate = get_masked_profile(
        candidate_data
    )

    if not candidate:

        logger.error(
            "Masked candidate profile not found: "
            "candidate_id=%s",
            candidate_id,
        )

        raise ScoringError(
            message=(
                "Candidate masked profile "
                "data not found."
            ),
            status_code=422,
        )

    # ========================================================
    # 3. EXTRACT CANDIDATE NAME
    # ========================================================

    candidate_name = get_candidate_name(
        candidate_data
    )

    # ========================================================
    # 4. LOAD JOB DESCRIPTION
    # ========================================================

    job_description = (
        load_job_description()
    )

    # ========================================================
    # 5. GENERATE EMBEDDINGS + SCORE
    # ========================================================

    logger.info(
        "Generating embeddings and calculating ATS score: "
        "candidate_id=%s",
        candidate_id,
    )

    try:

        # ----------------------------------------------------
        # Resume embedding text
        # ----------------------------------------------------

        resume_embedding_text = (
            profile_to_embedding_text(
                candidate
            )
        )

        if not resume_embedding_text:

            logger.error(
                "Empty resume embedding text: "
                "candidate_id=%s",
                candidate_id,
            )

            raise ScoringError(
                message=(
                    "Candidate profile produced "
                    "empty embedding text."
                ),
                status_code=422,
            )

        # ----------------------------------------------------
        # Resume embedding
        # ----------------------------------------------------

        resume_embedding = (
            embedding_generator.generate_embedding(
                resume_embedding_text
            )
        )

        # ----------------------------------------------------
        # JD embedding text
        # ----------------------------------------------------

        jd_embedding_text = (
            build_jd_embedding_text(
                job_description
            )
        )

        if not jd_embedding_text:

            logger.error(
                "Empty JD embedding text: "
                "candidate_id=%s",
                candidate_id,
            )

            raise ScoringError(
                message=(
                    "Job description produced "
                    "empty embedding text."
                ),
                status_code=422,
            )

        # ----------------------------------------------------
        # JD embedding
        # ----------------------------------------------------

        jd_embedding = (
            embedding_generator.generate_embedding(
                jd_embedding_text
            )
        )

        # ----------------------------------------------------
        # ATS SCORE
        # ----------------------------------------------------

        score_result = calculate_ats_score(
            candidate_profile=candidate,
            jd_profile=job_description,
            resume_embedding=resume_embedding,
            jd_embedding=jd_embedding,
            embedding_generator=embedding_generator,
        )

    except ScoringError:
        # Preserve expected scoring errors.
        raise

    except Exception:

        logger.exception(
            "Candidate scoring engine failed: "
            "candidate_id=%s",
            candidate_id,
        )

        raise ScoringError(
            message=(
                "Failed to calculate candidate score."
            ),
            status_code=500,
        )

    # ========================================================
    # 6. VALIDATE SCORE RESULT
    # ========================================================

    if not isinstance(
        score_result,
        dict,
    ):

        logger.error(
            "Invalid scoring result returned: "
            "candidate_id=%s",
            candidate_id,
        )

        raise ScoringError(
            message=(
                "Scoring engine returned an invalid result."
            ),
            status_code=500,
        )

    # ========================================================
    # 7. ATTACH NON-SCORING IDENTITY
    # ========================================================

    score_result["candidate_id"] = (
        candidate_id
    )

    # Candidate name is attached only AFTER scoring.
    score_result["candidate_name"] = (
        candidate_name
    )

    # ========================================================
    # 8. SAVE SCORING RESULT
    # ========================================================

    save_scoring_result(
        candidate_id=candidate_id,
        score_result=score_result,
    )

    # ========================================================
    # 9. LOG SCORE COMPLETION
    # ========================================================

    final_score = (
        score_result
        .get("candidate_score", {})
        .get("final_score")
    )

    logger.info(
        "Candidate scoring completed successfully: "
        "candidate_id=%s final_score=%s",
        candidate_id,
        final_score,
    )

    # ========================================================
    # 10. RETURN API RESPONSE
    # ========================================================

    return {
        "candidate_id": candidate_id,
        "status": "SCORED",
        "score": score_result,
    }