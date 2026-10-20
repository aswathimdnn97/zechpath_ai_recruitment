
"""
screening_session_service.py

Responsibilities
----------------
1. Create a unique HR screening session.
2. Retrieve candidate-facing questions from question_bank_service.
3. Validate and normalize assigned question metadata.
4. Remove answer-key metadata from the session question snapshot.
5. Persist the session using an atomic JSON write.
6. Return the generated session_id and assigned questions.
7. Keep session creation separate from response submission.

Security note
-------------
The evaluation service must obtain objective answer keys from the
trusted question bank, not from the candidate-facing session snapshot.
"""

import json
import logging
import re
import secrets
import threading

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
}

# These fields must never be included in candidate-facing session questions.
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
    """Base exception for screening session operations."""


class ScreeningSessionValidationError(ScreeningSessionError):
    """Raised when session creation input is invalid."""


class ScreeningQuestionsUnavailableError(ScreeningSessionError):
    """Raised when no usable screening questions are available."""


class ScreeningSessionStorageError(ScreeningSessionError):
    """Raised when session persistence fails."""


# ============================================================
# HELPERS
# ============================================================

def _utc_now() -> str:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def _validate_required_string(value: Any, field_name: str) -> str:
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
    """Resolve a session path after validating its ID."""

    if not isinstance(session_id, str) or not SESSION_ID_PATTERN.fullmatch(
        session_id
    ):
        raise ScreeningSessionValidationError(
            "Invalid screening session ID format."
        )

    return SESSION_DIR / f"{session_id}.json"


def _write_json_atomic(
    path: Path,
    payload: dict[str, Any],
) -> None:
    """Persist JSON atomically to reduce partial-file risk."""

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
            logger.warning(
                "Unable to remove temporary session file."
            )

        raise ScreeningSessionStorageError(
            "Unable to save the screening session."
        ) from exc


def _normalize_answer_type(value: Any, question_id: str) -> str:
    """Normalize supported question answer types."""

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
    """Normalize mandatory metadata without treating strings as booleans."""

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
    """
    Recursively remove answer-key fields from candidate-facing data.

    This also handles sensitive metadata nested inside option dictionaries.
    """

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
    """
    Normalize supported question-bank result formats.

    Accepted formats:
    - A list of question dictionaries.
    - A dictionary containing a 'questions' list.
    """

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
# QUESTION RETRIEVAL
# ============================================================

def _get_questions(
    *,
    role_id: str,
    language: str,
    categories: list[str] | None,
    include_optional: bool,
) -> list[dict[str, Any]]:
    """Load, validate, sanitize, and deduplicate assigned questions."""

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
                        "Skipping a question without a valid question ID."
                    )
                    continue

                question_id = raw_question_id.strip()

                if question_id in seen_question_ids:
                    continue

                answer_type_value = question.get("answer_type")

                if not answer_type_value:
                    answer_type_value = question.get(
                        "question_type",
                        question.get("type"),
                    )

                answer_type = _normalize_answer_type(
                    answer_type_value,
                    question_id,
                )

                mandatory = _normalize_mandatory(question)

                # Strip answer keys and internal scoring information from
                # the persisted candidate-facing question snapshot.
                normalized_question = _sanitize_candidate_value(question)

                normalized_question["question_id"] = question_id
                normalized_question["answer_type"] = answer_type
                normalized_question["mandatory"] = mandatory

                # Normalize the common alias without deleting original
                # question text fields used by existing clients.
                if not normalized_question.get("question") and isinstance(
                    normalized_question.get("question_text"), str
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
    """
    Create and persist a screening session.

    Response submission is handled by screening_response_service.py.
    """

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

        # Validate categories, but preserve their original casing.
        normalized_categories = [
            _validate_required_string(category, "category")
            for category in categories
        ]

        # Deduplicate case-insensitively while preserving the first value.
        unique_categories = []
        seen_categories = set()

        for category in normalized_categories:
            category_key = category.casefold()

            if category_key not in seen_categories:
                seen_categories.add(category_key)
                unique_categories.append(category)

        categories = unique_categories



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
            1
            for question in questions
            if question["mandatory"]
        ),
        "created_at": created_at,
        "updated_at": created_at,
    }

    try:
        with _SESSION_LOCK:
            # A bounded retry avoids an infinite loop if ID generation
            # unexpectedly collides repeatedly.
            for _ in range(MAX_SESSION_ID_ATTEMPTS):
                session_id = _new_session_id()
                path = _session_path(session_id)

                if path.exists():
                    continue

                session["session_id"] = session_id
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

    logger.info(
        "Created HR screening session | session_id=%s | candidate_id=%s "
        "| job_id=%s | question_count=%s",
        session["session_id"],
        candidate_id,
        job_id,
        len(questions),
    )

    return session
