
"""
transcript_skill_extraction_persistence_service.py

Responsibilities
----------------
1. Validate a saved transcript before extraction.
2. Orchestrate transcript skill extraction.
3. Preserve transcript and screening metadata.
4. Persist extraction results separately from transcript JSON.
5. Avoid duplicate results for repeated processing.
6. Write result JSON atomically.

Existing transcript and normalization services are not modified.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from api.service.transcript_skill_extraction_service import (
    extract_transcript_skills,
)


DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "hr_screening"
    / "transcript_skill_results"
)

EXTRACTION_VERSION = "1.1"

SUPPORTED_LANGUAGES = {"en", "ml", "hi"}

ID_PATTERNS = {
    "session_id": re.compile(r"^SCREEN_[A-F0-9]{12}$"),
    "candidate_id": re.compile(r"^CAN_[A-Z0-9]+$"),
    "job_id": re.compile(r"^JOB_[A-Z0-9]+$"),
    "transcript_id": re.compile(r"^TRN_[A-F0-9]+$"),
    "question_id": re.compile(r"^[A-Z0-9_]+$"),
}


class TranscriptSkillPersistenceError(Exception):
    """Raised when transcript skill extraction or persistence fails."""


def _utc_now() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _validate_transcript(transcript: dict[str, Any]) -> None:
    """Validate the transcript fields required for extraction and tracing."""

    if not isinstance(transcript, dict):
        raise TranscriptSkillPersistenceError(
            "Transcript must be supplied as a dictionary."
        )

    required_fields = (
        "session_id",
        "candidate_id",
        "job_id",
        "question_id",
        "transcript_id",
        "language",
        "original_text",
        "normalized_text",
        "status",
    )

    for field in required_fields:
        if field not in transcript:
            raise TranscriptSkillPersistenceError(
                f"Missing required transcript field: {field}"
            )

    for field in (
        "session_id",
        "candidate_id",
        "job_id",
        "question_id",
        "transcript_id",
        "language",
        "status",
    ):
        value = transcript[field]
        if not isinstance(value, str) or not value.strip():
            raise TranscriptSkillPersistenceError(
                f"Transcript field '{field}' must be a non-empty string."
            )

    for field in ("original_text", "normalized_text"):
        if not isinstance(transcript[field], str):
            raise TranscriptSkillPersistenceError(
                f"Transcript field '{field}' must be a string."
            )

    for field, pattern in ID_PATTERNS.items():
        if not pattern.fullmatch(transcript[field]):
            raise TranscriptSkillPersistenceError(
                f"Invalid format for transcript field '{field}'."
            )

    if transcript["language"] not in SUPPORTED_LANGUAGES:
        raise TranscriptSkillPersistenceError(
            f"Unsupported language: {transcript['language']}"
        )

    if transcript["status"] != "PROCESSED":
        raise TranscriptSkillPersistenceError(
            "Only transcripts with status 'PROCESSED' can be processed."
        )


def _text_fingerprint(normalized_text: str) -> str:
    """Fingerprint the exact normalized text used for extraction."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def _result_id(session_id: str, transcript_id: str) -> str:
    """Generate a stable result ID for a session/transcript pair."""
    identity = f"{session_id}:{transcript_id}".encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()[:12].upper()
    return f"TSR_{digest}"


def _write_json_atomically(
    destination: Path,
    payload: dict[str, Any],
) -> None:
    """Write JSON to a temporary file and atomically replace the destination."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.stem}_",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(
                payload,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, destination)

    except OSError as exc:
        raise TranscriptSkillPersistenceError(
            f"Could not save transcript skill results: {destination}"
        ) from exc

    finally:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass


def process_and_save_transcript_skills(
    transcript: dict[str, Any],
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    Extract skills from a processed transcript and persist the result.

    Args:
        transcript: The saved transcript JSON loaded as a dictionary.
        output_dir: Optional override for the result root directory.

    Returns:
        The persisted result dictionary.

    Reprocessing an unchanged transcript returns its existing result.
    If normalized text changes, the result is recalculated and updated.
    """

    _validate_transcript(transcript)

    output_root = (
        Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    )

    destination = (
        output_root
        / transcript["session_id"]
        / f"{transcript['transcript_id']}.json"
    )

    fingerprint = _text_fingerprint(transcript["normalized_text"])

    # Idempotency: reuse the saved result if the extraction input is unchanged.
    if destination.exists():
        try:
            with destination.open("r", encoding="utf-8") as file:
                existing_result = json.load(file)

            if (
                isinstance(existing_result, dict)
                and existing_result.get("session_id") == transcript["session_id"]
                and existing_result.get("transcript_id") == transcript["transcript_id"]
                and existing_result.get("input_text_sha256") == fingerprint
                and existing_result.get("extraction_version") == EXTRACTION_VERSION
                and existing_result.get("status") == "COMPLETED"
            ):
                return existing_result

        except (OSError, json.JSONDecodeError):
            # An unreadable or invalid existing file is regenerated below.
            pass

    try:
        extraction = extract_transcript_skills(
            {
                "original_text": transcript["original_text"],
                "normalized_text": transcript["normalized_text"],
                "language": transcript["language"],
            }
        )
    except Exception as exc:
        raise TranscriptSkillPersistenceError(
            "Transcript skill extraction failed."
        ) from exc

    recognized_skills = extraction.get("recognized_skills")

    if not isinstance(recognized_skills, list):
        raise TranscriptSkillPersistenceError(
            "Skill extraction returned an invalid 'recognized_skills' value."
        )

    now = _utc_now()

    result = {
        "result_id": _result_id(
            transcript["session_id"],
            transcript["transcript_id"],
        ),
        "transcript_id": transcript["transcript_id"],
        "session_id": transcript["session_id"],
        "candidate_id": transcript["candidate_id"],
        "job_id": transcript["job_id"],
        "question_id": transcript["question_id"],
        "source": transcript.get("source"),
        "language": transcript["language"],
        "recognized_skills": recognized_skills,
        "skill_count": len(recognized_skills),
        "extraction_version": EXTRACTION_VERSION,
        "input_text_sha256": fingerprint,
        "status": "COMPLETED",
        "created_at": now,
        "updated_at": now,
    }

    # Preserve the original creation timestamp when updating an existing result.
    if destination.exists():
        try:
            with destination.open("r", encoding="utf-8") as file:
                previous_result = json.load(file)

            if isinstance(previous_result, dict):
                result["created_at"] = previous_result.get("created_at", now)
        except (OSError, json.JSONDecodeError):
            pass

    _write_json_atomically(destination, result)

    return result
