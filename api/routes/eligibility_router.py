
import json
import math
import re
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException

from api.service.eligibility_service import evaluate_candidate_eligibility
from eligibility.eligibility_rule_generator import generate_eligibility_rules


router = APIRouter(prefix="/eligibility", tags=["Eligibility"])

BASE_DIR = Path(__file__).resolve().parents[2]

JD_DIR = BASE_DIR / "data" / "extracted" / "jd"

CANDIDATE_PROFILE_DIR = (
    BASE_DIR / "data" / "candidates" / "candidate_profile"
)

ELIGIBILITY_RULES_DIR = BASE_DIR / "data" / "eligibility_rules"

ELIGIBILITY_RESULTS_DIR = (
    BASE_DIR / "data" / "candidates" / "eligibility_results"
)

# Actual ATS score storage:
# data/candidates/scoring_results/{job_id}/{candidate_id}.json
ATS_SCORING_RESULTS_DIR = (
    BASE_DIR / "data" / "candidates" / "scoring_results"
)


def _validate_identifier(value: str, name: str) -> None:
    """Reject identifiers containing unsafe path characters."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {name}.",
        )


def _load_json(
    file_path: Path,
    description: str,
) -> dict[str, Any]:
    """Load a JSON object and convert file errors into HTTP errors."""
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"{description} not found.",
        )

    try:
        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read {description}.",
        ) from exc

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=500,
            detail=f"{description} must contain a JSON object.",
        )

    return data


def _load_ats_score(
    job_id: str,
    candidate_id: str,
    jd_id: str,
) -> float | None:
    """
    Load and validate a candidate's ATS score for the requested job.

    Returns None if the score file does not exist.
    Raises HTTPException if the stored score is invalid or mismatched.
    """
    _validate_identifier(job_id, "job_id")
    _validate_identifier(candidate_id, "candidate_id")
    _validate_identifier(jd_id, "jd_id")

    score_path = (
        ATS_SCORING_RESULTS_DIR
        / job_id
        / f"{candidate_id}.json"
    )

    # A missing score is handled as a manual-review case by the caller.
    if not score_path.is_file():
        return None

    score_data = _load_json(
        score_path,
        "ATS scoring result",
    )

    if score_data.get("candidate_id") != candidate_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "The ATS scoring result does not match "
                "the requested candidate."
            ),
        )

    stored_job_id = score_data.get("job_id")

    if stored_job_id is not None and stored_job_id != job_id:
        raise HTTPException(
            status_code=409,
            detail="The ATS scoring result belongs to another job.",
        )

    stored_jd_id = score_data.get("jd_id")

    if stored_jd_id is not None and stored_jd_id != jd_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "The ATS scoring result belongs to another "
                "job description."
            ),
        )

    candidate_score = score_data.get("candidate_score")

    if not isinstance(candidate_score, dict):
        raise HTTPException(
            status_code=422,
            detail="ATS scoring result has an invalid candidate_score.",
        )

    ats_score = candidate_score.get("final_score")

    if (
        isinstance(ats_score, bool)
        or not isinstance(ats_score, Real)
        or not math.isfinite(ats_score)
        or not 0 <= ats_score <= 100
    ):
        raise HTTPException(
            status_code=422,
            detail="ATS final_score must be a valid number from 0 to 100.",
        )

    return float(ats_score)


def _save_json(
    file_path: Path,
    data: dict[str, Any],
    description: str = "JSON data",
) -> None:
    """Save JSON atomically to avoid leaving a partially written file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False,
            )
            file.write("\n")

        temporary_path.replace(file_path)

    except (OSError, TypeError, ValueError) as exc:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass

        raise HTTPException(
            status_code=500,
            detail=f"Could not save {description}.",
        ) from exc


@router.post(
    "/jobs/{job_id}/rules/generate",
    status_code=201,
)
def generate_job_eligibility_rules(
    job_id: str,
) -> dict[str, Any]:
    """Generate and persist eligibility rules from a parsed JD."""
    _validate_identifier(job_id, "job_id")

    jd_path = JD_DIR / f"{job_id}.json"

    parsed_jd = _load_json(
        jd_path,
        "Parsed job description",
    )

    stored_job_id = parsed_jd.get("job_id")

    if stored_job_id is not None and stored_job_id != job_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "The job ID in the parsed JD does not match "
                "the requested job."
            ),
        )

    try:
        generated_rules = generate_eligibility_rules(parsed_jd)

    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not generate eligibility rules: {exc}",
        ) from exc

    if not isinstance(generated_rules, dict):
        raise HTTPException(
            status_code=500,
            detail="Eligibility rule generator returned an invalid result.",
        )

    if generated_rules.get("generation_status") == "failed":
        raise HTTPException(
            status_code=422,
            detail="Eligibility rule generation failed.",
        )

    if (
        generated_rules.get("job_id") is not None
        and generated_rules["job_id"] != job_id
    ):
        raise HTTPException(
            status_code=409,
            detail="Generated eligibility rules belong to another job.",
        )

    rules_path = ELIGIBILITY_RULES_DIR / f"{job_id}.json"

    _save_json(
        rules_path,
        generated_rules,
        "eligibility rules",
    )

    return {
        "message": "Eligibility rules generated successfully.",
        "job_id": job_id,
        "rules": generated_rules,
    }


@router.get("/jobs/{job_id}/rules")
def get_job_eligibility_rules(
    job_id: str,
) -> dict[str, Any]:
    """Retrieve the saved eligibility rules for a job."""
    _validate_identifier(job_id, "job_id")

    rules_path = ELIGIBILITY_RULES_DIR / f"{job_id}.json"

    rules = _load_json(
        rules_path,
        "Eligibility rules",
    )

    if rules.get("job_id") != job_id:
        raise HTTPException(
            status_code=409,
            detail="The saved eligibility rules belong to another job.",
        )

    return rules


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/evaluate"
)
def evaluate_job_candidate(
    job_id: str,
    candidate_id: str,
) -> dict[str, Any]:
    """Evaluate eligibility and persist the candidate's result."""
    _validate_identifier(job_id, "job_id")
    _validate_identifier(candidate_id, "candidate_id")

    # 1. Load eligibility rules generated for this job.
    rules_path = ELIGIBILITY_RULES_DIR / f"{job_id}.json"

    generated_rules = _load_json(
        rules_path,
        "Eligibility rules",
    )

    if generated_rules.get("job_id") != job_id:
        raise HTTPException(
            status_code=409,
            detail="The eligibility rules belong to another job.",
        )

    # 2. Obtain and validate the job description ID.
    jd_id = generated_rules.get("jd_id")

    if not isinstance(jd_id, str) or not jd_id:
        raise HTTPException(
            status_code=422,
            detail="Eligibility rules do not contain a valid jd_id.",
        )

    _validate_identifier(jd_id, "jd_id")

    # 3. Load the candidate profile.
    profile_path = (
        CANDIDATE_PROFILE_DIR / f"{candidate_id}.json"
    )

    candidate_profile = _load_json(
        profile_path,
        "Candidate profile",
    )

    if candidate_profile.get("candidate_id") != candidate_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "The candidate ID in the profile does not match "
                "the requested candidate."
            ),
        )

    # 4. Load the ATS score using the actual storage structure.
    ats_score = _load_ats_score(
        job_id=job_id,
        candidate_id=candidate_id,
        jd_id=jd_id,
    )

    
    # 5. Evaluate candidate eligibility.
    try:
        result = evaluate_candidate_eligibility(
            candidate_profile=candidate_profile,
            generated_rules=generated_rules,
            ats_score=ats_score,
        )

        logger.info(
            "Eligibility evaluation returned type=%s for candidate=%s",
            type(result).__name__,
            candidate_id,
        )

    except Exception:
        logger.exception(
            "Eligibility evaluation crashed for job=%s candidate=%s",
            job_id,
            candidate_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Candidate eligibility evaluation failed.",
        )

    if not isinstance(result, dict):
        logger.error(
            "Invalid eligibility result: type=%s, value=%r",
            type(result).__name__,
            result,
        )
        raise HTTPException(
            status_code=500,
            detail="Eligibility service returned an invalid result.",
        )

    # Validate the minimum result structure.
    if not isinstance(result.get("checks"), dict):
        logger.error(
            "Eligibility result has invalid checks: %r",
            result.get("checks"),
        )
        raise HTTPException(
            status_code=500,
            detail="Eligibility service returned invalid checks.",
        )

    if result.get("eligibility_status") not in {
        "ELIGIBLE",
        "REVIEW_REQUIRED",
        "REJECTED",
    }:
        logger.error(
            "Eligibility result has invalid status: %r",
            result.get("eligibility_status"),
        )
        raise HTTPException(
            status_code=500,
            detail="Eligibility service returned an invalid status.",
        )


    # 7. Add identifiers and evaluation metadata to the saved result.
    # These fields also allow the GET result endpoint to validate the file.
    result["job_id"] = job_id
    result["candidate_id"] = candidate_id
    result["jd_id"] = jd_id
    result["ats_score"] = ats_score
    result["evaluated_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    result["rule_version"] = generated_rules.get(
        "rule_version",
        "1.0",
    )

    # 8. Persist eligibility separately from ATS scoring results.
    result_path = (
        ELIGIBILITY_RESULTS_DIR
        / job_id
        / f"{candidate_id}.json"
    )

    _save_json(
        result_path,
        result,
        "eligibility result",
    )

    # 9. Return the evaluated and saved result.
    return result


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/result"
)
def get_candidate_eligibility_result(
    job_id: str,
    candidate_id: str,
) -> dict[str, Any]:
    """Retrieve the latest saved eligibility result."""
    _validate_identifier(job_id, "job_id")
    _validate_identifier(candidate_id, "candidate_id")

    result_path = (
        ELIGIBILITY_RESULTS_DIR
        / job_id
        / f"{candidate_id}.json"
    )

    result = _load_json(
        result_path,
        "Eligibility result",
    )

    if (
        result.get("job_id") != job_id
        or result.get("candidate_id") != candidate_id
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "The saved eligibility result does not match "
                "the requested job and candidate."
            ),
        )

    return result
