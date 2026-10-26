
"""
transcript_service.py

Responsibilities
----------------
1. Validate transcript input using TranscriptCreate.
2. Normalize transcript text without changing the original.
3. Verify transcript ownership and question membership against the
   persisted screening session.
4. Build a validated TranscriptRecord.
5. Persist transcript JSON files by screening session.
6. Retrieve a transcript by session and transcript ID.
7. List transcripts belonging to a screening session.
8. Prevent path traversal and accidental transcript overwrites.
9. Use atomic file creation to avoid partially written JSON records.

This service does not transcribe audio or evaluate candidate answers.
"""

import json
import logging
import os
import re
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from api.schemas.transcript_schema import (
    TranscriptCreate,
    TranscriptRecord,
    TranscriptStatus,
)
from api.service.transcript_normalization_service import (
    TranscriptNormalizationError,
    normalize_transcript,
)
from api.service.screening_session_service import (
    ScreeningSessionNotFoundError,
    ScreeningSessionStorageError,
    ScreeningSessionValidationError,
    get_screening_session,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRANSCRIPT_ROOT = (
    PROJECT_ROOT
    / "data"
    / "hr_screening"
    / "transcripts"
)

SAFE_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$"
)

TRANSCRIPT_ID_PREFIX = "TRN_"
TRANSCRIPT_ID_HEX_LENGTH = 12


# ============================================================
# EXCEPTIONS
# ============================================================

class TranscriptServiceError(Exception):
    """Base exception for transcript service failures."""


class TranscriptNotFoundError(TranscriptServiceError):
    """Raised when a requested transcript does not exist."""


class TranscriptAlreadyExistsError(TranscriptServiceError):
    """Raised when a transcript ID already exists."""


class TranscriptPersistenceError(TranscriptServiceError):
    """Raised when transcript data cannot be safely persisted or read."""


class TranscriptInputError(TranscriptServiceError):
    """Raised when transcript input or identifiers are invalid."""


class TranscriptSessionNotFoundError(TranscriptServiceError):
    """Raised when the associated screening session does not exist."""


# ============================================================
# IDENTIFIER AND PATH VALIDATION
# ============================================================

def _validate_identifier(
    value: str,
    field_name: str,
) -> str:
    """Validate an identifier before using it in a filesystem path."""

    if (
        not isinstance(value, str)
        or not SAFE_ID_PATTERN.fullmatch(value)
    ):
        raise TranscriptInputError(
            f"Invalid {field_name} format."
        )

    return value


def _generate_transcript_id() -> str:
    """Generate an ID such as TRN_A1B2C3D4E5F6."""

    return (
        f"{TRANSCRIPT_ID_PREFIX}"
        f"{uuid4().hex[:TRANSCRIPT_ID_HEX_LENGTH].upper()}"
    )


def _session_directory(session_id: str) -> Path:
    """Return the validated storage directory for one session."""

    safe_session_id = _validate_identifier(
        session_id,
        "session_id",
    )

    return TRANSCRIPT_ROOT / safe_session_id


def _transcript_file_path(
    session_id: str,
    transcript_id: str,
) -> Path:
    """Build a safe path for a transcript JSON file."""

    safe_session_id = _validate_identifier(
        session_id,
        "session_id",
    )
    safe_transcript_id = _validate_identifier(
        transcript_id,
        "transcript_id",
    )

    root = TRANSCRIPT_ROOT.resolve()
    directory = (root / safe_session_id).resolve()
    target = (
        directory / f"{safe_transcript_id}.json"
    ).resolve()

    if directory.parent != root or target.parent != directory:
        raise TranscriptInputError(
            "Invalid transcript storage path."
        )

    return target


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_transcript_input(
    payload: TranscriptCreate | dict[str, Any],
) -> TranscriptCreate:
    """Validate transcript input against the Pydantic schema."""

    try:
        if isinstance(payload, TranscriptCreate):
            validated = payload
        else:
            validated = TranscriptCreate.model_validate(payload)

        _validate_identifier(
            validated.session_id,
            "session_id",
        )
        _validate_identifier(
            validated.candidate_id,
            "candidate_id",
        )
        _validate_identifier(
            validated.job_id,
            "job_id",
        )
        _validate_identifier(
            validated.question_id,
            "question_id",
        )

        return validated

    except ValidationError as exc:
        raise TranscriptInputError(
            "Transcript input failed schema validation."
        ) from exc




def _question_is_assigned(
    session: dict,
    question_id: str,
) -> bool:
    """Check assigned question IDs case-insensitively."""

    target_id = question_id.strip().casefold()

    if not target_id:
        return False

    questions = session.get("questions", [])

    if not isinstance(questions, list):
        return False

    for question in questions:
        if isinstance(question, str):
            assigned_id = question
        elif isinstance(question, dict):
            assigned_id = question.get(
                "question_id",
                question.get("id"),
            )
        else:
            continue

        if (
            isinstance(assigned_id, str)
            and assigned_id.strip().casefold() == target_id
        ):
            return True

    return False


# ============================================================
# SCREENING SESSION VALIDATION
# ============================================================


def _validate_transcript_session(
    payload: TranscriptCreate,
) -> None:
    """
    Verify the transcript against the persisted screening session.

    The session file is the source of truth for candidate, job,
    language, and assigned question membership.
    """

    try:
        session = get_screening_session(
            payload.session_id
        )

    except ScreeningSessionNotFoundError as exc:
        raise TranscriptSessionNotFoundError(
            "Screening session was not found."
        ) from exc

    except ScreeningSessionValidationError as exc:
        raise TranscriptInputError(
            "Invalid screening session ID."
        ) from exc

    except ScreeningSessionStorageError as exc:
        raise TranscriptPersistenceError(
            "Unable to verify the screening session."
        ) from exc

    # Validate candidate ownership.
    if session.get("candidate_id") != payload.candidate_id:
        raise TranscriptInputError(
            "Candidate does not match the screening session."
        )

    # Validate job association.
    if session.get("job_id") != payload.job_id:
        raise TranscriptInputError(
            "Job does not match the screening session."
        )

    # Validate transcript language.
    if session.get("language") != payload.language:
        raise TranscriptInputError(
            "Transcript language does not match the screening session."
        )

    # Validate assigned question data.
    questions = session.get("questions")

    if not isinstance(questions, list):
        raise TranscriptPersistenceError(
            "Screening session contains invalid question data."
        )

    # Validate question membership case-insensitively.
    if not _question_is_assigned(
        session,
        payload.question_id,
    ):
        raise TranscriptInputError(
            "Question does not belong to the screening session."
        )



# ============================================================
# RECORD CONSTRUCTION
# ============================================================

def _build_transcript_record(
    payload: TranscriptCreate,
    transcript_id: str,
) -> TranscriptRecord:
    """
    Normalize transcript text and construct a validated record.

    original_text remains unchanged.
    normalized_text is produced by the normalization service.
    """

    try:
        normalized = normalize_transcript(
            text=payload.original_text,
            language=payload.language,
        )

        data = payload.model_dump(mode="python")

        data["transcript_id"] = transcript_id
        data["status"] = TranscriptStatus.PROCESSED
        data["normalized_text"] = normalized.normalized_text

        normalization_metadata = (
            data.get("normalization") or {}
        )
        normalization_metadata.update(
            {
                "version": normalized.normalization_version,
                "language_preserved": normalized.language_preserved,
            }
        )
        data["normalization"] = normalization_metadata

        timing = data.get("timing") or {}

        if timing.get("transcribed_at") is None:
            timing["transcribed_at"] = datetime.now(
                timezone.utc
            )

        data["timing"] = timing

        now = datetime.now(timezone.utc)
        data["created_at"] = now
        data["updated_at"] = now

        return TranscriptRecord.model_validate(data)

    except TranscriptNormalizationError as exc:
        raise TranscriptInputError(
            "Transcript text or language failed normalization validation."
        ) from exc

    except ValidationError as exc:
        raise TranscriptInputError(
            "The resulting transcript record failed schema validation."
        ) from exc


# ============================================================
# ATOMIC JSON PERSISTENCE
# ============================================================

def _write_json_atomically(
    target: Path,
    record: TranscriptRecord,
) -> None:
    """Persist a transcript without overwriting an existing file."""

    temporary_path: Path | None = None

    try:
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not target.parent.is_dir():
            raise TranscriptPersistenceError(
                "Transcript storage path is not a directory."
            )

    except OSError as exc:
        logger.exception(
            "Unable to create transcript storage directory."
        )
        raise TranscriptPersistenceError(
            "Unable to create transcript storage directory."
        ) from exc

    try:
        serialized = json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=".transcript_",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

            temporary_file.write(serialized)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

    except (OSError, TypeError, ValueError) as exc:
        logger.exception(
            "Unable to prepare transcript JSON."
        )
        raise TranscriptPersistenceError(
            "Unable to prepare transcript JSON for storage."
        ) from exc

    try:
        # Atomic no-overwrite creation. The temporary file is created
        # in the same directory to keep both paths on the same filesystem.
        os.link(temporary_path, target)

    except FileExistsError as exc:
        raise TranscriptAlreadyExistsError(
            "A transcript with this ID already exists in the session."
        ) from exc

    except OSError as exc:
        logger.exception(
            "Unable to persist transcript."
        )
        raise TranscriptPersistenceError(
            "Unable to persist transcript."
        ) from exc

    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logger.warning(
                    "Could not remove temporary transcript file."
                )


# ============================================================
# READ STORED TRANSCRIPT
# ============================================================

def _read_transcript_file(
    path: Path,
) -> TranscriptRecord:
    """Read and validate a stored transcript JSON record."""

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return TranscriptRecord.model_validate(data)

    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        logger.exception(
            "Stored transcript is unreadable or invalid."
        )
        raise TranscriptPersistenceError(
            "Stored transcript could not be read or validated."
        ) from exc


# ============================================================
# CREATE TRANSCRIPT
# ============================================================

def create_transcript(
    payload: TranscriptCreate | dict[str, Any],
    *,
    transcript_id: str | None = None,
) -> TranscriptRecord:
    """
    Validate, verify, normalize, save, and return a transcript.

    The associated screening session must exist, and the candidate,
    job, language, and question must match that session.
    """

    # 1. Validate the submitted payload.
    validated_payload = validate_transcript_input(payload)

    # 2. Verify that the transcript belongs to the saved session.
    _validate_transcript_session(validated_payload)

    # 3. Select and validate the transcript ID.
    selected_id = (
        transcript_id
        if transcript_id is not None
        else _generate_transcript_id()
    )

    selected_id = _validate_identifier(
        selected_id,
        "transcript_id",
    )

    # 4. Normalize text and construct the record.
    record = _build_transcript_record(
        payload=validated_payload,
        transcript_id=selected_id,
    )

    # 5. Build the safe destination path.
    target = _transcript_file_path(
        record.session_id,
        record.transcript_id,
    )

    # 6. Save without overwriting an existing transcript.
    _write_json_atomically(
        target=target,
        record=record,
    )

    logger.info(
        "Transcript created | session_id=%s | transcript_id=%s",
        record.session_id,
        record.transcript_id,
    )

    return record


# ============================================================
# GET TRANSCRIPT
# ============================================================

def get_transcript(
    session_id: str,
    transcript_id: str,
) -> TranscriptRecord:
    """Retrieve one transcript within the specified session."""

    target = _transcript_file_path(
        session_id=session_id,
        transcript_id=transcript_id,
    )

    try:
        record = _read_transcript_file(target)

    except TranscriptPersistenceError as exc:
        if not target.exists():
            raise TranscriptNotFoundError(
                "Transcript was not found in the requested session."
            ) from exc
        raise

    if (
        record.session_id != session_id
        or record.transcript_id != transcript_id
    ):
        raise TranscriptPersistenceError(
            "Stored transcript identifiers do not match the requested path."
        )

    return record


# ============================================================
# LIST TRANSCRIPTS
# ============================================================

def list_transcripts(
    session_id: str,
) -> list[TranscriptRecord]:
    """
    Retrieve all valid transcripts for one screening session.

    Returns an empty list when no transcript directory exists.
    """

    directory = _session_directory(session_id)

    if not directory.exists():
        return []

    if not directory.is_dir():
        raise TranscriptPersistenceError(
            "Transcript storage path is not a directory."
        )

    records: list[TranscriptRecord] = []

    try:
        paths = sorted(
            directory.glob("*.json"),
            key=lambda path: path.name,
        )

        for path in paths:
            record = _read_transcript_file(path)

            if record.session_id != session_id:
                raise TranscriptPersistenceError(
                    "Stored transcript belongs to a different session."
                )

            if path.stem != record.transcript_id:
                raise TranscriptPersistenceError(
                    "Stored transcript ID does not match its filename."
                )

            records.append(record)

    except OSError as exc:
        logger.exception(
            "Unable to list transcripts for session."
        )
        raise TranscriptPersistenceError(
            "Unable to list transcripts for this session."
        ) from exc

    records.sort(
        key=lambda record: (
            record.created_at,
            record.transcript_id,
        )
    )

    return records
