
"""
screening_response_service.py

Responsibilities
----------------
1. Validate screening session existence and ownership.
2. Validate question assignments and answer types.
3. Validate selected options against configured choices.
4. Save and update candidate responses.
5. Track mandatory question completion.
6. Support draft and final submissions.
7. Prevent final submission when mandatory answers are missing.
8. Persist response data without exposing internal file paths.
9. Store candidate_id for evaluation integrity checks.
10. Normalize question IDs consistently across submission and retrieval.

Question retrieval remains in question_bank_service.py.
Request validation remains in hr_screening_schema.py.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile

from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from api.schemas.hr_screening_schema import (
    ScreeningAnswerSubmission,
    ScreeningResponseSubmissionRequest,
    ScreeningSessionStatus,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCREENING_DATA_DIR = PROJECT_ROOT / "data" / "hr_screening"
SESSION_DIR = SCREENING_DATA_DIR / "sessions"
RESPONSE_DIR = SCREENING_DATA_DIR / "responses"

# Protects read-modify-write operations within this process.
_STORAGE_LOCK = RLock()

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,200}$")

ALLOWED_SESSION_STATUSES = {
    ScreeningSessionStatus.CREATED.value,
    ScreeningSessionStatus.IN_PROGRESS.value,
}


SUPPORTED_ANSWER_TYPES = {
    "TEXT",
    "SINGLE_CHOICE",
    "MULTIPLE_CHOICE",
    "BOOLEAN",
    "YES_NO_WITH_DETAILS",
    "MULTI_SELECT_WITH_DETAILS",
    "CURRENCY_RANGE",
    "DATE_OR_DURATION",
}



# ============================================================
# SERVICE ERRORS
# ============================================================

class ScreeningResponseError(Exception):
    """Base exception for screening response operations."""


class ScreeningSessionNotFoundError(ScreeningResponseError):
    """Raised when a screening session does not exist."""


class ScreeningOwnershipError(ScreeningResponseError):
    """Raised when the session belongs to another candidate."""


class ScreeningSessionStateError(ScreeningResponseError):
    """Raised when the session cannot accept responses."""


class ScreeningQuestionError(ScreeningResponseError):
    """Raised when a question is invalid or not assigned."""


class ScreeningAnswerError(ScreeningResponseError):
    """Raised when an answer violates question rules."""


class ScreeningMandatoryQuestionsError(ScreeningResponseError):
    """Raised when mandatory questions remain unanswered."""

    def __init__(self, question_ids: list[str]):
        self.question_ids = question_ids
        super().__init__(
            "Mandatory screening questions remain unanswered."
        )


class ScreeningStorageError(ScreeningResponseError):
    """Raised when screening data cannot be read or persisted."""


# ============================================================
# COMMON HELPERS
# ============================================================

def _utc_now() -> str:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _validate_identifier(value: str, field: str) -> str:
    """Reject unsafe or malformed identifiers."""
    if not isinstance(value, str):
        raise ValueError(f"Invalid {field}.")

    value = value.strip()

    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid {field}.")

    return value


def _session_path(session_id: str) -> Path:
    """Resolve a validated session identifier."""
    if not isinstance(session_id, str):
        raise ValueError("Invalid session_id.")

    session_id = session_id.strip()

    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError("Invalid session_id.")

    return SESSION_DIR / f"{session_id}.json"


def _response_path(session_id: str) -> Path:
    """Resolve the response file for a validated session."""
    if not isinstance(session_id, str):
        raise ValueError("Invalid session_id.")

    session_id = session_id.strip()

    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError("Invalid session_id.")

    return RESPONSE_DIR / f"{session_id}.json"


def _normalize_question_id(value: Any) -> str:
    """Normalize question IDs for case-insensitive matching."""
    if not isinstance(value, str):
        return ""

    return value.strip().casefold()


def _canonical_question_id(question: dict[str, Any]) -> str:
    """Return the trimmed, canonical question ID from an assignment."""
    value = question.get("question_id", question.get("id"))

    if not isinstance(value, str) or not value.strip():
        raise ScreeningStorageError(
            "Assigned question has no valid identifier."
        )

    return value.strip()



def _saved_answer_is_answered(answer: Any) -> bool:
    """Return True when a saved answer has meaningful content."""
    if not isinstance(answer, dict):
        return False

    text_answer = answer.get("answer")
    if isinstance(text_answer, str) and text_answer.strip():
        return True

    selected_options = answer.get("selected_options")
    if isinstance(selected_options, list) and any(
        isinstance(option, str) and option.strip()
        for option in selected_options
    ):
        return True

    if answer.get("minimum_amount") is not None:
        return True
    if answer.get("maximum_amount") is not None:
        return True
    if answer.get("joining_date"):
        return True

    duration = answer.get("duration")
    if isinstance(duration, str) and duration.strip():
        return True

    return False

# ============================================================
# JSON STORAGE
# ============================================================

def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object without exposing filesystem details."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except FileNotFoundError:
        raise

    except (OSError, json.JSONDecodeError) as exc:
        logger.error(
            "Unable to read screening storage file: %s",
            path.name,
        )
        raise ScreeningStorageError(
            "Unable to read screening data."
        ) from exc

    if not isinstance(data, dict):
        raise ScreeningStorageError(
            "Screening storage contains an invalid record."
        )

    return data


def _write_json_atomic(
    path: Path,
    data: dict[str, Any],
) -> None:
    """
    Write JSON through a temporary file and atomically replace
    the destination to reduce the risk of partial writes.
    """
    temp_path: Path | None = None

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, path)

    except (OSError, TypeError, ValueError) as exc:
        logger.error(
            "Unable to persist screening data: %s",
            path.name,
        )

        raise ScreeningStorageError(
            "Unable to save screening responses."
        ) from exc

    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                logger.warning(
                    "Unable to remove temporary screening file."
                )


def _load_session(session_id: str) -> dict[str, Any]:
    """Load a session or raise a domain-specific exception."""
    path = _session_path(session_id)

    try:
        session = _read_json(path)

    except FileNotFoundError as exc:
        raise ScreeningSessionNotFoundError(
            "Screening session not found."
        ) from exc

    required_fields = {
        "session_id",
        "candidate_id",
        "job_id",
        "status",
        "questions",
    }

    if not required_fields.issubset(session):
        raise ScreeningStorageError(
            "Screening session record is incomplete."
        )

    if not isinstance(session["questions"], list):
        raise ScreeningStorageError(
            "Screening session questions are invalid."
        )

    if session["session_id"] != session_id:
        raise ScreeningStorageError(
            "Screening session identifier mismatch."
        )

    try:
        _validate_identifier(session["candidate_id"], "candidate_id")
        _validate_identifier(session["job_id"], "job_id")
    except (TypeError, ValueError) as exc:
        raise ScreeningStorageError(
            "Screening session references are invalid."
        ) from exc

    return session


def _load_responses(
    session_id: str,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    """
    Load saved responses, returning an empty record if new.

    Existing response records without candidate_id remain readable.
    When candidate_id is provided, new or updated records receive it.
    """
    path = _response_path(session_id)

    try:
        responses = _read_json(path)

    except FileNotFoundError:
        responses = {
            "session_id": session_id,
            "answers": {},
            "created_at": _utc_now(),
            "updated_at": None,
        }

    if responses.get("session_id") != session_id:
        raise ScreeningStorageError(
            "Screening response session mismatch."
        )

    if not isinstance(responses.get("answers"), dict):
        raise ScreeningStorageError(
            "Screening response data is invalid."
        )

    stored_candidate_id = responses.get("candidate_id")

    if stored_candidate_id is not None:
        try:
            _validate_identifier(
                stored_candidate_id,
                "candidate_id",
            )
        except (TypeError, ValueError) as exc:
            raise ScreeningStorageError(
                "Screening response candidate reference is invalid."
            ) from exc

    if (
        candidate_id is not None
        and stored_candidate_id is not None
        and stored_candidate_id != candidate_id
    ):
        raise ScreeningStorageError(
            "Screening response candidate mismatch."
        )

    if candidate_id is not None:
        responses["candidate_id"] = candidate_id

    return responses


# ============================================================
# QUESTION VALIDATION
# ============================================================

def _build_question_map(
    session: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Build a case-insensitive map of assigned questions.

    The original question records are preserved. Normalized IDs are
    used only as lookup keys.
    """
    raw_questions = session.get("questions")

    if not isinstance(raw_questions, list):
        raise ScreeningStorageError(
            "Screening session questions are invalid."
        )

    question_map: dict[str, dict[str, Any]] = {}

    for question in raw_questions:
        if not isinstance(question, dict):
            raise ScreeningStorageError(
                "Invalid question assignment in screening session."
            )

        question_id = question.get(
            "question_id",
            question.get("id"),
        )
        key = _normalize_question_id(question_id)

        if not key:
            raise ScreeningStorageError(
                "Assigned question has no valid identifier."
            )

        if key in question_map:
            raise ScreeningStorageError(
                "Duplicate question assignments found."
            )

        question_map[key] = question

    logger.debug(
        "Loaded assigned screening questions | session_id=%s | "
        "assigned_question_count=%d",
        session.get("session_id"),
        len(question_map),
    )

    return question_map


def _normalize_saved_answers(
    answers: dict[str, Any],
    question_map: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Normalize saved answers to canonical assigned question IDs.

    Reject unassigned questions and duplicate answers, including IDs
    that differ only by case.
    """
    normalized_answers: dict[str, dict[str, Any]] = {}
    seen_question_ids: set[str] = set()

    for stored_key, stored_answer in answers.items():
        if not isinstance(stored_answer, dict):
            raise ScreeningStorageError(
                "A saved screening answer is invalid."
            )

        answer_qid = stored_answer.get(
            "question_id",
            stored_key,
        )
        normalized_qid = _normalize_question_id(answer_qid)

        if not normalized_qid or normalized_qid not in question_map:
            raise ScreeningStorageError(
                "Saved response references an unassigned question."
            )

        if normalized_qid in seen_question_ids:
            raise ScreeningStorageError(
                "Duplicate saved answers exist for a question."
            )

        seen_question_ids.add(normalized_qid)

        question = question_map[normalized_qid]
        canonical_id = _canonical_question_id(question)

        normalized_answers[canonical_id] = {
            **stored_answer,
            "question_id": canonical_id,
        }

    return normalized_answers


def _question_is_mandatory(
    question: dict[str, Any],
) -> bool:
    """Resolve and validate the question's mandatory flag."""
    for key in ("mandatory", "is_mandatory", "required"):
        if key in question:
            value = question[key]

            if not isinstance(value, bool):
                raise ScreeningStorageError(
                    "Invalid mandatory-question configuration."
                )

            return value

    return False


def _get_answer_type(question: dict[str, Any]) -> str:
    """Resolve the answer type configured for a question."""
    answer_type = question.get(
        "answer_type",
        question.get("type", "TEXT"),
    )

    if not isinstance(answer_type, str):
        raise ScreeningStorageError(
            "Invalid question answer-type configuration."
        )

    answer_type = answer_type.strip().upper()

    if answer_type not in SUPPORTED_ANSWER_TYPES:
        raise ScreeningStorageError(
            "Unsupported question answer type."
        )

    return answer_type


def _get_option_values(
    question: dict[str, Any],
) -> set[str]:
    """Extract allowed option identifiers from question metadata."""
    raw_options = question.get(
        "options",
        question.get("choices", []),
    )

    if not isinstance(raw_options, list):
        raise ScreeningStorageError(
            "Invalid question options configuration."
        )

    allowed: set[str] = set()

    for option in raw_options:
        if isinstance(option, str):
            value = option

        elif isinstance(option, dict):
            value = option.get(
                "option_id",
                option.get("id", option.get("value")),
            )

        else:
            raise ScreeningStorageError(
                "Invalid question option configuration."
            )

        if not isinstance(value, str) or not value.strip():
            raise ScreeningStorageError(
                "Question option has no valid identifier."
            )

        normalized = value.strip().casefold()

        if normalized in allowed:
            raise ScreeningStorageError(
                "Duplicate question options found."
            )

        allowed.add(normalized)

    if not allowed:
        raise ScreeningStorageError(
            "Choice question has no configured options."
        )

    return allowed



def _validate_answer_against_question(
    answer: ScreeningAnswerSubmission,
    question: dict[str, Any],
) -> dict[str, Any]:
    """Validate the submitted answer using its assigned question type."""
    answer_type = _get_answer_type(question)

    text_answer = answer.answer
    selected_options = answer.selected_options
    details = answer.details

    if details is not None:
        details = details.strip() or None

    if answer_type == "TEXT":
        if not text_answer or not text_answer.strip():
            raise ScreeningAnswerError(
                "This question requires a non-empty text answer."
            )
        if selected_options is not None or any((
            answer.currency is not None,
            answer.minimum_amount is not None,
            answer.maximum_amount is not None,
            answer.joining_date is not None,
            answer.duration is not None,
        )):
            raise ScreeningAnswerError(
                "This question accepts a text answer only."
            )
        text_answer = text_answer.strip()

    elif answer_type in {"BOOLEAN", "YES_NO_WITH_DETAILS"}:
        if not text_answer:
            raise ScreeningAnswerError(
                "Provide yes or no for this question."
            )

        normalized = text_answer.strip().casefold()
        if normalized not in {"yes", "no", "true", "false"}:
            raise ScreeningAnswerError(
                "Answer must be yes or no."
            )

        if selected_options is not None:
            raise ScreeningAnswerError(
                "This question does not accept selected options."
            )

        text_answer = (
            "yes" if normalized in {"yes", "true"} else "no"
        )

        if answer_type == "BOOLEAN" and details:
            raise ScreeningAnswerError(
                "This boolean question does not accept additional details."
            )

    elif answer_type in {"SINGLE_CHOICE", "MULTIPLE_CHOICE"}:
        if text_answer is not None or not selected_options:
            raise ScreeningAnswerError(
                "Provide selected options for this question."
            )

        if answer_type == "SINGLE_CHOICE" and len(selected_options) != 1:
            raise ScreeningAnswerError(
                "Select exactly one option for this question."
            )

    elif answer_type == "MULTI_SELECT_WITH_DETAILS":
        if not selected_options:
            raise ScreeningAnswerError(
                "Select at least one option for this question."
            )
        if text_answer is not None:
            raise ScreeningAnswerError(
                "Use selected_options for the choices and details for explanation."
            )

    elif answer_type == "CURRENCY_RANGE":
        if any((
            text_answer is not None,
            selected_options is not None,
            answer.currency is None,
            answer.minimum_amount is None,
            answer.maximum_amount is None,
        )):
            raise ScreeningAnswerError(
                "Provide currency, minimum_amount, and maximum_amount."
            )

        if answer.maximum_amount < answer.minimum_amount:
            raise ScreeningAnswerError(
                "maximum_amount cannot be less than minimum_amount."
            )

        if not answer.currency.isalpha():
            raise ScreeningAnswerError(
                "Currency must be a three-letter currency code."
            )

    elif answer_type == "DATE_OR_DURATION":
        if selected_options is not None:
            raise ScreeningAnswerError(
                "This question accepts a joining date or duration."
            )

        if not any((
            answer.joining_date is not None,
            bool(answer.duration and answer.duration.strip()),
            bool(text_answer and text_answer.strip()),
        )):
            raise ScreeningAnswerError(
                "Provide a joining date or joining duration."
            )

    # Validate choices against the question's configured option IDs.
    if selected_options is not None:
        allowed_options = _get_option_values(question)
        normalized_options = [option.strip() for option in selected_options]

        if any(not option for option in normalized_options):
            raise ScreeningAnswerError(
                "Selected options cannot be empty."
            )

        normalized_keys = [option.casefold() for option in normalized_options]

        if len(normalized_keys) != len(set(normalized_keys)):
            raise ScreeningAnswerError(
                "Duplicate selected options are not allowed."
            )

        if any(option not in allowed_options for option in normalized_keys):
            raise ScreeningAnswerError(
                "One or more selected options are invalid."
            )

        selected_options = normalized_options

    return {
        "question_id": _canonical_question_id(question),
        "answer": text_answer,
        "selected_options": selected_options,
        "details": details,
        "currency": answer.currency,
        "minimum_amount": answer.minimum_amount,
        "maximum_amount": answer.maximum_amount,
        "joining_date": (
            answer.joining_date.isoformat()
            if answer.joining_date is not None
            else None
        ),
        "duration": answer.duration,
        "answered": True,
        "updated_at": _utc_now(),
    }


# ============================================================
# SUBMIT SCREENING RESPONSES
# ============================================================

def submit_screening_responses(
    *,
    session_id: str,
    candidate_id: str,
    request: ScreeningResponseSubmissionRequest,
) -> dict[str, Any]:
    """
    Save candidate answers for a screening session.

    Draft submission:
        - Saves valid answers.
        - Keeps the session IN_PROGRESS.

    Final submission:
        - Saves valid answers.
        - Checks all mandatory questions.
        - Marks the session SUBMITTED only if all mandatory
          questions have meaningful answers.

    Existing answers for omitted questions are preserved.
    """
    session_id = _validate_identifier(
        session_id,
        "session_id",
    )
    candidate_id = _validate_identifier(
        candidate_id,
        "candidate_id",
    )

    if not isinstance(request, ScreeningResponseSubmissionRequest):
        raise ValueError("Invalid screening response request.")

    with _STORAGE_LOCK:
        session = _load_session(session_id)
        stored_candidate_id = session["candidate_id"]

        if stored_candidate_id != candidate_id:
            raise ScreeningOwnershipError(
                "Candidate does not own this screening session."
            )

        session_status = session["status"]

        if session_status not in ALLOWED_SESSION_STATUSES:
            raise ScreeningSessionStateError(
                "This screening session cannot accept responses."
            )

        question_map = _build_question_map(session)

        responses = _load_responses(
            session_id,
            candidate_id=candidate_id,
        )

        updated_answers = _normalize_saved_answers(
            responses["answers"],
            question_map,
        )

        # Validate all submitted answers before writing either file.
        for submitted_answer in request.answers:
            question_key = _normalize_question_id(
                submitted_answer.question_id
            )

            question = question_map.get(question_key)

            if question is None:
                logger.warning(
                    "Unassigned screening question submitted | "
                    "session_id=%s | question_id=%r",
                    session_id,
                    submitted_answer.question_id,
                )
                raise ScreeningQuestionError(
                    "Question is not assigned to this session."
                )

            normalized_answer = _validate_answer_against_question(
                submitted_answer,
                question,
            )

            canonical_id = _canonical_question_id(question)
            updated_answers[canonical_id] = {
                **normalized_answer,
                "question_id": canonical_id,
            }

        missing_mandatory: list[str] = []

        for question in question_map.values():
            if not _question_is_mandatory(question):
                continue

            canonical_id = _canonical_question_id(question)
            saved_answer = updated_answers.get(canonical_id)

            if not _saved_answer_is_answered(saved_answer):
                missing_mandatory.append(canonical_id)

        # Do not persist any changes when mandatory answers are missing
        # from a final submission.
        if request.final_submission and missing_mandatory:
            raise ScreeningMandatoryQuestionsError(
                missing_mandatory
            )

        now = _utc_now()

        responses["session_id"] = session_id
        responses["candidate_id"] = candidate_id
        responses["answers"] = updated_answers
        responses["updated_at"] = now

        if request.final_submission:
            session["status"] = ScreeningSessionStatus.SUBMITTED.value
            session["submitted_at"] = now
        else:
            session["status"] = ScreeningSessionStatus.IN_PROGRESS.value

        session["updated_at"] = now

        response_path = _response_path(session_id)
        session_path = _session_path(session_id)

        # Each file is written atomically. The two writes are not a
        # single transaction; use a database transaction for stronger
        # cross-record consistency in a multi-process deployment.
        _write_json_atomic(response_path, responses)
        _write_json_atomic(session_path, session)

        mandatory_count = sum(
            _question_is_mandatory(question)
            for question in question_map.values()
        )

        answered_mandatory_count = sum(
            _question_is_mandatory(question)
            and _saved_answer_is_answered(
                updated_answers.get(
                    _canonical_question_id(question)
                )
            )
            for question in question_map.values()
        )

        answered_count = sum(
            _saved_answer_is_answered(
                updated_answers.get(
                    _canonical_question_id(question)
                )
            )
            for question in question_map.values()
        )

        logger.info(
            "Screening responses saved | session_id=%s | "
            "candidate_id=%s | submitted_answers=%d | "
            "final_submission=%s",
            session_id,
            candidate_id,
            len(request.answers),
            request.final_submission,
        )

        # Never return answer text or scoring metadata.
        return {
            "success": True,
            "session_id": session_id,
            "candidate_id": candidate_id,
            "job_id": session["job_id"],
            "status": session["status"],
            "submitted_answers": len(request.answers),
            "total_questions": len(question_map),
            "answered_questions": answered_count,
            "mandatory_questions": mandatory_count,
            "answered_mandatory_questions": answered_mandatory_count,
            "unanswered_mandatory_questions": missing_mandatory,
            "updated_at": now,
        }


# ============================================================
# RETRIEVE SAVED RESPONSE STATUS
# ============================================================

def get_screening_responses(
    *,
    session_id: str,
    candidate_id: str,
) -> dict[str, Any]:
    """
    Return saved response status for the owning candidate.

    Answer text and selected option values are not returned.
    """
    session_id = _validate_identifier(
        session_id,
        "session_id",
    )
    candidate_id = _validate_identifier(
        candidate_id,
        "candidate_id",
    )

    with _STORAGE_LOCK:
        session = _load_session(session_id)

        if session["candidate_id"] != candidate_id:
            raise ScreeningOwnershipError(
                "Candidate does not own this screening session."
            )

        responses = _load_responses(
            session_id,
            candidate_id=candidate_id,
        )

        question_map = _build_question_map(session)

        saved_answers = _normalize_saved_answers(
            responses["answers"],
            question_map,
        )

        safe_answers = []

        for question in session["questions"]:
            question_id = _canonical_question_id(question)
            saved = saved_answers.get(question_id)

            safe_answers.append({
                "question_id": question_id,
                "answered": _saved_answer_is_answered(saved),
                "updated_at": (
                    saved.get("updated_at")
                    if saved
                    else None
                ),
            })

        return {
            "success": True,
            "session_id": session_id,
            "candidate_id": candidate_id,
            "status": session["status"],
            "total_questions": len(question_map),
            "answered_questions": sum(
                item["answered"] for item in safe_answers
            ),
            "answers": safe_answers,
        }
