from pathlib import Path
import json
import logging
from typing import Any, Dict


from scoring.ats_scoring_engine import (
    calculate_ats_score,
)


from embeddings.embedding_generator import (
    EmbeddingGenerator,
)


from embeddings.embedding_text_builder import (
    profile_to_embedding_text,
    build_jd_embedding_text,
)


from document_processing.job_description.job_description_pipeline import (
    job_description_pipeline,
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

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)


# ============================================================
# CANDIDATE PROFILE STORAGE
# ============================================================

CANDIDATE_STORAGE_DIR = (
    BASE_DIR
    / "data"
    / "candidates"
    / "candidate_profile"
)


# ============================================================
# SCORING RESULT STORAGE
#
# Structure:
#
# scoring_results/
#     JOB_120215F8D847/
#         CAN_001.json
#         CAN_002.json
#
# One job -> many candidates
# ============================================================

SCORING_RESULTS_DIR = (
    BASE_DIR
    / "data"
    / "candidates"
    / "scoring_results"
)


# ============================================================
# JOB DESCRIPTION STORAGE
# ============================================================

JD_STORAGE_DIR = (
    BASE_DIR
    / "data"
    / "job_descriptions"
)


# ============================================================
# PARSED JOB DESCRIPTION STORAGE
#
# Structure:
#
# extracted/
#     jd/
#         JOB_120215F8D847.json
#         JOB_ABC123456789.json
#
# One parsed JD instance per job_id.
# ============================================================

PARSED_JD_STORAGE_DIR = (
    BASE_DIR
    / "data"
    / "extracted"
    / "jd"
)


# ============================================================
# CREATE REQUIRED DIRECTORIES
# ============================================================

PARSED_JD_STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


SCORING_RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


JD_STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# EMBEDDING GENERATOR
# ============================================================

embedding_generator = (
    EmbeddingGenerator()
)


# ============================================================
# VALIDATE IDENTIFIER
# ============================================================

def validate_identifier(
    value: str,
    field_name: str,
) -> str:
    """
    Validate an identifier used for filesystem paths.

    Prevents directory traversal and ensures
    the identifier is a non-empty string.
    """

    if not isinstance(
        value,
        str,
    ):
        raise ScoringError(
            message=f"{field_name} must be a string.",
            status_code=422,
        )

    value = value.strip()

    if not value:
        raise ScoringError(
            message=f"{field_name} is required.",
            status_code=422,
        )

    # --------------------------------------------------------
    # Prevent directory traversal
    # --------------------------------------------------------

    safe_value = Path(
        value
    ).name

    if safe_value != value:
        logger.error(
            "Invalid %s path: %s",
            field_name,
            value,
        )

        raise ScoringError(
            message=f"Invalid {field_name}.",
            status_code=400,
        )

    return value


# ============================================================
# VALIDATE JOB ID
# ============================================================

def validate_job_id(
    job_id: str,
) -> str:
    """
    Validate the existing job_id.

    IMPORTANT:
    This function does NOT generate a job_id.

    The job_id must already have been created
    when the job/requisition was created.
    """

    return validate_identifier(
        job_id,
        "job_id",
    )


# ============================================================
# LOAD CANDIDATE PROFILE
# ============================================================

def load_candidate(
    candidate_id: str,
) -> dict:
    """
    Load candidate profile from candidate_profile storage.
    """

    candidate_id = validate_identifier(
        candidate_id,
        "candidate_id",
    )

    logger.info(
        "Loading candidate profile: "
        "candidate_id=%s",
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

    if not candidate_file.is_file():

        raise ScoringError(
            message=(
                f"Candidate '{candidate_id}' "
                "is not a valid file."
            ),
            status_code=404,
        )

    try:

        with candidate_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            candidate_data = json.load(
                file
            )

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

    Only the masked profile is passed
    to the ATS scoring engine.
    """

    if not isinstance(
        candidate_data,
        dict,
    ):
        return {}

    masked_profile = (
        candidate_data.get(
            "masked_profile"
        )
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
    Extract candidate name from original profile.

    Candidate name is used only for output.

    It is never passed to ATS scoring.
    """

    if not isinstance(
        candidate_data,
        dict,
    ):
        return ""

    original_profile = (
        candidate_data.get(
            "original_profile"
        )
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
# RESOLVE JD FILE
# ============================================================

def resolve_jd_file(
    jd_id: str,
) -> Path:
    """
    Resolve a JD ID or JD filename to a PDF.

    Supported:

        JD_001_Python_Developer

    OR

        JD_001_Python_Developer.pdf

    Example:

        jd_id = "JD_001_Python_Developer"

        resolves to:

        data/job_descriptions/
        JD_001_Python_Developer.pdf
    """

    jd_id = validate_identifier(
        jd_id,
        "jd_id",
    )

    # --------------------------------------------------------
    # Remove any supplied path information
    # --------------------------------------------------------

    jd_name = Path(
        jd_id
    ).name

    # --------------------------------------------------------
    # Only PDF files are supported
    # --------------------------------------------------------

    if not jd_name.lower().endswith(
        ".pdf"
    ):

        jd_name = (
            jd_name
            + ".pdf"
        )

    jd_file = (
        JD_STORAGE_DIR
        / jd_name
    )

    # --------------------------------------------------------
    # Make sure resolved path stays inside
    # JD storage directory
    # --------------------------------------------------------

    try:

        jd_file.resolve().relative_to(
            JD_STORAGE_DIR.resolve()
        )

    except ValueError:

        logger.error(
            "Invalid JD file path: jd_id=%s",
            jd_id,
        )

        raise ScoringError(
            message=(
                "Invalid JD file path."
            ),
            status_code=400,
        )

    # --------------------------------------------------------
    # Check file existence
    # --------------------------------------------------------

    if not jd_file.exists():

        logger.warning(
            "JD file not found: %s",
            jd_file,
        )

        raise ScoringError(
            message=(
                f"Job description "
                f"'{jd_id}' not found."
            ),
            status_code=404,
        )

    if not jd_file.is_file():

        raise ScoringError(
            message=(
                f"JD '{jd_id}' is not a valid file."
            ),
            status_code=404,
        )

    return jd_file


# ============================================================
# LOAD + PARSE JOB DESCRIPTION
# ============================================================

def load_job_description(
    jd_id: str,
    job_id: str,
) -> dict:
    """
    Load and parse the JD associated with a job.

    Important relationship:

        job_id
            |
            +---- jd_id
            |
            +---- jd_file

    The job_id is supplied by the caller.
    This function does NOT generate a new job_id.
    """

    jd_id = validate_identifier(
        jd_id,
        "jd_id",
    )

    job_id = validate_job_id(
        job_id,
    )

    # --------------------------------------------------------
    # Resolve JD file
    # --------------------------------------------------------

    jd_file = resolve_jd_file(
        jd_id
    )

    logger.info(
        "Parsing job description: "
        "jd_id=%s job_id=%s file=%s",
        jd_id,
        job_id,
        jd_file.name,
    )

    try:

        # ----------------------------------------------------
        # Parse JD
        # ----------------------------------------------------

        jd_data = job_description_pipeline(
            str(jd_file),
            job_id=job_id,
        )

        if not isinstance(
            jd_data,
            dict,
        ):

            logger.error(
                "Invalid JD structure: "
                "jd_id=%s job_id=%s",
                jd_id,
                job_id,
            )

            raise ScoringError(
                message=(
                    "Job description parser "
                    "returned invalid data."
                ),
                status_code=500,
            )

        # ----------------------------------------------------
        # Add identifiers to parsed JD
        # ----------------------------------------------------

        jd_data["jd_id"] = (
            Path(jd_id).stem
        )

        jd_data["job_id"] = (
            job_id
        )

        jd_data["jd_file"] = (
            jd_file.name
        )

        # ----------------------------------------------------
        # Save parsed JD by JOB ID
        #
        # IMPORTANT:
        #
        # Do NOT save only as:
        #
        # SeniorPythonDeveloper.json
        #
        # because multiple job postings may use
        # the same JD.
        #
        # Instead:
        #
        # JOB_120215F8D847.json
        # ----------------------------------------------------

        parsed_jd_file = (
            PARSED_JD_STORAGE_DIR
            / f"{job_id}.json"
        )

        with parsed_jd_file.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                jd_data,
                file,
                indent=4,
                ensure_ascii=False,
            )

        logger.info(
            "Parsed JD saved successfully: "
            "jd_id=%s job_id=%s path=%s",
            jd_id,
            job_id,
            parsed_jd_file,
        )

        return jd_data

    except ScoringError:

        raise

    except Exception as exc:

        logger.exception(
            "Job description parsing failed: "
            "jd_id=%s job_id=%s",
            jd_id,
            job_id,
        )

        raise ScoringError(
            message=(
                f"Failed to parse job description: {exc}"
            ),
            status_code=500,
        )


# ============================================================
# BUILD SCORING RESULT FILE PATH
# ============================================================

def get_scoring_result_file(
    candidate_id: str,
    job_id: str,
) -> Path:
    """
    Build the scoring result path using:

        job_id + candidate_id

    Structure:

        scoring_results/
            JOB_120215F8D847/
                CAN_001.json
                CAN_002.json

    This represents:

        ONE JOB
            |
            +---- Candidate 1
            +---- Candidate 2
            +---- Candidate 3
    """

    candidate_id = validate_identifier(
        candidate_id,
        "candidate_id",
    )

    job_id = validate_job_id(
        job_id,
    )

    job_result_dir = (
        SCORING_RESULTS_DIR
        / job_id
    )

    return (
        job_result_dir
        / f"{candidate_id}.json"
    )


# ============================================================
# SAVE SCORING RESULT
# ============================================================

def save_scoring_result(
    candidate_id: str,
    job_id: str,
    score_result: dict,
) -> None:
    """
    Persist ATS scoring result.

    Result is stored using:

        job_id + candidate_id

    Example:

        scoring_results/
            JOB_120215F8D847/
                CAN_001.json
                CAN_002.json

    This prevents scores for different jobs
    from overwriting each other.
    """

    scoring_file = (
        get_scoring_result_file(
            candidate_id,
            job_id,
        )
    )

    job_result_dir = (
        scoring_file.parent
    )

    job_result_dir.mkdir(
        parents=True,
        exist_ok=True,
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
            "candidate_id=%s job_id=%s",
            candidate_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Failed to save scoring result."
            ),
            status_code=500,
        )

    logger.info(
        "Scoring result saved: "
        "candidate_id=%s job_id=%s path=%s",
        candidate_id,
        job_id,
        scoring_file,
    )


# ============================================================
# LOAD SCORING RESULT
# ============================================================

def load_scoring_result(
    candidate_id: str,
    job_id: str,
) -> dict:
    """
    Load an already-completed scoring result.

    This function is used by the scoring-result API.

    It does NOT create a new scoring job.

    Result is identified by:

        job_id + candidate_id
    """

    scoring_file = (
        get_scoring_result_file(
            candidate_id,
            job_id,
        )
    )

    logger.info(
        "Loading scoring result: "
        "candidate_id=%s job_id=%s",
        candidate_id,
        job_id,
    )

    if not scoring_file.exists():

        logger.warning(
            "Scoring result not found: "
            "candidate_id=%s job_id=%s",
            candidate_id,
            job_id,
        )

        raise ScoringError(
            message=(
                f"No scoring result found for "
                f"candidate '{candidate_id}' "
                f"and job '{job_id}'."
            ),
            status_code=404,
        )

    if not scoring_file.is_file():

        raise ScoringError(
            message=(
                "Scoring result path is not a file."
            ),
            status_code=500,
        )

    try:

        with scoring_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            score_result = json.load(
                file
            )

    except json.JSONDecodeError:

        logger.exception(
            "Invalid scoring result JSON: "
            "candidate_id=%s job_id=%s",
            candidate_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Scoring result file is invalid."
            ),
            status_code=500,
        )

    except OSError:

        logger.exception(
            "Failed to read scoring result: "
            "candidate_id=%s job_id=%s",
            candidate_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Failed to load scoring result."
            ),
            status_code=500,
        )

    # ========================================================
    # Validate saved result
    # ========================================================

    if not isinstance(
        score_result,
        dict,
    ):

        logger.error(
            "Invalid scoring result structure: "
            "candidate_id=%s job_id=%s",
            candidate_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Invalid scoring result structure."
            ),
            status_code=500,
        )

    # ========================================================
    # Validate candidate ID
    # ========================================================

    saved_candidate_id = (
        score_result.get(
            "candidate_id"
        )
    )

    if (
        saved_candidate_id is not None
        and saved_candidate_id != candidate_id
    ):

        logger.error(
            "Candidate ID mismatch in scoring result: "
            "requested=%s saved=%s",
            candidate_id,
            saved_candidate_id,
        )

        raise ScoringError(
            message=(
                "Scoring result candidate_id does not match."
            ),
            status_code=500,
        )

    # ========================================================
    # Validate job ID
    # ========================================================

    saved_job_id = (
        score_result.get(
            "job_id"
        )
    )

    if (
        saved_job_id is not None
        and saved_job_id != job_id
    ):

        logger.error(
            "Job ID mismatch in scoring result: "
            "requested=%s saved=%s",
            job_id,
            saved_job_id,
        )

        raise ScoringError(
            message=(
                "Scoring result job_id does not match."
            ),
            status_code=500,
        )

    # ========================================================
    # Validate candidate_score
    # ========================================================

    candidate_score = (
        score_result.get(
            "candidate_score"
        )
    )

    if not isinstance(
        candidate_score,
        dict,
    ):

        logger.error(
            "candidate_score missing or invalid: "
            "candidate_id=%s job_id=%s",
            candidate_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Invalid scoring result: "
                "candidate_score missing."
            ),
            status_code=500,
        )

    # ========================================================
    # Validate final_score
    # ========================================================

    final_score = (
        candidate_score.get(
            "final_score"
        )
    )

    if not isinstance(
        final_score,
        (int, float),
    ):

        logger.error(
            "final_score missing or invalid: "
            "candidate_id=%s job_id=%s",
            candidate_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Invalid scoring result: "
                "final_score missing or invalid."
            ),
            status_code=500,
        )

    logger.info(
        "Scoring result loaded successfully: "
        "candidate_id=%s job_id=%s final_score=%s",
        candidate_id,
        job_id,
        final_score,
    )

    return score_result


# ============================================================
# SCORE CANDIDATE
# ============================================================

def score_candidate(
    candidate_id: str,
    jd_id: str,
    job_id: str,
) -> dict:
    """
    Complete candidate scoring pipeline.

    Important relationship:

        job_id
            |
            +---- jd_id
            |
            +---- candidate_id
            |
            +---- score

    The job_id MUST already exist before this
    function is called.

    This function does NOT generate a new job_id.

    Only the masked candidate profile is passed
    to the ATS scoring engine.
    """

    # ========================================================
    # VALIDATE INPUTS
    # ========================================================

    candidate_id = validate_identifier(
        candidate_id,
        "candidate_id",
    )

    jd_id = validate_identifier(
        jd_id,
        "jd_id",
    )

    job_id = validate_job_id(
        job_id,
    )

    logger.info(
        "Candidate scoring started: "
        "candidate_id=%s jd_id=%s job_id=%s",
        candidate_id,
        jd_id,
        job_id,
    )

    # ========================================================
    # 1. LOAD CANDIDATE
    # ========================================================

    candidate_data = (
        load_candidate(
            candidate_id
        )
    )

    # ========================================================
    # 2. EXTRACT MASKED PROFILE
    # ========================================================

    candidate = (
        get_masked_profile(
            candidate_data
        )
    )

    if not candidate:

        logger.error(
            "Masked candidate profile not found: "
            "candidate_id=%s job_id=%s",
            candidate_id,
            job_id,
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

    candidate_name = (
        get_candidate_name(
            candidate_data
        )
    )

    # ========================================================
    # 4. LOAD + PARSE SELECTED JD
    # ========================================================

    job_description = (
        load_job_description(
            jd_id=jd_id,
            job_id=job_id,
        )
    )

    # ========================================================
    # 5. VALIDATE MASKING
    # ========================================================

    if "personal_information" in candidate:

        logger.error(
            "Masked profile contains "
            "personal_information: "
            "candidate_id=%s job_id=%s",
            candidate_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Masked candidate profile contains "
                "personal information."
            ),
            status_code=422,
        )

    # ========================================================
    # 6. GENERATE EMBEDDINGS + SCORE
    # ========================================================

    logger.info(
        "Generating embeddings and calculating ATS score: "
        "candidate_id=%s jd_id=%s job_id=%s",
        candidate_id,
        jd_id,
        job_id,
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
                "candidate_id=%s job_id=%s",
                candidate_id,
                job_id,
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
                "candidate_id=%s jd_id=%s job_id=%s",
                candidate_id,
                jd_id,
                job_id,
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

        score_result = (
            calculate_ats_score(
                candidate_profile=candidate,
                jd_profile=job_description,
                resume_embedding=resume_embedding,
                jd_embedding=jd_embedding,
                embedding_generator=embedding_generator,
            )
        )

    except ScoringError:

        raise

    except Exception:

        logger.exception(
            "Candidate scoring engine failed: "
            "candidate_id=%s jd_id=%s job_id=%s",
            candidate_id,
            jd_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Failed to calculate candidate score."
            ),
            status_code=500,
        )

    # ========================================================
    # 7. VALIDATE SCORE RESULT
    # ========================================================

    if not isinstance(
        score_result,
        dict,
    ):

        logger.error(
            "Invalid scoring result returned: "
            "candidate_id=%s jd_id=%s job_id=%s",
            candidate_id,
            jd_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Scoring engine returned "
                "an invalid result."
            ),
            status_code=500,
        )

    # --------------------------------------------------------
    # Validate candidate_score
    # --------------------------------------------------------

    candidate_score = (
        score_result.get(
            "candidate_score"
        )
    )

    if not isinstance(
        candidate_score,
        dict,
    ):

        logger.error(
            "candidate_score missing or invalid: "
            "candidate_id=%s jd_id=%s job_id=%s",
            candidate_id,
            jd_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Invalid scoring result: "
                "candidate_score missing."
            ),
            status_code=500,
        )

    # --------------------------------------------------------
    # Validate final_score
    # --------------------------------------------------------

    final_score = (
        candidate_score.get(
            "final_score"
        )
    )

    if not isinstance(
        final_score,
        (int, float),
    ):

        logger.error(
            "final_score missing or invalid: "
            "candidate_id=%s jd_id=%s job_id=%s",
            candidate_id,
            jd_id,
            job_id,
        )

        raise ScoringError(
            message=(
                "Invalid scoring result: "
                "final_score missing or invalid."
            ),
            status_code=500,
        )

    # --------------------------------------------------------
    # Validate final score range
    # --------------------------------------------------------

    if not 0 <= final_score <= 100:

        logger.error(
            "final_score outside valid range: "
            "candidate_id=%s jd_id=%s job_id=%s final_score=%s",
            candidate_id,
            jd_id,
            job_id,
            final_score,
        )

        raise ScoringError(
            message=(
                "Invalid scoring result: "
                "final_score must be between 0 and 100."
            ),
            status_code=500,
        )

    # ========================================================
    # 8. ATTACH NON-SCORING METADATA
    # ========================================================

    score_result["candidate_id"] = (
        candidate_id
    )

    score_result["candidate_name"] = (
        candidate_name
    )

    score_result["jd_id"] = (
        Path(jd_id).stem
    )

    score_result["job_id"] = (
        job_id
    )

    score_result["jd_file"] = (
        resolve_jd_file(
            jd_id
        ).name
    )

    # ========================================================
    # 9. SAVE RESULT
    # ========================================================

    save_scoring_result(
        candidate_id=candidate_id,
        job_id=job_id,
        score_result=score_result,
    )

    # ========================================================
    # 10. LOG COMPLETION
    # ========================================================

    logger.info(
        "Candidate scoring completed successfully: "
        "candidate_id=%s jd_id=%s job_id=%s final_score=%s",
        candidate_id,
        jd_id,
        job_id,
        final_score,
    )

    # ========================================================
    # 11. RETURN SCORING RESULT
    # ========================================================

    return {
        "candidate_id": candidate_id,
        "jd_id": Path(jd_id).stem,
        "job_id": job_id,
        "status": "SCORED",
        "score": score_result,
    }