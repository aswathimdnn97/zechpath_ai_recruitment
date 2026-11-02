"""
screening_response_service.py

Responsibilities
----------------
1. Validate screening session existence and candidate ownership.
2. Load sessions and assigned questions from JSON or PostgreSQL.
3. Validate submitted answers against assigned question definitions.
4. Validate selected options and answer types.
5. Save and update candidate responses.
6. Track mandatory question completion.
7. Support draft and final submissions.
8. Prevent final submission when mandatory answers are missing.
9. Persist responses and update session status transactionally in PostgreSQL.
10. Preserve JSON storage compatibility.
11. Retrieve response status without exposing answer content.
12. Keep internal database IDs and filesystem paths out of API responses.

Security
--------
- A candidate can only submit responses to their own session.
- Answers must reference questions assigned to that session.
- Final submission is blocked when mandatory answers are missing.
- Candidate-facing response retrieval does not expose answer content.
- PostgreSQL response records are linked through session_questions.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

import psycopg2
from psycopg2.extras import Json, RealDictCursor

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
    """Raised when a session cannot accept responses."""


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
# STORAGE CONFIGURATION
# ============================================================

def _postgres_enabled() -> bool:
    """Determine the active storage backend dynamically."""
    return (
        os.getenv("ZECHPATH_STORAGE_BACKEND", "json")
        .strip()
        .lower()
        == "postgres"
    )


def _postgres_connection():
    """Create a PostgreSQL connection."""
    database_url = os.getenv("ZECHPATH_DATABASE_URL")

    if not database_url:
        raise ScreeningStorageError(
            "PostgreSQL database configuration is missing."
        )

    try:
        return psycopg2.connect(database_url)

    except psycopg2.Error as exc:
        logger.exception(
            "Unable to connect to the screening database."
        )
        raise ScreeningStorageError(
            "Unable to access screening data."
        ) from exc


# ============================================================
# COMMON HELPERS
# ============================================================

def _utc_now() -> str:
    """Return the current UTC timestamp as an ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _validate_identifier(value: Any, field: str) -> str:
    """Validate a session, candidate, or other identifier."""
    if not isinstance(value, str):
        raise ValueError(f"Invalid {field}.")

    value = value.strip()

    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid {field}.")

    return value


def _session_path(session_id: str) -> Path:
    """Return the JSON session path after validating its ID."""
    if not isinstance(session_id, str):
        raise ValueError("Invalid session_id.")

    session_id = session_id.strip()

    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError("Invalid session_id.")

    return SESSION_DIR / f"{session_id}.json"


def _response_path(session_id: str) -> Path:
    """Return the JSON response path after validating its ID."""
    if not isinstance(session_id, str):
        raise ValueError("Invalid session_id.")

    session_id = session_id.strip()

    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError("Invalid session_id.")

    return RESPONSE_DIR / f"{session_id}.json"


def _timestamp_to_string(value: Any) -> Any:
    """Convert database timestamps to ISO strings."""
    if isinstance(value, datetime):
        return value.isoformat()

    return value


def _normalize_question_id(value: Any) -> str:
    """Normalize a question ID for case-insensitive matching."""
    if not isinstance(value, str):
        return ""

    return value.strip().casefold()


def _canonical_question_id(
    question: dict[str, Any],
) -> str:
    """Get the canonical assigned question ID."""
    value = question.get(
        "question_id",
        question.get("id"),
    )

    if not isinstance(value, str) or not value.strip():
        raise ScreeningStorageError(
            "Assigned question has no valid identifier."
        )

    return value.strip()


# ============================================================
# JSON STORAGE HELPERS
# ============================================================

def _read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except FileNotFoundError:
        raise

    except (OSError, json.JSONDecodeError) as exc:
        logger.exception(
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
    """Write a JSON record atomically."""
    temporary_path: Path | None = None

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
            temporary_path = Path(file.name)

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )

            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, path)

    except (OSError, TypeError, ValueError) as exc:
        logger.exception(
            "Unable to persist screening data: %s",
            path.name,
        )
        raise ScreeningStorageError(
            "Unable to save screening responses."
        ) from exc

    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logger.warning(
                    "Unable to remove temporary screening file."
                )


# ============================================================
# LOAD SESSION: JSON
# ============================================================

def _load_session(session_id: str) -> dict[str, Any]:
    """Load a session from JSON storage."""
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
        _validate_identifier(
            session["candidate_id"],
            "candidate_id",
        )
        _validate_identifier(
            session["job_id"],
            "job_id",
        )

    except (TypeError, ValueError) as exc:
        raise ScreeningStorageError(
            "Screening session references are invalid."
        ) from exc

    return session


# ============================================================
# LOAD SESSION: POSTGRESQL
# ============================================================

def _load_session_postgres(
    session_id: str,
) -> dict[str, Any]:
    """
    Load a PostgreSQL session and its assigned questions.

    Question metadata is merged first. Database-controlled fields
    are then applied so metadata cannot override them.
    """
    try:
        with closing(_postgres_connection()) as conn:
            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:
                cur.execute(
                    """
                    SELECT
                        session_id,
                        candidate_id,
                        job_id,
                        role_id,
                        language,
                        status,
                        created_at,
                        updated_at,
                        submitted_at
                    FROM public.screening_sessions
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )

                row = cur.fetchone()

                if row is None:
                    raise ScreeningSessionNotFoundError(
                        "Screening session not found."
                    )

                session = dict(row)

                cur.execute(
                    """
                    SELECT
                        sq.question_id,
                        sq.is_mandatory,
                        sq.question_order,
                        q.role_id,
                        q.category,
                        q.language,
                        q.question_text,
                        q.question_type,
                        q.metadata
                    FROM public.session_questions AS sq
                    JOIN public.questions AS q
                      ON q.question_pk = sq.question_pk
                    WHERE sq.session_id = %s
                    ORDER BY sq.question_order
                    """,
                    (session_id,),
                )

                question_rows = cur.fetchall()

    except ScreeningResponseError:
        raise

    except psycopg2.Error as exc:
        logger.exception(
            "Failed to load PostgreSQL session: %s",
            session_id,
        )
        raise ScreeningStorageError(
            "Unable to read screening data."
        ) from exc

    questions: list[dict[str, Any]] = []

    for row in question_rows:
        metadata = row.get("metadata") or {}

        if not isinstance(metadata, dict):
            metadata = {}

        # Preserve candidate-facing options and other metadata.
        question = dict(metadata)

        # Database values remain authoritative.
        question.update({
            "question_id": str(row["question_id"]),
            "role_id": row["role_id"],
            "category": row["category"],
            "language": row["language"],
            "question_text": row["question_text"],
            "question": row["question_text"],
            "question_type": str(
                row["question_type"] or "TEXT"
            ).strip().upper(),
            "answer_type": str(
                row["question_type"] or "TEXT"
            ).strip().upper(),
            "mandatory": bool(row["is_mandatory"]),
            "is_mandatory": bool(row["is_mandatory"]),
            "question_order": row["question_order"],
        })

        questions.append(question)

    session["session_id"] = str(session["session_id"])
    session["candidate_id"] = str(session["candidate_id"])
    session["job_id"] = str(session["job_id"])
    session["status"] = str(session["status"]).upper()
    session["questions"] = questions
    session["total_questions"] = len(questions)
    session["mandatory_questions"] = sum(
        1 for question in questions
        if question["mandatory"]
    )

    for field in (
        "created_at",
        "updated_at",
        "submitted_at",
    ):
        session[field] = _timestamp_to_string(
            session.get(field)
        )

    return session


# ============================================================
# LOAD SESSION: BACKEND ROUTER
# ============================================================

def _load_session_for_backend(
    session_id: str,
) -> dict[str, Any]:
    """Load a session from the configured storage backend."""
    if _postgres_enabled():
        return _load_session_postgres(session_id)

    return _load_session(session_id)


# ============================================================
# LOAD RESPONSES: JSON
# ============================================================

def _load_responses(
    session_id: str,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    """
    Load JSON responses.

    An absent response file means the candidate has not saved
    any responses yet.
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
# LOAD RESPONSES: POSTGRESQL
# ============================================================

def _load_responses_postgres(
    session_id: str,
    candidate_id: str,
) -> dict[str, Any]:
    """
    Load saved responses using the actual database relationships.

    screening_responses has no question_id column. The assigned
    question ID is retrieved through session_questions.
    """
    try:
        with closing(_postgres_connection()) as conn:
            with conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:
                cur.execute(
                    """
                    SELECT
                        sq.question_id,
                        sr.answer_text,
                        sr.selected_option,
                        sr.answer_status,
                        sr.answer_data,
                        sr.updated_at
                    FROM public.screening_responses AS sr
                    JOIN public.session_questions AS sq
                      ON sq.session_question_id =
                         sr.session_question_id
                     AND sq.session_id = sr.session_id
                    WHERE sr.session_id = %s
                    ORDER BY sq.question_order
                    """,
                    (session_id,),
                )

                rows = cur.fetchall()

    except psycopg2.Error as exc:
        logger.exception(
            "Failed to load PostgreSQL responses: %s",
            session_id,
        )
        raise ScreeningStorageError(
            "Unable to read screening responses."
        ) from exc

    answers: dict[str, dict[str, Any]] = {}

    for row in rows:
        question_id = str(row["question_id"]).strip()

        answer_data = row.get("answer_data") or {}

        if not isinstance(answer_data, dict):
            answer_data = {}

        selected_option = row.get("selected_option") or []

        # The column may contain JSON data; normalize the expected
        # list format used by the existing validation service.
        if not isinstance(selected_option, list):
            selected_option = [selected_option]

        answer = {
            **answer_data,
            "question_id": question_id,
            "answer": row.get("answer_text"),
            "selected_options": selected_option,
            "updated_at": _timestamp_to_string(
                row.get("updated_at")
            ),
        }

        answers[question_id] = answer

    return {
        "session_id": session_id,
        "candidate_id": candidate_id,
        "answers": answers,
    }


def _load_responses_for_backend(
    session_id: str,
    candidate_id: str,
) -> dict[str, Any]:
    """Load responses from the configured backend."""
    if _postgres_enabled():
        return _load_responses_postgres(
            session_id,
            candidate_id,
        )

    return _load_responses(
        session_id,
        candidate_id=candidate_id,
    )


# ============================================================
# QUESTION VALIDATION HELPERS
# ============================================================

def _build_question_map(
    session: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build a normalized map of questions assigned to the session."""
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

    return question_map


def _normalize_saved_answers(
    answers: dict[str, Any],
    question_map: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Normalize saved answers and reject unassigned question IDs."""
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

        if (
            not normalized_qid
            or normalized_qid not in question_map
        ):
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
    """Resolve the mandatory flag."""
    for key in ("mandatory", "is_mandatory", "required"):
        if key in question:
            value = question[key]

            if not isinstance(value, bool):
                raise ScreeningStorageError(
                    "Invalid mandatory-question configuration."
                )

            return value

    return False


def _get_answer_type(
    question: dict[str, Any],
) -> str:
    """Resolve and validate a question's answer type."""
    answer_type = question.get(
        "answer_type",
        question.get(
            "question_type",
            question.get("type", "TEXT"),
        ),
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
    """Extract the allowed option IDs or values."""
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


# ============================================================
# ANSWER COMPLETENESS
# ============================================================

def _saved_answer_is_answered(answer: Any) -> bool:
    """Return whether a saved answer contains meaningful content."""
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

    if (
        isinstance(answer.get("currency"), str)
        and answer["currency"].strip()
        and answer.get("minimum_amount") is not None
        and answer.get("maximum_amount") is not None
    ):
        return True

    if answer.get("joining_date"):
        return True

    duration = answer.get("duration")

    if isinstance(duration, str) and duration.strip():
        return True

    return False


# ============================================================
# ANSWER VALIDATION
# ============================================================

def _validate_answer_against_question(
    answer: ScreeningAnswerSubmission,
    question: dict[str, Any],
) -> dict[str, Any]:
    """Validate an answer against the assigned question definition."""
    answer_type = _get_answer_type(question)

    text_answer = answer.answer
    selected_options = answer.selected_options
    details = answer.details

    if details is not None:
        details = details.strip() or None

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    if answer_type == "TEXT":
        if (
            not isinstance(text_answer, str)
            or not text_answer.strip()
        ):
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

    # --------------------------------------------------------
    # BOOLEAN / YES-NO
    # --------------------------------------------------------

    elif answer_type in {
        "BOOLEAN",
        "YES_NO_WITH_DETAILS",
    }:
        if (
            not isinstance(text_answer, str)
            or not text_answer.strip()
        ):
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
            "yes"
            if normalized in {"yes", "true"}
            else "no"
        )

        if answer_type == "BOOLEAN" and details:
            raise ScreeningAnswerError(
                "This boolean question does not accept additional details."
            )

    # --------------------------------------------------------
    # SINGLE / MULTIPLE CHOICE
    # --------------------------------------------------------

    elif answer_type in {
        "SINGLE_CHOICE",
        "MULTIPLE_CHOICE",
    }:
        if text_answer is not None or not selected_options:
            raise ScreeningAnswerError(
                "Provide selected options for this question."
            )

        if (
            answer_type == "SINGLE_CHOICE"
            and len(selected_options) != 1
        ):
            raise ScreeningAnswerError(
                "Select exactly one option for this question."
            )

    # --------------------------------------------------------
    # MULTI-SELECT WITH DETAILS
    # --------------------------------------------------------

    elif answer_type == "MULTI_SELECT_WITH_DETAILS":
        if not selected_options:
            raise ScreeningAnswerError(
                "Select at least one option for this question."
            )

        if text_answer is not None:
            raise ScreeningAnswerError(
                "Use selected_options for choices and details for explanation."
            )

    # --------------------------------------------------------
    # CURRENCY RANGE
    # --------------------------------------------------------

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

        currency = answer.currency.strip().upper()

        if (
            len(currency) != 3
            or not currency.isalpha()
        ):
            raise ScreeningAnswerError(
                "Currency must be a three-letter currency code."
            )

        if answer.minimum_amount < 0 or answer.maximum_amount < 0:
            raise ScreeningAnswerError(
                "Currency amounts cannot be negative."
            )

        if answer.maximum_amount < answer.minimum_amount:
            raise ScreeningAnswerError(
                "maximum_amount cannot be less than minimum_amount."
            )

    # --------------------------------------------------------
    # DATE OR DURATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VALIDATE SELECTED OPTIONS
    # --------------------------------------------------------

    if selected_options is not None:
        allowed_options = _get_option_values(question)

        normalized_options = []

        for option in selected_options:
            if not isinstance(option, str) or not option.strip():
                raise ScreeningAnswerError(
                    "Selected options cannot be empty."
                )

            normalized_options.append(option.strip())

        normalized_keys = [
            option.casefold()
            for option in normalized_options
        ]

        if len(normalized_keys) != len(set(normalized_keys)):
            raise ScreeningAnswerError(
                "Duplicate selected options are not allowed."
            )

        if any(
            option not in allowed_options
            for option in normalized_keys
        ):
            raise ScreeningAnswerError(
                "One or more selected options are invalid."
            )

        selected_options = normalized_options

    return {
        "question_id": _canonical_question_id(question),
        "answer": text_answer,
        "selected_options": selected_options,
        "details": details,
        "currency": (
            answer.currency.strip().upper()
            if answer.currency is not None
            else None
        ),
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


def _attach_semantic_classification(
    normalized_answer: dict[str, Any],
    question: dict[str, Any],
    session: dict[str, Any],
) -> dict[str, Any]:
    """
    Attach semantic classification to eligible text answers.
    Structured choice and numeric answers are not classified here.
    """
    from api.service.intent_classification_service import (
        classify_candidate_answer,
    )

    answer_type = str(
        question.get(
            "answer_type",
            question.get("question_type", "TEXT"),
        )
    ).strip().upper()

    if answer_type not in {"TEXT", "YES_NO_WITH_DETAILS"}:
        return normalized_answer

    answer_text = normalized_answer.get("answer")

    if not isinstance(answer_text, str) or not answer_text.strip():
        return normalized_answer

    question_text = (
        question.get("question_text")
        or question.get("question")
        or ""
    )

    if not isinstance(question_text, str) or not question_text.strip():
        return normalized_answer

    language = session.get("language", "en")

    classification = classify_candidate_answer(
        question_text=question_text,
        answer_text=answer_text,
        language=language,
    )

    normalized_answer["semantic_classification"] = classification

    return normalized_answer
# ============================================================
# POSTGRESQL RESPONSE PERSISTENCE
# ============================================================

def _save_responses_postgres(
    *,
    session_id: str,
    candidate_id: str,
    answers: dict[str, dict[str, Any]],
    final_submission: bool,
) -> tuple[str, str]:
    """
    Persist answers and update the session in one transaction.

    Returns:
        (new_status, updated_at)
    """
    now_dt = datetime.now(timezone.utc)
    now_str = now_dt.isoformat()

    new_status = (
        ScreeningSessionStatus.SUBMITTED.value
        if final_submission
        else ScreeningSessionStatus.IN_PROGRESS.value
    )

    try:
        with closing(_postgres_connection()) as conn:
            with conn:
                with conn.cursor(
                    cursor_factory=RealDictCursor
                ) as cur:

                    # Lock the session and recheck ownership/status
                    # inside the transaction.
                    cur.execute(
                        """
                        SELECT candidate_id, status
                        FROM public.screening_sessions
                        WHERE session_id = %s
                        FOR UPDATE
                        """,
                        (session_id,),
                    )

                    session_row = cur.fetchone()

                    if session_row is None:
                        raise ScreeningSessionNotFoundError(
                            "Screening session not found."
                        )

                    if (
                        str(session_row["candidate_id"])
                        != candidate_id
                    ):
                        raise ScreeningOwnershipError(
                            "Candidate does not own this screening session."
                        )

                    current_status = str(
                        session_row["status"]
                    ).upper()

                    if current_status not in ALLOWED_SESSION_STATUSES:
                        raise ScreeningSessionStateError(
                            "This screening session cannot accept responses."
                        )

                    cur.execute(
                        """
                        SELECT
                            session_question_id,
                            question_id
                        FROM public.session_questions
                        WHERE session_id = %s
                        """,
                        (session_id,),
                    )

                    assignments = {
                        str(row["question_id"]).strip().casefold():
                        row["session_question_id"]
                        for row in cur.fetchall()
                    }

                    for question_id, answer_data in answers.items():
                        assignment_id = assignments.get(
                            question_id.strip().casefold()
                        )

                        if assignment_id is None:
                            raise ScreeningQuestionError(
                                "Question is not assigned to this session."
                            )

                        answer_text = answer_data.get("answer")
                        selected_options = (
                            answer_data.get("selected_options") or []
                        )

                        answer_status = (
                            "SUBMITTED"
                            if final_submission
                            else "DRAFT"
                        )

                        submitted_at = (
                            now_dt
                            if final_submission
                            else None
                        )

                        cur.execute(
                            """
                            INSERT INTO public.screening_responses (
                                session_question_id,
                                session_id,
                                answer_text,
                                selected_option,
                                answer_status,
                                submitted_at,
                                created_at,
                                updated_at,
                                answer_data
                            )
                            VALUES (
                                %s, %s, %s, %s, %s,
                                %s, %s, %s, %s
                            )
                            ON CONFLICT (session_question_id)
                            DO UPDATE SET
                                answer_text = EXCLUDED.answer_text,
                                selected_option = EXCLUDED.selected_option,
                                answer_status = EXCLUDED.answer_status,
                                submitted_at = EXCLUDED.submitted_at,
                                updated_at = EXCLUDED.updated_at,
                                answer_data = EXCLUDED.answer_data
                            """,
                            (
                                assignment_id,
                                session_id,
                                answer_text,
                                Json(selected_options),
                                answer_status,
                                submitted_at,
                                now_dt,
                                now_dt,
                                Json(answer_data),
                            ),
                        )

                    cur.execute(
                        """
                        UPDATE public.screening_sessions
                        SET
                            status = %s,
                            updated_at = %s,
                            submitted_at = CASE
                                WHEN %s THEN %s
                                ELSE submitted_at
                            END
                        WHERE session_id = %s
                        """,
                        (
                            new_status,
                            now_dt,
                            final_submission,
                            now_dt if final_submission else None,
                            session_id,
                        ),
                    )

    except ScreeningResponseError:
        raise

    except psycopg2.Error as exc:
        logger.exception(
            "Failed to save PostgreSQL responses | session_id=%s",
            session_id,
        )
        raise ScreeningStorageError(
            "Unable to save screening responses."
        ) from exc

    return new_status, now_str


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
    Save candidate answers.

    Draft:
        - Save submitted answers.
        - Preserve previously saved answers.
        - Set session status to IN_PROGRESS.

    Final:
        - Validate all mandatory answers.
        - Save all merged answers.
        - Set response status and session status to SUBMITTED.

    PostgreSQL writes occur in one database transaction.
    JSON mode continues to use atomic file writes.
    """
    session_id = _validate_identifier(
        session_id,
        "session_id",
    )
    candidate_id = _validate_identifier(
        candidate_id,
        "candidate_id",
    )

    if not isinstance(
        request,
        ScreeningResponseSubmissionRequest,
    ):
        raise ValueError(
            "Invalid screening response request."
        )

    with _STORAGE_LOCK:
        session = _load_session_for_backend(session_id)

        if session["candidate_id"] != candidate_id:
            raise ScreeningOwnershipError(
                "Candidate does not own this screening session."
            )

        session_status = str(session["status"]).upper()

        if session_status not in ALLOWED_SESSION_STATUSES:
            raise ScreeningSessionStateError(
                "This screening session cannot accept responses."
            )

        question_map = _build_question_map(session)

        responses = _load_responses_for_backend(
            session_id,
            candidate_id,
        )

        updated_answers = _normalize_saved_answers(
            responses["answers"],
            question_map,
        )
        
        # Validate every submitted answer before persistence.
        for submitted_answer in request.answers:
            question_key = _normalize_question_id(
                submitted_answer.question_id
            )

            question = question_map.get(question_key)

            if question is None:
                raise ScreeningQuestionError(
                    "Question is not assigned to this session."
                )

            normalized_answer = _validate_answer_against_question(
                submitted_answer,
                question,
            )
            
            normalized_answer = _attach_semantic_classification(
                normalized_answer=normalized_answer,
                question=question,
                session=session,
            )

            canonical_id = _canonical_question_id(question)

            updated_answers[canonical_id] = {
                **normalized_answer,
                "question_id": canonical_id,
            }

        # Check mandatory answers against the merged saved answers.
        missing_mandatory: list[str] = []

        for question in question_map.values():
            if not _question_is_mandatory(question):
                continue

            canonical_id = _canonical_question_id(question)
            saved_answer = updated_answers.get(canonical_id)

            if not _saved_answer_is_answered(saved_answer):
                missing_mandatory.append(canonical_id)

        # No writes occur if a final submission is incomplete.
        if request.final_submission and missing_mandatory:
            raise ScreeningMandatoryQuestionsError(
                missing_mandatory
            )
        logger.info(
            "ACTIVE STORAGE BACKEND: %s",
            "postgres" if _postgres_enabled() else "json",
        )
        # ----------------------------------------------------
        # POSTGRESQL PERSISTENCE
        # ----------------------------------------------------

        if _postgres_enabled():
            new_status, now = _save_responses_postgres(
                session_id=session_id,
                candidate_id=candidate_id,
                answers=updated_answers,
                final_submission=request.final_submission,
            )

        # ----------------------------------------------------
        # JSON PERSISTENCE
        # ----------------------------------------------------

        else:
            now = _utc_now()

            responses["session_id"] = session_id
            responses["candidate_id"] = candidate_id
            responses["answers"] = updated_answers
            responses["updated_at"] = now

            if request.final_submission:
                session["status"] = (
                    ScreeningSessionStatus.SUBMITTED.value
                )
                session["submitted_at"] = now
            else:
                session["status"] = (
                    ScreeningSessionStatus.IN_PROGRESS.value
                )

            session["updated_at"] = now

            _write_json_atomic(
                _response_path(session_id),
                responses,
            )

            _write_json_atomic(
                _session_path(session_id),
                session,
            )

            new_status = session["status"]

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        mandatory_count = sum(
            1
            for question in question_map.values()
            if _question_is_mandatory(question)
        )

        answered_mandatory_count = sum(
            1
            for question in question_map.values()
            if (
                _question_is_mandatory(question)
                and _saved_answer_is_answered(
                    updated_answers.get(
                        _canonical_question_id(question)
                    )
                )
            )
        )

        answered_count = sum(
            1
            for question in question_map.values()
            if _saved_answer_is_answered(
                updated_answers.get(
                    _canonical_question_id(question)
                )
            )
        )

        logger.info(
            "Screening responses saved | session_id=%s | "
            "candidate_id=%s | submitted_answers=%d | "
            "final_submission=%s | backend=%s",
            session_id,
            candidate_id,
            len(request.answers),
            request.final_submission,
            "postgres" if _postgres_enabled() else "json",
        )

        # Do not return candidate answer content.
        return {
            "success": True,
            "session_id": session_id,
            "candidate_id": candidate_id,
            "job_id": session["job_id"],
            "status": new_status,
            "submitted_answers": len(request.answers),
            "total_questions": len(question_map),
            "answered_questions": answered_count,
            "mandatory_questions": mandatory_count,
            "answered_mandatory_questions": (
                answered_mandatory_count
            ),
            "unanswered_mandatory_questions": (
                missing_mandatory
            ),
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
    Return response status for the owning candidate.

    The returned answers contain question IDs, answered flags,
    and timestamps only. Answer text is not exposed.
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
        session = _load_session_for_backend(session_id)

        if session["candidate_id"] != candidate_id:
            raise ScreeningOwnershipError(
                "Candidate does not own this screening session."
            )

        responses = _load_responses_for_backend(
            session_id,
            candidate_id,
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
                1 for item in safe_answers
                if item["answered"]
            ),
            "answers": safe_answers,
        }