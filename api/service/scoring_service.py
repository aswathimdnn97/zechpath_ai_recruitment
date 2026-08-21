from pathlib import Path
import json
from typing import Any, Dict

from fastapi import HTTPException

from scoring.ats_scoring_engine import calculate_ats_score

from embeddings.embedding_generator import (
    EmbeddingGenerator,
)

from embeddings.embedding_text_builder import (
    profile_to_embedding_text,
    build_jd_embedding_text,
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

    Expected file:

        data/candidates/candidate_profile/
            CAN_123.json

    The candidate file may contain:

        {
            "candidate_id": "...",
            "masked_profile": {...},
            "bias_report": {...},
            "original_profile": {...}
        }
    """

    candidate_file = (
        CANDIDATE_STORAGE_DIR
        / f"{candidate_id}.json"
    )

    if not candidate_file.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Candidate "
                f"'{candidate_id}' not found."
            ),
        )

    try:

        with candidate_file.open(
            "r",
            encoding="utf-8",
        ) as file:

            candidate_data = json.load(file)

    except json.JSONDecodeError as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Candidate JSON file "
                "is invalid."
            ),
        ) from exc

    if not isinstance(
        candidate_data,
        dict,
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "Invalid candidate "
                "profile structure."
            ),
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

    Expected structure:

        {
            "candidate_id": "...",
            "masked_profile": {
                ...
            }
        }

    Backward compatibility is supported for files
    where the profile itself is stored directly.
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

    Expected structure:

        {
            "original_profile": {
                "personal_information": {
                    "name": "ANJALI MENON"
                }
            }
        }

    The candidate name is used only for API/output purposes.

    IMPORTANT:
    The candidate name is NEVER passed to the ATS
    scoring engine.
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

    Supports:

        {
            "resume_text": {
                ...
            }
        }

    and direct JD structures.
    """

    if not JD_FILE.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Job description file "
                "not found."
            ),
        )

    try:

        with JD_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            jd_data = json.load(file)

    except json.JSONDecodeError as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Job description JSON "
                "file is invalid."
            ),
        ) from exc

    if not isinstance(
        jd_data,
        dict,
    ):

        raise HTTPException(
            status_code=500,
            detail=(
                "Invalid job description "
                "structure."
            ),
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

    Ranking can read these files instead of
    recalculating ATS scores.
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
            )

    except OSError as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to save "
                "scoring result."
            ),
        ) from exc


# ============================================================
# SCORE CANDIDATE
# ============================================================

def score_candidate(
    candidate_id: str,
) -> dict:
    """
    Complete candidate scoring pipeline.

    Flow:

        candidate_id
              |
              v
        candidate_profile
              |
              +-------------------------+
              |                         |
              v                         v
        masked_profile            original_profile
              |                         |
              v                         v
        Resume embedding          candidate name
              |                         |
              +------------+------------+
                           |
                           v
                    Job description
                           |
                           v
                    JD embedding
                           |
                           v
                    ATS scoring
                           |
                           v
                    Attach identity
                           |
                           v
                  Save scoring result
                           |
                           v
                    API response

    IMPORTANT:

    - Only masked_profile is passed to ATS scoring.
    - Candidate name is extracted from original_profile.
    - Candidate name is NEVER passed to calculate_ats_score().
    """

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

        raise HTTPException(
            status_code=500,
            detail=(
                "Candidate masked profile "
                "data not found."
            ),
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

            raise ValueError(
                "Candidate profile produced "
                "empty embedding text."
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

            raise ValueError(
                "Job description produced "
                "empty embedding text."
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

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to calculate "
                "candidate score."
            ),
        ) from exc

    # ========================================================
    # 6. ATTACH NON-SCORING IDENTITY
    # ========================================================

    # Candidate ID is safe to preserve.
    score_result["candidate_id"] = (
        candidate_id
    )

    # Candidate name is attached only AFTER scoring.
    # It was NOT used by ATS scoring.
    score_result["candidate_name"] = (
        candidate_name
    )

    # ========================================================
    # 7. SAVE SCORING RESULT
    # ========================================================

    save_scoring_result(
        candidate_id=candidate_id,
        score_result=score_result,
    )

    # ========================================================
    # 8. RETURN API RESPONSE
    # ========================================================

    return {
        "candidate_id": candidate_id,
        "status": "SCORED",
        "score": score_result,
    }