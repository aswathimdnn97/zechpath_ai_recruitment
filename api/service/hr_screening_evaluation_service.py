
"""
HR screening evaluation service for ZechPath.

Responsibilities
-----------------
1. Evaluate only submitted screening sessions.
2. Validate session, response, and assigned-question data.
3. Resolve trusted evaluation configuration from question_bank.json.
4. Keep HUMAN_REVIEW questions out of automatic scoring.
5. Support explicit objective answer keys.
6. Support configured keyword rubrics and injected evaluators.
7. Keep RULE_BASED questions in review until a rule evaluator is configured.
8. Validate all scores before aggregation.
9. Track mandatory unanswered questions and review requirements.
10. Save independent evaluation reports atomically.
11. Cache reports only when inputs match and no custom evaluator is supplied.
12. Never automatically reject a candidate.

Storage
-------
data/hr_screening/sessions/{session_id}.json
data/hr_screening/responses/{session_id}.json
data/hr_screening/evaluations/{session_id}.json
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from api.service.answer_evaluator import (
    AnswerEvaluationError,
    evaluate_answer,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

HR_SCREENING_DIR = PROJECT_ROOT / "data" / "hr_screening"
SESSIONS_DIR = HR_SCREENING_DIR / "sessions"
RESPONSES_DIR = HR_SCREENING_DIR / "responses"
EVALUATIONS_DIR = HR_SCREENING_DIR / "evaluations"
QUESTION_BANK_PATH = HR_SCREENING_DIR / "question_bank.json"

EVALUATION_VERSION = "1.1"
SESSION_ID_PATTERN = re.compile(r"^SCREEN_[A-Za-z0-9_-]{1,100}$")
MAX_FEEDBACK_LENGTH = 2000

TRUSTED_EVALUATION_FIELDS = (
    "evaluation_type",
    "correct_option_ids",
    "correct_options",
    "expected_answer",
    "correct_answer",
    "accepted_answers",
    "correct_answers",
    "answer_key",
    "evaluation_criteria",
    "rubric",
    "rules",
    "rule_config",
    "max_score",
    "points",
    "score_weight",
    "answer_type",
    "question_type",
    "type",
    "scoring_importance",
    "version",
)


class ScreeningEvaluationError(Exception):
    """Base exception for screening evaluation errors."""


class ScreeningSessionNotFoundError(ScreeningEvaluationError):
    """Raised when a screening session does not exist."""


class ScreeningResponseNotFoundError(ScreeningEvaluationError):
    """Raised when submitted responses do not exist."""


class InvalidScreeningStateError(ScreeningEvaluationError):
    """Raised when a session is not ready for evaluation."""


class ScreeningDataError(ScreeningEvaluationError):
    """Raised when stored screening data is invalid."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    """Read and validate a JSON object."""
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        raise ScreeningDataError(
            f"Unable to read valid JSON from {path.name}."
        ) from exc

    if not isinstance(data, dict):
        raise ScreeningDataError(
            f"Expected a JSON object in {path.name}."
        )

    return data


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Persist a JSON object atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")

        temporary_path.replace(path)

    except OSError as exc:
        temporary_path.unlink(missing_ok=True)
        raise ScreeningEvaluationError(
            f"Unable to save evaluation report: {path.name}."
        ) from exc


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    return re.sub(r"\s+", " ", value).strip().casefold()


def _is_mandatory(question: dict[str, Any]) -> bool:
    value = question.get(
        "mandatory",
        question.get("is_mandatory", question.get("required", False)),
    )
    return value is True


def _question_id(question: dict[str, Any]) -> Optional[str]:
    value = question.get("question_id", question.get("id"))

    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


def _answer_text(answer: dict[str, Any]) -> str:
    value = answer.get(
        "answer",
        answer.get("text_answer", answer.get("response", "")),
    )

    return value.strip() if isinstance(value, str) else ""


def _answer_options(answer: dict[str, Any]) -> list[str]:
    value = answer.get(
        "selected_options",
        answer.get(
            "selected_option_ids",
            answer.get("selected_option"),
        ),
    )

    if value is None:
        return []

    if isinstance(value, (str, int, float)) and not isinstance(value, bool):
        normalized = str(value).strip()
        return [normalized] if normalized else []

    if isinstance(value, (list, tuple, set)):
        return [
            str(item).strip()
            for item in value
            if item is not None and str(item).strip()
        ]

    return []


def _is_answered(answer: Optional[dict[str, Any]]) -> bool:
    if not isinstance(answer, dict):
        return False

    return bool(_answer_text(answer) or _answer_options(answer))


def _extract_answers(
    response_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Support answers stored as either a list or a question-ID mapping."""
    answers = response_data.get("answers", [])

    if isinstance(answers, dict):
        normalized_answers = []

        for key, value in answers.items():
            if not isinstance(value, dict):
                raise ScreeningDataError(
                    f"Answer for question {key!r} must be a JSON object."
                )

            answer = dict(value)
            qid = answer.get("question_id", key)

            if qid is None or not str(qid).strip():
                raise ScreeningDataError(
                    "Every submitted answer must have a question ID."
                )

            answer["question_id"] = str(qid).strip()
            normalized_answers.append(answer)

        answers = normalized_answers

    elif not isinstance(answers, list):
        raise ScreeningDataError(
            "Response document must contain answers as a list or object."
        )

    result = []
    seen_ids = set()

    for answer in answers:
        if not isinstance(answer, dict):
            raise ScreeningDataError(
                "Every submitted answer must be a JSON object."
            )

        qid = answer.get("question_id")

        if qid is None or not str(qid).strip():
            raise ScreeningDataError(
                "Every submitted answer must have a question_id."
            )

        qid = str(qid).strip()

        if qid in seen_ids:
            raise ScreeningDataError(
                f"Duplicate submitted answer for question: {qid}."
            )

        seen_ids.add(qid)
        result.append({**answer, "question_id": qid})

    return result


def _load_question_bank() -> dict[str, dict[str, Any]]:
    """
    Load question definitions from the configured bank.

    The standard schema uses a top-level questions list. Nested legacy
    structures are also supported. Duplicate question IDs are rejected.
    """
    if not QUESTION_BANK_PATH.is_file():
        return {}

    data = _read_json(QUESTION_BANK_PATH)
    index: dict[str, dict[str, Any]] = {}

    def add_question(node: dict[str, Any]) -> None:
        qid = _question_id(node)

        if not qid:
            return

        is_question = any(
            key in node
            for key in (
                "question_text",
                "question",
                "question_type",
                "answer_type",
                "evaluation_type",
            )
        )

        if not is_question:
            return

        if qid in index:
            raise ScreeningDataError(
                f"Duplicate question ID in question bank: {qid}."
            )

        index[qid] = dict(node)

    questions = data.get("questions")

    if questions is not None:
        if not isinstance(questions, list):
            raise ScreeningDataError(
                "Question bank 'questions' must be a list."
            )

        for question in questions:
            if not isinstance(question, dict):
                raise ScreeningDataError(
                    "Every question-bank entry must be an object."
                )
            add_question(question)

        return index

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            add_question(node)
            for value in node.values():
                visit(value)

        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(data)
    return index


def _validate_configured_score_fields(question: dict[str, Any]) -> None:
    """Reject invalid explicitly configured score maxima before evaluation."""
    qid = _question_id(question) or "UNKNOWN"

    # scoring_importance/score_weight are not maximum scores and are not
    # interpreted as such here.
    for key in ("max_score", "points"):
        if key not in question or question[key] is None:
            continue

        value = question[key]
        if isinstance(value, bool):
            raise ScreeningDataError(
                f"Invalid {key} for question '{qid}': expected a positive number."
            )

        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ScreeningDataError(
                f"Invalid {key} for question '{qid}': expected a positive number."
            ) from exc

        if not math.isfinite(numeric_value) or numeric_value <= 0:
            raise ScreeningDataError(
                f"Invalid {key} for question '{qid}': expected a finite positive number."
            )


def _resolve_questions(
    session: dict[str, Any],
    question_bank: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Resolve assigned questions while keeping bank configuration trusted.

    The session snapshot supplies the assigned question and its mandatory
    flag. Evaluation configuration comes from the bank when available.
    """
    assigned = session.get(
        "assigned_questions",
        session.get("questions", []),
    )

    if not isinstance(assigned, list):
        raise ScreeningDataError(
            "Session questions must be stored as a list."
        )

    resolved = []

    for item in assigned:
        if isinstance(item, str):
            qid = item.strip()
            snapshot = {"question_id": qid}
        elif isinstance(item, dict):
            qid = _question_id(item)
            snapshot = dict(item)
        else:
            raise ScreeningDataError(
                "Every assigned question must be an ID or an object."
            )

        if not qid:
            raise ScreeningDataError(
                "Every assigned question must have a question ID."
            )

        bank_question = question_bank.get(qid)

        if bank_question is not None:
            # Preserve candidate-facing snapshot fields, but never allow
            # the snapshot to override trusted scoring configuration.
            question = {**bank_question, **snapshot}

            for field in TRUSTED_EVALUATION_FIELDS:
                if field in bank_question:
                    question[field] = bank_question[field]

            # The question bank is authoritative for mandatory status.
            # If absent there, use the assignment snapshot.
            if "mandatory" in bank_question:
                question["mandatory"] = bank_question["mandatory"]
            elif "is_mandatory" in bank_question:
                question["mandatory"] = bank_question["is_mandatory"]

        else:
            # Legacy session snapshots may contain all required
            # configuration. They must not silently become objective
            # questions without an explicit answer key.
            question = snapshot

        question["question_id"] = qid
        resolved.append(question)

    ids = [question["question_id"] for question in resolved]

    if len(ids) != len(set(ids)):
        raise ScreeningDataError(
            "The session contains duplicate assigned question IDs."
        )

    return resolved


def _get_expected_options(
    question: dict[str, Any],
) -> Optional[set[str]]:
    value = None

    for key in (
        "correct_option_ids",
        "correct_options",
        "accepted_answers",
        "correct_answers",
        "answer_key",
        "expected_answer",
        "correct_answer",
    ):
        if key in question and question[key] is not None:
            value = question[key]
            break

    if value is None:
        return None

    values = value if isinstance(value, (list, tuple, set)) else [value]

    normalized = {
        _normalize_text(str(item))
        for item in values
        if item is not None and _normalize_text(str(item))
    }

    return normalized


def _needs_review(
    qid: str,
    mandatory: bool,
    answered: bool,
    method: str,
    feedback: str,
) -> dict[str, Any]:
    return {
        "question_id": qid,
        "mandatory": mandatory,
        "answered": answered,
        "evaluation_method": method,
        "evaluation_status": (
            "NEEDS_REVIEW" if answered else "UNANSWERED"
        ),
        "score": None,
        "max_score": None,
        "feedback": feedback[:MAX_FEEDBACK_LENGTH],
    }


def _validate_evaluation_result(
    qid: str,
    mandatory: bool,
    answered: bool,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Normalize and validate an answer-evaluator result."""
    if not isinstance(evaluation, dict):
        raise ScreeningDataError(
            f"Invalid evaluator result for question {qid}."
        )

    status = str(
        evaluation.get("evaluation_status", evaluation.get("status", "NEEDS_REVIEW"))
    ).strip().upper()

    method = str(
        evaluation.get("evaluation_method", evaluation.get("method", "NONE"))
    ).strip().upper()

    if method == "OBJECTIVE":
        method = "EXACT_MATCH"

    feedback = str(evaluation.get("feedback") or "")[
        :MAX_FEEDBACK_LENGTH
    ]

    if not answered:
        return {
            "question_id": qid,
            "mandatory": mandatory,
            "answered": False,
            "evaluation_method": method,
            "evaluation_status": "UNANSWERED",
            "score": None,
            "max_score": None,
            "feedback": "No answer was submitted.",
        }

    if status != "EVALUATED":
        return {
            "question_id": qid,
            "mandatory": mandatory,
            "answered": True,
            "evaluation_method": method,
            "evaluation_status": "NEEDS_REVIEW",
            "score": None,
            "max_score": None,
            "feedback": feedback or "Manual review is required.",
        }

    try:
        score = float(evaluation.get("score"))
        max_score = float(evaluation.get("max_score"))
    except (TypeError, ValueError) as exc:
        raise ScreeningDataError(
            f"Evaluator returned invalid scores for question {qid}."
        ) from exc

    if (
        not math.isfinite(score)
        or not math.isfinite(max_score)
        or max_score <= 0
        or score < 0
        or score > max_score
    ):
        raise ScreeningDataError(
            f"Evaluator returned out-of-range scores for question {qid}."
        )

    return {
        "question_id": qid,
        "mandatory": mandatory,
        "answered": True,
        "evaluation_method": method,
        "evaluation_status": "EVALUATED",
        "score": round(score, 4),
        "max_score": round(max_score, 4),
        "feedback": feedback,
    }


def _evaluate_question(
    question: dict[str, Any],
    answer: Optional[dict[str, Any]],
    evaluator: Optional[Callable[..., dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Evaluate one question according to its explicit evaluation type."""
    qid = question["question_id"]
    mandatory = _is_mandatory(question)
    answered = _is_answered(answer)

    if not answered:
        return {
            "question_id": qid,
            "mandatory": mandatory,
            "answered": False,
            "evaluation_method": "NONE",
            "evaluation_status": "UNANSWERED",
            "score": None,
            "max_score": None,
            "feedback": "No answer was submitted.",
        }

    answer = dict(answer or {})
    evaluation_type = str(
        question.get("evaluation_type", "")
    ).strip().upper()

    # Human-reviewed answers must never receive automatic scores.
    if evaluation_type == "HUMAN_REVIEW":
        return _needs_review(
            qid,
            mandatory,
            True,
            "HUMAN_REVIEW",
            "Recruiter review is required for this answer.",
        )

    expected_options = _get_expected_options(question)

    # Objective scoring requires an explicit objective configuration.
    # Legacy questions without evaluation_type may still use an explicit
    # answer key for backward compatibility.
    is_objective = (
        evaluation_type == "OBJECTIVE"
        or (not evaluation_type and expected_options is not None)
    )

    if is_objective:
        if expected_options is None or not expected_options:
            return _needs_review(
                qid,
                mandatory,
                True,
                "EXACT_MATCH",
                "Objective answer key is missing or empty.",
            )

        normalized_question = dict(question)
        normalized_question["accepted_answers"] = sorted(expected_options)

        selected = _answer_options(answer)
        if selected:
            normalized_answer = {**answer, "selected_options": selected}
        else:
            normalized_answer = answer

        try:
            evaluation = evaluate_answer(
                question=normalized_question,
                answer=normalized_answer,
            )
        except AnswerEvaluationError as exc:
            raise ScreeningDataError(
                f"Invalid objective configuration for {qid}: {exc}"
            ) from exc

        return _validate_evaluation_result(
            qid, mandatory, True, evaluation
        )

    # Keyword rubric scoring is permitted only for RUBRIC_REVIEW.
    if evaluation_type == "RUBRIC_REVIEW":
        has_rubric = (
            question.get("evaluation_criteria") is not None
            or question.get("rubric") is not None
        )

        if evaluator is None and not has_rubric:
            return _needs_review(
                qid,
                mandatory,
                True,
                "RUBRIC",
                "Rubric criteria are missing. Manual review is required.",
            )

        try:
            evaluation = evaluate_answer(
                question=question,
                answer=answer,
                evaluator=evaluator,
            )
        except AnswerEvaluationError as exc:
            # Invalid rubric configuration is a data/configuration problem,
            # not a reason to invent a score or silently ignore the rubric.
            raise ScreeningDataError(
                f"Invalid rubric configuration for {qid}: {exc}"
            ) from exc

        return _validate_evaluation_result(
            qid, mandatory, True, evaluation
        )

    # Rule-based questions need both explicit rule configuration and an
    # injected evaluator that knows how to interpret those rules.
    if evaluation_type == "RULE_BASED":
        has_rules = (
            isinstance(question.get("rules"), (dict, list))
            and bool(question.get("rules"))
        ) or (
            isinstance(question.get("rule_config"), dict)
            and bool(question.get("rule_config"))
        )

        if evaluator is None or not has_rules:
            return _needs_review(
                qid,
                mandatory,
                True,
                "RULE_BASED",
                (
                    "Explicit rules and a configured rule evaluator "
                    "are required. Manual review is required."
                ),
            )

        try:
            evaluation = evaluate_answer(
                question=question,
                answer=answer,
                evaluator=evaluator,
            )
        except AnswerEvaluationError as exc:
            raise ScreeningDataError(
                f"Invalid rule-based configuration for {qid}: {exc}"
            ) from exc

        return _validate_evaluation_result(
            qid, mandatory, True, evaluation
        )

    # Support legacy questions that explicitly contain an answer key.
    # Do not use this fallback for a known HUMAN_REVIEW/RULE_BASED type.
    if not evaluation_type and expected_options is not None:
        try:
            evaluation = evaluate_answer(
                question=question,
                answer=answer,
                evaluator=evaluator,
            )
        except AnswerEvaluationError as exc:
            raise ScreeningDataError(
                f"Invalid evaluation configuration for {qid}: {exc}"
            ) from exc

        return _validate_evaluation_result(
            qid, mandatory, True, evaluation
        )

    # Unknown types must not fall through to automatic rubric scoring.
    # Legacy questions without evaluation_type may use an explicitly
    # injected evaluator. Known HUMAN_REVIEW and RULE_BASED questions
    # have already been handled above.
    if not evaluation_type and evaluator is not None:
        try:
            evaluation = evaluate_answer(
                question=question,
                answer=answer,
                evaluator=evaluator,
            )
        except AnswerEvaluationError as exc:
            raise ScreeningDataError(
                f"Invalid evaluation configuration for {qid}: {exc}"
            ) from exc

        return _validate_evaluation_result(
            qid, mandatory, True, evaluation
        )

    # Unknown types must not fall through to automatic scoring.
    return _needs_review(
        qid,
        mandatory,
        True,
        "NONE",
        (
            f"Evaluation type {evaluation_type or 'UNSPECIFIED'} "
            "is unsupported. Manual review is required."
        ),
    )

   
def _build_evaluation_fingerprint(
    *,
    session: dict[str, Any],
    questions: list[dict[str, Any]],
    answers: dict[str, dict[str, Any]],
) -> str:
    """Create a deterministic fingerprint for evaluation inputs."""
    payload = {
        "evaluation_version": EVALUATION_VERSION,
        "session_id": session.get("session_id"),
        "candidate_id": session.get("candidate_id"),
        "job_id": session.get("job_id"),
        "role_id": session.get("role_id"),
        "status": session.get("status"),
        "questions": questions,
        "answers": answers,
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_session_id(session_id: str) -> None:
    if (
        not isinstance(session_id, str)
        or not SESSION_ID_PATTERN.fullmatch(session_id)
    ):
        raise ValueError("Invalid screening session ID.")



def evaluate_screening_session(
    session_id: str,
    evaluator: Optional[Callable[..., dict[str, Any]]] = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Evaluate a submitted screening session and persist its report.

    Cache policy:
    - Return an existing report when force=False.
    - A custom evaluator does not bypass the cache.
    - Set force=True to explicitly run evaluation again.
    - Validate the session and response records before using the cache.
    """
    _validate_session_id(session_id)

    session_path = SESSIONS_DIR / f"{session_id}.json"
    response_path = RESPONSES_DIR / f"{session_id}.json"
    report_path = EVALUATIONS_DIR / f"{session_id}.json"

    # ---------------------------------------------------------
    # 1. Load and validate the session
    # ---------------------------------------------------------
    try:
        session = _read_json(session_path)
    except FileNotFoundError as exc:
        raise ScreeningSessionNotFoundError(
            f"Screening session '{session_id}' was not found."
        ) from exc

    if session.get("session_id") != session_id:
        raise ScreeningDataError(
            "Screening session ID does not match its stored record."
        )

    if session.get("status") != "SUBMITTED":
        raise InvalidScreeningStateError(
            "Only submitted screening sessions can be evaluated."
        )

    # ---------------------------------------------------------
    # 2. Validate the response record
    # ---------------------------------------------------------
    try:
        responses = _read_json(response_path)
    except FileNotFoundError as exc:
        raise ScreeningResponseNotFoundError(
            f"Responses for session '{session_id}' were not found."
        ) from exc

    if responses.get("session_id") != session_id:
        raise ScreeningDataError(
            "Response session ID does not match the requested session."
        )

    session_candidate_id = session.get("candidate_id")
    response_candidate_id = responses.get("candidate_id")

    if (
        response_candidate_id is not None
        and response_candidate_id != session_candidate_id
    ):
        raise ScreeningDataError(
            "Session and response candidate IDs do not match."
        )

    # ---------------------------------------------------------
    # 3. Return the existing report unless forced to reevaluate
    # ---------------------------------------------------------
    if report_path.is_file() and not force:
        cached_report = _read_json(report_path)

        if cached_report.get("session_id") != session_id:
            raise ScreeningDataError(
                "Saved evaluation report session ID does not match "
                "the requested session."
            )

        logger.info(
            "HR screening evaluation cache hit: session_id=%s",
            session_id,
        )
        return cached_report

    # ---------------------------------------------------------
    # 4. Resolve and validate assigned questions
    # ---------------------------------------------------------
    raw_assigned_questions = session.get(
        "assigned_questions",
        session.get("questions", []),
    )

    if isinstance(raw_assigned_questions, list):
        for raw_question in raw_assigned_questions:
            if isinstance(raw_question, dict):
                _validate_configured_score_fields(raw_question)

    question_bank = _load_question_bank()
    questions = _resolve_questions(session, question_bank)

    if not questions:
        raise ScreeningDataError(
            "Cannot evaluate a session with no assigned questions."
        )

    assigned_ids: set[str] = set()

    for question in questions:
        qid = question.get("question_id")

        if not isinstance(qid, str) or not qid.strip():
            raise ScreeningDataError(
                "An assigned question has no valid question ID."
            )

        mandatory = question.get(
            "mandatory",
            question.get("is_mandatory", False),
        )

        if not isinstance(mandatory, bool):
            raise ScreeningDataError(
                f"Invalid mandatory flag for question '{qid}'."
            )

        question["mandatory"] = mandatory
        _validate_configured_score_fields(question)
        assigned_ids.add(qid)

    # ---------------------------------------------------------
    # 5. Normalize submitted answers and validate assignments
    # ---------------------------------------------------------
    answers_list = _extract_answers(responses)
    answers_by_id = {
        answer["question_id"]: answer
        for answer in answers_list
    }

    unexpected_ids = set(answers_by_id) - assigned_ids

    if unexpected_ids:
        raise ScreeningDataError(
            "Responses contain questions that were not assigned "
            "to this screening session."
        )

    # Fingerprint retained for auditability and compatibility.
    input_fingerprint = _build_evaluation_fingerprint(
        session=session,
        questions=questions,
        answers=answers_by_id,
    )

    # ---------------------------------------------------------
    # 6. Evaluate each assigned question
    # ---------------------------------------------------------
    question_results = []

    for question in questions:
        qid = question["question_id"]
        answer = answers_by_id.get(qid)

        result = _evaluate_question(
            question=question,
            answer=answer,
            evaluator=evaluator,
        )

        if result.get("question_id") != qid:
            raise ScreeningDataError(
                f"Evaluation result question ID mismatch: {qid}."
            )

        # Assignment-level mandatory status remains authoritative.
        result["mandatory"] = question["mandatory"]

        # An evaluator cannot mark an absent answer as answered.
        result["answered"] = _is_answered(answer)

        if not result["answered"]:
            result["evaluation_status"] = "UNANSWERED"
            result["score"] = None
            result["max_score"] = None

        question_results.append(result)

    # ---------------------------------------------------------
    # 7. Aggregate and validate scores
    # ---------------------------------------------------------
    total_score = 0.0
    max_score = 0.0
    evaluated_questions = 0

    for result in question_results:
        if result["evaluation_status"] != "EVALUATED":
            continue

        score = result.get("score")
        question_max = result.get("max_score")

        if isinstance(score, bool) or isinstance(question_max, bool):
            raise ScreeningDataError(
                "Boolean values are not valid evaluation scores."
            )

        try:
            score = float(score)
            question_max = float(question_max)
        except (TypeError, ValueError) as exc:
            raise ScreeningDataError(
                "An evaluated question contains invalid scores."
            ) from exc

        if (
            not math.isfinite(score)
            or not math.isfinite(question_max)
            or question_max <= 0
            or score < 0
            or score > question_max
        ):
            raise ScreeningDataError(
                "An evaluated question contains a score outside "
                "its permitted range."
            )

        total_score += score
        max_score += question_max
        evaluated_questions += 1

    total_score = round(total_score, 2)
    max_score = round(max_score, 2)

    score_percentage = (
        round(total_score / max_score * 100, 2)
        if max_score > 0
        else None
    )

    # ---------------------------------------------------------
    # 8. Calculate screening completion and review requirements
    # ---------------------------------------------------------
    answered_questions = sum(
        result["answered"] for result in question_results
    )

    mandatory_questions = sum(
        question["mandatory"] for question in questions
    )

    answered_mandatory_questions = sum(
        result["mandatory"] and result["answered"]
        for result in question_results
    )

    unanswered_questions = sum(
        result["evaluation_status"] == "UNANSWERED"
        for result in question_results
    )

    unanswered_mandatory_ids = [
        result["question_id"]
        for result in question_results
        if result["mandatory"] and not result["answered"]
    ]

    questions_needing_review = sum(
        result["evaluation_status"] == "NEEDS_REVIEW"
        for result in question_results
    )

    summary = {
        "total_questions": len(questions),
        "mandatory_questions": mandatory_questions,
        "optional_questions": len(questions) - mandatory_questions,
        "answered_questions": answered_questions,
        "answered_mandatory_questions": answered_mandatory_questions,
        "evaluated_questions": evaluated_questions,
        "unanswered_questions": unanswered_questions,
        "unanswered_mandatory_questions": unanswered_mandatory_ids,
        "mandatory_unanswered_questions": len(
            unanswered_mandatory_ids
        ),
        "questions_needing_review": questions_needing_review,
        "total_score": total_score,
        "max_score": max_score,
        "score_percentage": score_percentage,
    }

    needs_review = bool(unanswered_mandatory_ids) or any(
        result["evaluation_status"] == "NEEDS_REVIEW"
        for result in question_results
    )

    overall_status = (
        "NEEDS_REVIEW" if needs_review else "COMPLETED"
    )
    recommendation = (
        "MANUAL_REVIEW"
        if needs_review
        else "EVALUATION_COMPLETED"
    )

    # ---------------------------------------------------------
    # 9. Build the evaluation report
    # ---------------------------------------------------------
    report = {
        "evaluation_id": f"EVAL_{session_id}",
        "session_id": session_id,
        "candidate_id": session_candidate_id,
        "job_id": session.get("job_id"),
        "role_id": session.get("role_id"),
        "language": session.get("language", "en"),
        "evaluation_version": EVALUATION_VERSION,
        "input_fingerprint": input_fingerprint,
        "summary": summary,

        # Compatibility fields retained for existing consumers.
        "evaluated_questions": evaluated_questions,
        "total_score": total_score,
        "max_score": max_score,
        "score_percentage": score_percentage,
        "question_results": question_results,
        "evaluation_results": question_results,

        "status": overall_status,
        "overall_status": overall_status,
        "decision": {
            "recommendation": recommendation,
            "automatic_rejection": False,
        },
        "recommendation": recommendation,
        "automatic_rejection": False,
        "evaluated_at": _utc_now(),
    }

    # ---------------------------------------------------------
    # 10. Persist atomically and return the report
    # ---------------------------------------------------------
    _write_json_atomic(report_path, report)

    logger.info(
        "HR screening evaluation saved: session_id=%s status=%s "
        "evaluated_questions=%s",
        session_id,
        overall_status,
        evaluated_questions,
    )

    return report


def get_screening_evaluation(session_id: str) -> dict[str, Any]:
    """Retrieve a previously saved evaluation report."""
    _validate_session_id(session_id)
    report_path = EVALUATIONS_DIR / f"{session_id}.json"

    try:
        report = _read_json(report_path)
    except FileNotFoundError as exc:
        raise ScreeningEvaluationError(
            f"No evaluation report exists for session: {session_id}."
        ) from exc

    if report.get("session_id") != session_id:
        raise ScreeningDataError(
            "Saved evaluation report session ID does not match the request."
        )

    return report



def _recalculate_reviewed_report(
    report: dict[str, Any],
) -> None:
    """Recalculate report totals after recruiter review."""

    results = report.get("question_results", [])

    evaluated = [
        item for item in results
        if item.get("evaluation_status") == "EVALUATED"
    ]

    total_score = round(
        sum(float(item["score"]) for item in evaluated),
        2,
    )
    max_score = round(
        sum(float(item["max_score"]) for item in evaluated),
        2,
    )

    score_percentage = (
        round(total_score / max_score * 100, 2)
        if max_score > 0
        else None
    )

    unanswered = [
        item for item in results
        if item.get("evaluation_status") == "UNANSWERED"
    ]

    unanswered_mandatory = [
        item["question_id"]
        for item in unanswered
        if item.get("mandatory") is True
    ]

    needs_review = sum(
        item.get("evaluation_status") == "NEEDS_REVIEW"
        for item in results
    )

    mandatory_count = sum(
        item.get("mandatory") is True
        for item in results
    )

    answered_count = sum(
        item.get("answered") is True
        for item in results
    )

    answered_mandatory_count = sum(
        item.get("mandatory") is True
        and item.get("answered") is True
        for item in results
    )

    is_complete = (
        needs_review == 0
        and not unanswered_mandatory
    )

    report["summary"].update({
        "total_questions": len(results),
        "mandatory_questions": mandatory_count,
        "optional_questions": len(results) - mandatory_count,
        "answered_questions": answered_count,
        "answered_mandatory_questions": answered_mandatory_count,
        "evaluated_questions": len(evaluated),
        "unanswered_questions": len(unanswered),
        "unanswered_mandatory_questions": unanswered_mandatory,
        "mandatory_unanswered_questions": len(unanswered_mandatory),
        "questions_needing_review": needs_review,
        "total_score": total_score,
        "max_score": max_score,
        "score_percentage": score_percentage,
    })

    report.update({
        "evaluated_questions": len(evaluated),
        "total_score": total_score,
        "max_score": max_score,
        "score_percentage": score_percentage,
        "status": "COMPLETED" if is_complete else "NEEDS_REVIEW",
        "overall_status": "COMPLETED" if is_complete else "NEEDS_REVIEW",
        "recommendation": (
            "EVALUATION_COMPLETED"
            if is_complete
            else "MANUAL_REVIEW"
        ),
        "decision": {
            "recommendation": (
                "EVALUATION_COMPLETED"
                if is_complete
                else "MANUAL_REVIEW"
            ),
            "automatic_rejection": False,
        },
        "automatic_rejection": False,
        "review_updated_at": _utc_now(),
    })

    # Keep both compatibility fields synchronized.
    report["question_results"] = results
    report["evaluation_results"] = results


def review_screening_question(
    session_id: str,
    *,
    question_id: str,
    reviewer_id: str,
    score: float,
    max_score: float,
    feedback: str,
) -> dict[str, Any]:
    """Record a recruiter review for one answer."""

    _validate_session_id(session_id)

    if not question_id.strip():
        raise ValueError("question_id is required.")

    if not reviewer_id.strip():
        raise ValueError("reviewer_id is required.")

    if not math.isfinite(score) or not math.isfinite(max_score):
        raise ValueError("Scores must be finite numbers.")

    if max_score <= 0 or score < 0 or score > max_score:
        raise ValueError("Invalid recruiter score range.")

    feedback = feedback.strip()

    if not feedback:
        raise ValueError("Recruiter feedback is required.")

    if len(feedback) > MAX_FEEDBACK_LENGTH:
        raise ValueError("Recruiter feedback is too long.")

    report_path = EVALUATIONS_DIR / f"{session_id}.json"

    try:
        report = _read_json(report_path)
    except FileNotFoundError as exc:
        raise ScreeningEvaluationError(
            "No evaluation report exists for this session."
        ) from exc

    if report.get("session_id") != session_id:
        raise ScreeningDataError(
            "Evaluation report session ID does not match."
        )

    results = report.get("question_results")

    if not isinstance(results, list):
        raise ScreeningDataError(
            "Evaluation report has invalid question results."
        )

    target = next(
        (
            item for item in results
            if item.get("question_id") == question_id
        ),
        None,
    )

    if target is None:
        raise ScreeningEvaluationError(
            "Question does not belong to this evaluation."
        )

    if target.get("answered") is not True:
        raise ScreeningEvaluationError(
            "Unanswered questions cannot be scored by this workflow."
        )

    if target.get("evaluation_status") != "NEEDS_REVIEW":
        raise ScreeningEvaluationError(
            "Only questions marked NEEDS_REVIEW can be reviewed."
        )

    reviewed_at = _utc_now()

    review = {
        "reviewer_id": reviewer_id.strip(),
        "score": round(float(score), 4),
        "max_score": round(float(max_score), 4),
        "feedback": feedback,
        "reviewed_at": reviewed_at,
    }

    # Preserve the previous automatic evaluation details in the audit.
    history = target.setdefault("review_history", [])
    if not isinstance(history, list):
        raise ScreeningDataError(
            "Question review history is invalid."
        )

    history.append(review)

    target.update({
        "evaluation_method": "HUMAN_REVIEW",
        "evaluation_status": "EVALUATED",
        "score": review["score"],
        "max_score": review["max_score"],
        "feedback": feedback,
        "reviewer_id": review["reviewer_id"],
        "reviewed_at": reviewed_at,
    })

    report.setdefault("review_history", []).append({
        "question_id": question_id,
        **review,
    })

    _recalculate_reviewed_report(report)
    _write_json_atomic(report_path, report)

    logger.info(
        "Recruiter review saved: session_id=%s question_id=%s",
        session_id,
        question_id,
    )

    return report
