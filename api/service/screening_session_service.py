
"""
screening_session_service.py

Responsibilities
----------------
1. Create a unique HR screening session.
2. Retrieve candidate-facing questions from JSON question-bank service
   or PostgreSQL, depending on the configured backend.
3. Validate and normalize assigned question metadata.
4. Remove answer-key metadata from candidate-facing question snapshots.
5. Persist sessions atomically in JSON mode or transactionally in PostgreSQL.
6. Assign questions through session_questions in PostgreSQL mode.
7. Retrieve sessions from the configured storage backend.
8. Keep session creation separate from response submission.

Security note
-------------
The evaluation service must obtain objective answer keys from the
trusted question bank, not from the candidate-facing session snapshot.
"""

import json
import logging
import os
import re
import secrets
import threading

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from api.service.question_bank_service import get_candidate_questions


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCREENING_DATA_DIR = PROJECT_ROOT / "data" / "hr_screening"
SESSION_DIR = SCREENING_DATA_DIR / "sessions"

SESSION_ID_PATTERN = re.compile(r"^SCREEN_[A-F0-9]{12}$")

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

SENSITIVE_ANSWER_KEYS = {
    "correct",
    "correct_answer",
    "correct_answers",
    "correct_option",
    "correct_options",
    "correct_option_id",
    "correct_option_ids",
    "expected_answer",
    "expected_answers",
    "answer_key",
    "answer_keys",
    "is_correct",
    "answer_explanation",
    "evaluation_rubric",
    "scoring_rubric",
}

MAX_SESSION_ID_ATTEMPTS = 10

_SESSION_LOCK = threading.RLock()


# ============================================================
# EXCEPTIONS
# ============================================================

class ScreeningSessionError(Exception):
    """Base exception for session operations."""


class ScreeningSessionValidationError(ScreeningSessionError):
    """Raised when session input is invalid."""


class ScreeningQuestionsUnavailableError(ScreeningSessionError):
    """Raised when no usable screening questions are available."""


class ScreeningSessionStorageError(ScreeningSessionError):
    """Raised when session persistence or retrieval fails."""


class ScreeningSessionNotFoundError(ScreeningSessionError):
    """Raised when the requested session does not exist."""


# ============================================================
# STORAGE CONFIGURATION
# ============================================================

def _postgres_enabled() -> bool:
    """Read the backend setting dynamically."""

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
        raise ScreeningSessionStorageError(
            "ZECHPATH_DATABASE_URL is not configured."
        )

    try:
        return psycopg2.connect(database_url)

    except psycopg2.Error as exc:
        logger.exception("Unable to connect to PostgreSQL.")
        raise ScreeningSessionStorageError(
            "Unable to connect to screening storage."
        ) from exc


# ============================================================
# COMMON HELPERS
# ============================================================

def _utc_now() -> str:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def _timestamp_to_string(value: Any) -> Any:
    """Convert database timestamps to ISO strings."""

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def _validate_required_string(
    value: Any,
    field_name: str,
) -> str:
    """Validate and normalize a required string."""

    if not isinstance(value, str) or not value.strip():
        raise ScreeningSessionValidationError(
            f"{field_name} must be a non-empty string."
        )

    return value.strip()


def _new_session_id() -> str:
    """Generate a session ID in the supported format."""

    return f"SCREEN_{secrets.token_hex(6).upper()}"


def _session_path(session_id: str) -> Path:
    """Resolve a JSON session path after validating its ID."""

    if (
        not isinstance(session_id, str)
        or not SESSION_ID_PATTERN.fullmatch(session_id)
    ):
        raise ScreeningSessionValidationError(
            "Invalid screening session ID format."
        )

    return SESSION_DIR / f"{session_id}.json"


def _write_json_atomic(
    path: Path,
    payload: dict[str, Any],
) -> None:
    """Write JSON atomically."""

    temporary_path = path.with_name(
        f".{path.stem}.{secrets.token_hex(4)}.tmp"
    )

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with temporary_path.open("x", encoding="utf-8") as file:
            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            file.write("\n")

        temporary_path.replace(path)

    except (OSError, TypeError, ValueError) as exc:
        logger.exception("Failed to persist screening session.")

        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Unable to remove temporary session file.")

        raise ScreeningSessionStorageError(
            "Unable to save the screening session."
        ) from exc


def _normalize_answer_type(
    value: Any,
    question_id: str,
) -> str:
    """Validate supported question types."""

    if not isinstance(value, str) or not value.strip():
        raise ScreeningQuestionsUnavailableError(
            f"Question '{question_id}' has no valid answer type."
        )

    answer_type = value.strip().upper()

    if answer_type not in SUPPORTED_ANSWER_TYPES:
        raise ScreeningQuestionsUnavailableError(
            f"Question '{question_id}' has an unsupported answer type."
        )

    return answer_type


def _normalize_mandatory(question: dict[str, Any]) -> bool:
    """Normalize mandatory metadata."""

    value = question.get(
        "mandatory",
        question.get("is_mandatory", True),
    )

    if not isinstance(value, bool):
        raise ScreeningQuestionsUnavailableError(
            "Question mandatory metadata must be a boolean."
        )

    return value


def _sanitize_candidate_value(value: Any) -> Any:
    """Recursively remove sensitive answer-key fields."""

    if isinstance(value, dict):
        sanitized = {}

        for key, nested_value in value.items():
            normalized_key = str(key).strip().lower()

            if normalized_key in SENSITIVE_ANSWER_KEYS:
                continue

            sanitized[key] = _sanitize_candidate_value(nested_value)

        return sanitized

    if isinstance(value, list):
        return [
            _sanitize_candidate_value(item)
            for item in value
        ]

    return value


def _extract_question_list(result: Any) -> list[dict[str, Any]]:
    """Normalize supported question-bank result formats."""

    if isinstance(result, dict):
        result = result.get("questions")

    if not isinstance(result, list):
        raise ScreeningQuestionsUnavailableError(
            "The question bank returned an invalid question collection."
        )

    return [
        item for item in result
        if isinstance(item, dict)
    ]


# ============================================================
# JSON QUESTION RETRIEVAL
# ============================================================

def _get_questions(
    *,
    role_id: str,
    language: str,
    categories: list[str] | None,
    include_optional: bool,
) -> list[dict[str, Any]]:
    """Load questions through the existing question-bank service."""

    selected_questions: list[dict[str, Any]] = []
    seen_question_ids: set[str] = set()

    requested_categories = categories or [None]

    try:
        for category in requested_categories:
            result = get_candidate_questions(
                role_id=role_id,
                language=language,
                category=category,
                include_optional=include_optional,
            )

            questions = _extract_question_list(result)

            for question in questions:
                raw_question_id = question.get(
                    "question_id",
                    question.get("id"),
                )

                if (
                    not isinstance(raw_question_id, str)
                    or not raw_question_id.strip()
                ):
                    logger.warning(
                        "Skipping question without a valid question ID."
                    )
                    continue

                question_id = raw_question_id.strip()

                if question_id in seen_question_ids:
                    continue

                answer_type_value = (
                    question.get("answer_type")
                    or question.get("question_type")
                    or question.get("type")
                )

                answer_type = _normalize_answer_type(
                    answer_type_value,
                    question_id,
                )

                mandatory = _normalize_mandatory(question)

                normalized_question = _sanitize_candidate_value(
                    question
                )

                normalized_question["question_id"] = question_id
                normalized_question["answer_type"] = answer_type
                normalized_question["mandatory"] = mandatory

                if (
                    not normalized_question.get("question")
                    and isinstance(
                        normalized_question.get("question_text"),
                        str,
                    )
                ):
                    normalized_question["question"] = (
                        normalized_question["question_text"]
                    )

                seen_question_ids.add(question_id)
                selected_questions.append(normalized_question)

    except ScreeningSessionError:
        raise

    except Exception as exc:
        logger.exception(
            "Question-bank retrieval failed | role_id=%s | language=%s",
            role_id,
            language,
        )
        raise ScreeningQuestionsUnavailableError(
            "Unable to retrieve screening questions."
        ) from exc

    if not selected_questions:
        raise ScreeningQuestionsUnavailableError(
            "No screening questions are available for the selected role."
        )

    return selected_questions


# ============================================================
# POSTGRESQL QUESTION RETRIEVAL
# ============================================================

def _get_questions_from_postgres(
    *,
    role_id: str,
    language: str,
    categories: list[str] | None,
    include_optional: bool,
) -> list[dict[str, Any]]:
    """Retrieve active questions and their database primary keys."""

    sql = """
        SELECT
            question_pk,
            question_id,
            role_id,
            category,
            language,
            question_text,
            question_type,
            is_mandatory,
            metadata
        FROM public.questions
        WHERE role_id = %s
          AND language = %s
          AND is_active = TRUE
          AND (%s = TRUE OR is_mandatory = TRUE)
          AND (
              %s::text[] IS NULL
              OR UPPER(category) = ANY(%s::text[])
          )
        ORDER BY category, question_id
    """

    normalized_categories = (
        [category.upper() for category in categories]
        if categories
        else None
    )

    try:
        with closing(_postgres_connection()) as connection:
            with connection.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:
                cursor.execute(
                    sql,
                    (
                        role_id,
                        language,
                        include_optional,
                        normalized_categories,
                        normalized_categories,
                    ),
                )
                rows = cursor.fetchall()

    except ScreeningSessionStorageError:
        raise

    except psycopg2.Error as exc:
        logger.exception("Unable to retrieve PostgreSQL questions.")
        raise ScreeningQuestionsUnavailableError(
            "Unable to retrieve screening questions."
        ) from exc

    questions: list[dict[str, Any]] = []
    seen_question_ids: set[str] = set()

    for row in rows:
        question_id = row["question_id"]

        if question_id in seen_question_ids:
            continue

        metadata = row.get("metadata") or {}

        if not isinstance(metadata, dict):
            logger.warning(
                "Skipping invalid metadata for question %s.",
                question_id,
            )
            metadata = {}

        # Preserve candidate-facing metadata such as options, if present.
        question = dict(metadata)

        question.update({
            "question_id": question_id,
            "role_id": row["role_id"],
            "category": row["category"],
            "language": row["language"],
            "question_text": row["question_text"],
            "question": row["question_text"],
            "question_type": row["question_type"],
            "answer_type": _normalize_answer_type(
                row["question_type"],
                question_id,
            ),
            "is_mandatory": row["is_mandatory"],
            "mandatory": row["is_mandatory"],
            "_question_pk": row["question_pk"],
        })

        question = _sanitize_candidate_value(question)

        # Restore the internal key after sanitization; this key is used
        # only for database assignment and is removed before returning.
        question["_question_pk"] = row["question_pk"]

        seen_question_ids.add(question_id)
        questions.append(question)

    if not questions:
        raise ScreeningQuestionsUnavailableError(
            "No screening questions are available for the selected role "
            "and language."
        )

    return questions


# ============================================================
# POSTGRESQL SESSION PERSISTENCE
# ============================================================

def _create_postgres_session(
    session: dict[str, Any],
) -> None:
    """Insert a session and all its question assignments in one transaction."""

    try:
        with closing(_postgres_connection()) as connection:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO public.screening_sessions (
                            session_id,
                            candidate_id,
                            job_id,
                            role_id,
                            language,
                            status,
                            created_at,
                            updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            session["session_id"],
                            session["candidate_id"],
                            session["job_id"],
                            session["role_id"],
                            session["language"],
                            session["status"],
                            session["created_at"],
                            session["updated_at"],
                        ),
                    )

                    for order, question in enumerate(
                        session["questions"],
                        start=1,
                    ):
                        cursor.execute(
                            """
                            INSERT INTO public.session_questions (
                                session_id,
                                question_id,
                                question_order,
                                is_mandatory,
                                question_pk
                            )
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (
                                session["session_id"],
                                question["question_id"],
                                order,
                                question["mandatory"],
                                question["_question_pk"],
                            ),
                        )

    except ScreeningSessionStorageError:
        raise

    except psycopg2.Error as exc:
        logger.exception(
            "Unable to persist PostgreSQL session | session_id=%s",
            session.get("session_id"),
        )
        raise ScreeningSessionStorageError(
            "Unable to save the screening session."
        ) from exc


# ============================================================
# CREATE SCREENING SESSION
# ============================================================

def create_screening_session(
    *,
    candidate_id: str,
    job_id: str,
    role_id: str,
    language: str = "en",
    categories: list[str] | None = None,
    include_optional: bool = False,
) -> dict[str, Any]:
    """Create a session using the configured storage backend."""

    candidate_id = _validate_required_string(
        candidate_id,
        "candidate_id",
    )
    job_id = _validate_required_string(job_id, "job_id")
    role_id = _validate_required_string(role_id, "role_id")
    language = _validate_required_string(language, "language").lower()

    if not isinstance(include_optional, bool):
        raise ScreeningSessionValidationError(
            "include_optional must be a boolean."
        )

    if categories is not None:
        if not isinstance(categories, list) or not categories:
            raise ScreeningSessionValidationError(
                "categories must be a non-empty list when provided."
            )

        normalized_categories = [
            _validate_required_string(category, "category")
            for category in categories
        ]

        unique_categories = []
        seen_categories = set()

        for category in normalized_categories:
            category_key = category.casefold()

            if category_key not in seen_categories:
                seen_categories.add(category_key)
                unique_categories.append(category)

        categories = unique_categories

    if _postgres_enabled():
        questions = _get_questions_from_postgres(
            role_id=role_id,
            language=language,
            categories=categories,
            include_optional=include_optional,
        )
    else:
        questions = _get_questions(
            role_id=role_id,
            language=language,
            categories=categories,
            include_optional=include_optional,
        )

    created_at = _utc_now()

    session = {
        "session_id": None,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "role_id": role_id,
        "language": language,
        "status": "CREATED",
        "questions": questions,
        "total_questions": len(questions),
        "mandatory_questions": sum(
            1 for question in questions
            if question["mandatory"]
        ),
        "created_at": created_at,
        "updated_at": created_at,
    }

    try:
        with _SESSION_LOCK:
            for _ in range(MAX_SESSION_ID_ATTEMPTS):
                session_id = _new_session_id()
                path = _session_path(session_id)

                if path.exists():
                    continue

                session["session_id"] = session_id

                if _postgres_enabled():
                    _create_postgres_session(session)
                else:
                    _write_json_atomic(path, session)

                break

            else:
                raise ScreeningSessionStorageError(
                    "Unable to allocate a unique screening session ID."
                )

    except ScreeningSessionStorageError:
        raise

    except OSError as exc:
        logger.exception("Failed to create screening session.")
        raise ScreeningSessionStorageError(
            "Unable to create the screening session."
        ) from exc

    # Do not expose internal PostgreSQL primary keys to the candidate.
    for question in session["questions"]:
        question.pop("_question_pk", None)

    logger.info(
        "Created HR screening session | session_id=%s | candidate_id=%s "
        "| job_id=%s | question_count=%s | backend=%s",
        session["session_id"],
        candidate_id,
        job_id,
        len(questions),
        "postgres" if _postgres_enabled() else "json",
    )

    return session


# ============================================================
# GET POSTGRESQL SCREENING SESSION
# ============================================================

def _get_postgres_screening_session(
    session_id: str,
) -> dict[str, Any]:
    """Load a session and its assigned questions from PostgreSQL."""

    try:
        with closing(_postgres_connection()) as connection:
            with connection.cursor(
                cursor_factory=RealDictCursor
            ) as cursor:
                cursor.execute(
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
                        started_at,
                        submitted_at
                    FROM public.screening_sessions
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )

                row = cursor.fetchone()

                if row is None:
                    raise ScreeningSessionNotFoundError(
                        "Screening session was not found."
                    )

                session = dict(row)

                cursor.execute(
                    """
                    SELECT
                        sq.question_pk,
                        sq.question_id,
                        sq.question_order,
                        sq.is_mandatory,
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

                question_rows = cursor.fetchall()

    except ScreeningSessionNotFoundError:
        raise

    except ScreeningSessionStorageError:
        raise

    except psycopg2.Error as exc:
        logger.exception(
            "Unable to retrieve PostgreSQL session | session_id=%s",
            session_id,
        )
        raise ScreeningSessionStorageError(
            "Unable to read the screening session."
        ) from exc

    questions = []

    for row in question_rows:
        metadata = row.get("metadata") or {}

        if not isinstance(metadata, dict):
            metadata = {}

        question = dict(metadata)

        question.update({
            "question_id": row["question_id"],
            "role_id": row["role_id"],
            "category": row["category"],
            "language": row["language"],
            "question_text": row["question_text"],
            "question": row["question_text"],
            "question_type": row["question_type"],
            "answer_type": _normalize_answer_type(
                row["question_type"],
                row["question_id"],
            ),
            "is_mandatory": row["is_mandatory"],
            "mandatory": row["is_mandatory"],
            "question_order": row["question_order"],
        })

        questions.append(_sanitize_candidate_value(question))

    session["questions"] = questions
    session["total_questions"] = len(questions)
    session["mandatory_questions"] = sum(
        1 for question in questions
        if question.get("mandatory") is True
    )

    for field in (
        "created_at",
        "updated_at",
        "started_at",
        "submitted_at",
    ):
        session[field] = _timestamp_to_string(session.get(field))

    return session


# ============================================================
# GET SCREENING SESSION
# ============================================================

def get_screening_session(session_id: str) -> dict[str, Any]:
    """Retrieve a session from the configured backend."""

    # Validate the ID format in either storage mode.
    _session_path(session_id)

    if _postgres_enabled():
        return _get_postgres_screening_session(session_id)

    path = _session_path(session_id)

    try:
        with path.open("r", encoding="utf-8") as file:
            session = json.load(file)

    except FileNotFoundError as exc:
        raise ScreeningSessionNotFoundError(
            "Screening session was not found."
        ) from exc

    except (OSError, json.JSONDecodeError) as exc:
        logger.exception(
            "Unable to read screening session | session_id=%s",
            session_id,
        )
        raise ScreeningSessionStorageError(
            "Unable to read the screening session."
        ) from exc

    if not isinstance(session, dict):
        raise ScreeningSessionStorageError(
            "Stored screening session has an invalid format."
        )

    if session.get("session_id") != session_id:
        raise ScreeningSessionStorageError(
            "Stored screening session ID does not match its filename."
        )

    if not isinstance(session.get("questions"), list):
        raise ScreeningSessionStorageError(
            "Stored screening session has invalid question data."
        )

    return session
