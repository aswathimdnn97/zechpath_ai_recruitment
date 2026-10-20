"""
answer_evaluator.py

Responsibilities
----------------
1. Evaluate objective answers using explicit answer keys.
2. Evaluate rubric-based answers only when a valid rubric is configured.
3. Support custom evaluators for open-ended answers.
4. Preserve the custom evaluator's evaluation method.
5. Validate scores and maximum scores.
6. Never invent scores when evaluation configuration is missing.
7. Return NEEDS_REVIEW when an answer cannot be evaluated reliably.
8. Never automatically reject a candidate.

Supported evaluation methods
----------------------------
- EXACT_MATCH
- KEYWORD_RUBRIC
- CUSTOM or a custom evaluator's own method name
- NONE

Public API
----------
evaluate_answer(question, answer, evaluator=None)
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from typing import Any


# ============================================================
# CONSTANTS
# ============================================================

STATUS_EVALUATED = "EVALUATED"
STATUS_NEEDS_REVIEW = "NEEDS_REVIEW"

METHOD_EXACT_MATCH = "EXACT_MATCH"
METHOD_OBJECTIVE = "OBJECTIVE"
METHOD_KEYWORD_RUBRIC = "KEYWORD_RUBRIC"
METHOD_CUSTOM = "CUSTOM"
METHOD_NONE = "NONE"


# ============================================================
# EXCEPTIONS
# ============================================================

class AnswerEvaluationError(ValueError):
    """Raised when answer evaluation configuration or scores are invalid."""


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_text(value: Any) -> str:
    """Normalize text for case-insensitive exact matching."""

    if value is None:
        return ""

    if isinstance(value, bool):
        return str(value).lower()

    if isinstance(value, (int, float)):
        return str(value).strip().lower()

    if not isinstance(value, str):
        return ""

    return re.sub(r"\s+", " ", value.strip()).casefold()


def _normalize_answer_collection(value: Any) -> set[str]:
    """Convert an answer or collection of answers into normalized strings."""

    if value is None:
        return set()

    if isinstance(value, str):
        normalized = _normalize_text(value)
        return {normalized} if normalized else set()

    if isinstance(value, (list, tuple, set)):
        results: set[str] = set()

        for item in value:
            results.update(_normalize_answer_collection(item))

        return results

    if isinstance(value, (int, float, bool)):
        normalized = _normalize_text(value)
        return {normalized} if normalized else set()

    return set()


# ============================================================
# QUESTION CONFIGURATION
# ============================================================

def _get_configured_max_score(
    question: dict[str, Any],
) -> float | None:
    """
    Return an explicitly configured maximum score.

    scoring_importance is intentionally excluded because it represents
    the importance of a question, not its maximum achievable score.

    Returns None when the question has no explicitly configured maximum.
    """

    for key in ("max_score", "points"):
        if key not in question or question[key] is None:
            continue

        value = question[key]

        if isinstance(value, bool):
            raise AnswerEvaluationError(
                f"Question {key} must be a positive number."
            )

        try:
            value = float(value)
        except (TypeError, ValueError) as exc:
            raise AnswerEvaluationError(
                f"Question {key} must be a positive number."
            ) from exc

        if not math.isfinite(value) or value <= 0:
            raise AnswerEvaluationError(
                f"Question {key} must be finite and greater than zero."
            )

        return value

    return None


def _get_max_score(question: dict[str, Any]) -> float:
    """
    Get the scoring maximum.

    The default of 1.0 is used for built-in evaluators when no maximum
    is configured. A custom evaluator may supply its own maximum.
    """

    configured_max = _get_configured_max_score(question)
    return configured_max if configured_max is not None else 1.0


def _get_answer_type(question: dict[str, Any]) -> str:
    """Read and normalize the question's answer type."""

    for key in ("answer_type", "question_type", "type"):
        value = question.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip().upper()

    return ""


def _get_answer_value(answer: Any) -> Any:
    """
    Extract the candidate's answer from supported answer formats.

    Supported examples:
        "Python"
        {"answer": "Python"}
        {"response": "Python"}
        {"selected_option": "OPT_1"}
        {"selected_options": ["OPT_1", "OPT_2"]}
    """

    if answer is None:
        return None

    if not isinstance(answer, dict):
        return answer

    for key in ("selected_options", "selected_option"):
        if key in answer:
            value = answer[key]

            if value is not None and value != "" and value != []:
                return value

    for key in ("answer", "response", "answer_text", "value"):
        if key in answer:
            return answer[key]

    return None


def _is_answered(answer: Any) -> bool:
    """Determine whether the candidate provided a meaningful answer."""

    value = _get_answer_value(answer)

    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (list, tuple, set)):
        return any(_is_answered(item) for item in value)

    if isinstance(value, dict):
        return bool(value)

    # False and zero can be valid answers.
    return True


# ============================================================
# OBJECTIVE ANSWER KEY
# ============================================================

def _get_answer_key(question: dict[str, Any]) -> Any:
    """Return the first explicitly configured answer key."""

    for key in (
        "accepted_answers",
        "correct_answers",
        "answer_key",
        "correct_option_ids",
        "correct_options",
        "expected_answer",
        "correct_answer",
    ):
        if key in question and question[key] is not None:
            value = question[key]

            if value != "" and value != []:
                return value

    return None


def _has_answer_key(question: dict[str, Any]) -> bool:
    """Check whether an explicit answer key is available."""

    return bool(_normalize_answer_collection(_get_answer_key(question)))


def _evaluate_objective(
    question: dict[str, Any],
    answer: Any,
) -> dict[str, Any]:
    """Evaluate an objective answer using exact normalized matching."""

    answer_key = _get_answer_key(question)

    if answer_key is None:
        return _needs_review(
            "No explicit answer key is configured for this question."
        )

    expected = _normalize_answer_collection(answer_key)
    actual = _normalize_answer_collection(_get_answer_value(answer))

    if not expected:
        return _needs_review("The configured answer key is empty or invalid.")

    if not actual:
        return _needs_review("The answer could not be normalized.")

    max_score = _get_max_score(question)
    is_correct = actual == expected

    return {
        "status": STATUS_EVALUATED,
        "evaluation_status": STATUS_EVALUATED,
        "score": max_score if is_correct else 0.0,
        "max_score": max_score,
        "evaluation_method": METHOD_OBJECTIVE,
        "method": METHOD_OBJECTIVE,
        "feedback": (
            "The answer matches the configured answer key."
            if is_correct
            else "The answer does not match the configured answer key."
        ),
    }


# ============================================================
# RUBRIC EVALUATION
# ============================================================

def _contains_keyword(text: str, keyword: str) -> bool:
    """Check whether a keyword or phrase occurs as a whole phrase."""

    normalized_text = _normalize_text(text)
    normalized_keyword = _normalize_text(keyword)

    if not normalized_text or not normalized_keyword:
        return False

    pattern = (
        r"(?<!\w)"
        + re.escape(normalized_keyword)
        + r"(?!\w)"
    )

    return re.search(pattern, normalized_text, flags=re.IGNORECASE) is not None


def _get_rubric(question: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Retrieve an explicitly configured evaluation rubric."""

    for key in ("evaluation_criteria", "rubric"):
        value = question.get(key)

        if value is None:
            continue

        if isinstance(value, list) and value:
            return value

    return None


def _evaluate_rubric(
    question: dict[str, Any],
    answer: Any,
) -> dict[str, Any]:
    """
    Evaluate configured rubric criteria through keyword coverage.

    This is a deterministic keyword-based approximation. It does not
    claim to understand answer quality or meaning beyond keyword matches.
    """

    rubric = _get_rubric(question)

    if not rubric:
        return _needs_review("No evaluation rubric is configured.")

    answer_text = _get_answer_value(answer)

    if not isinstance(answer_text, str) or not answer_text.strip():
        return _needs_review(
            "The answer is not suitable for keyword-based rubric evaluation."
        )

    parsed_criteria: list[dict[str, Any]] = []

    for index, criterion in enumerate(rubric):
        if not isinstance(criterion, dict):
            return _needs_review(
                f"Rubric criterion {index + 1} has an invalid format."
            )

        keywords = criterion.get("keywords")

        if not isinstance(keywords, list) or not keywords:
            return _needs_review(
                f"Rubric criterion {index + 1} has no configured keywords."
            )

        normalized_keywords = [
            str(keyword).strip()
            for keyword in keywords
            if isinstance(keyword, str) and keyword.strip()
        ]

        if not normalized_keywords:
            return _needs_review(
                f"Rubric criterion {index + 1} has no valid keywords."
            )

        weight_value = criterion.get("weight", 1)

        if isinstance(weight_value, bool):
            return _needs_review(
                f"Rubric criterion {index + 1} has an invalid weight."
            )

        try:
            weight = float(weight_value)
        except (TypeError, ValueError):
            return _needs_review(
                f"Rubric criterion {index + 1} has an invalid weight."
            )

        if not math.isfinite(weight) or weight <= 0:
            return _needs_review(
                f"Rubric criterion {index + 1} must have a positive weight."
            )

        required = criterion.get("required", False)

        if not isinstance(required, bool):
            return _needs_review(
                f"Rubric criterion {index + 1} has an invalid required flag."
            )

        parsed_criteria.append(
            {
                "keywords": normalized_keywords,
                "weight": weight,
                "required": required,
                "name": str(
                    criterion.get("name")
                    or criterion.get("criterion")
                    or f"Criterion {index + 1}"
                ),
            }
        )

    max_score = _get_max_score(question)
    total_weight = sum(item["weight"] for item in parsed_criteria)

    if total_weight <= 0:
        return _needs_review("The rubric has no valid scoring weight.")

    earned_weight = 0.0
    missing_required: list[str] = []
    matched_criteria: list[str] = []

    for criterion in parsed_criteria:
        matched = any(
            _contains_keyword(answer_text, keyword)
            for keyword in criterion["keywords"]
        )

        if matched:
            earned_weight += criterion["weight"]
            matched_criteria.append(criterion["name"])
        elif criterion["required"]:
            missing_required.append(criterion["name"])

    score = max_score * earned_weight / total_weight

    feedback_parts = [
        "Score is based on configured keyword coverage, not semantic understanding."
    ]

    if matched_criteria:
        feedback_parts.append(
            "Matched criteria: " + ", ".join(matched_criteria) + "."
        )

    if missing_required:
        feedback_parts.append(
            "Required criteria not matched: "
            + ", ".join(missing_required)
            + "."
        )

    return {
        "status": STATUS_EVALUATED,
        "evaluation_status": STATUS_EVALUATED,
        "score": round(score, 4),
        "max_score": max_score,
        "evaluation_method": METHOD_KEYWORD_RUBRIC,
        "method": METHOD_KEYWORD_RUBRIC,
        "feedback": " ".join(feedback_parts),
        "matched_criteria": matched_criteria,
        "missing_required_criteria": missing_required,
    }


# ============================================================
# CUSTOM EVALUATOR
# ============================================================

def _evaluate_with_custom_evaluator(
    question: dict[str, Any],
    answer: Any,
    evaluator: Callable[..., Any],
) -> dict[str, Any]:
    """
    Evaluate an answer using a supplied custom evaluator.

    The evaluator must return a dictionary containing at least:
        score
        status

    It may also return:
        max_score
        method
        evaluation_method
        feedback

    If the question has an explicit maximum score, a conflicting maximum
    returned by the evaluator is rejected.

    If the question has no explicit maximum, the evaluator may provide
    its own maximum score. This supports evaluators returning scores such
    as 4/5 or 3/3 without being incorrectly compared against a default 1.
    """

    raw_result = evaluator(question=question, answer=answer)

    if not isinstance(raw_result, dict):
        raise AnswerEvaluationError(
            "The custom evaluator must return a dictionary."
        )

    status = raw_result.get("status", STATUS_EVALUATED)

    if status != STATUS_EVALUATED:
        if status != STATUS_NEEDS_REVIEW:
            raise AnswerEvaluationError(
                f"Unsupported custom evaluator status: {status!r}."
            )

        return {
            **raw_result,
            "status": STATUS_NEEDS_REVIEW,
            "score": None,
            "max_score": raw_result.get("max_score"),
            "evaluation_method": str(
                raw_result.get("evaluation_method")
                or raw_result.get("method")
                or METHOD_CUSTOM
            ).strip().upper(),
            "method": str(
                raw_result.get("method")
                or raw_result.get("evaluation_method")
                or METHOD_CUSTOM
            ).strip().upper(),
            "feedback": str(
                raw_result.get("feedback")
                or "Manual review is required."
            ),
        }

    score_value = raw_result.get("score")

    if isinstance(score_value, bool):
        raise AnswerEvaluationError(
            "The custom evaluator score must be a non-negative number."
        )

    try:
        score = float(score_value)
    except (TypeError, ValueError) as exc:
        raise AnswerEvaluationError(
            "The custom evaluator must return a numeric score."
        ) from exc

    if not math.isfinite(score) or score < 0:
        raise AnswerEvaluationError(
            "The custom evaluator score must be finite and non-negative."
        )


    configured_max = _get_configured_max_score(question)
    returned_max_value = raw_result.get("max_score")

    if returned_max_value is not None:
        if isinstance(returned_max_value, bool):
            raise AnswerEvaluationError(
                "Custom evaluator max_score must be a positive number."
            )

        try:
            returned_max = float(returned_max_value)
        except (TypeError, ValueError) as exc:
            raise AnswerEvaluationError(
                "Custom evaluator max_score must be a positive number."
            ) from exc

        if not math.isfinite(returned_max) or returned_max <= 0:
            raise AnswerEvaluationError(
                "Custom evaluator max_score must be finite and positive."
            )

        if (
            configured_max is not None
            and not math.isclose(
                returned_max,
                configured_max,
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
        ):
            raise AnswerEvaluationError(
                "Custom evaluator max_score does not match the configured maximum."
            )

        effective_max = (
            configured_max if configured_max is not None else returned_max
        )
    else:
        effective_max = (
            configured_max if configured_max is not None else _get_max_score(question)
        )

    if score > effective_max:
        raise AnswerEvaluationError(
            "Custom evaluator score cannot exceed max_score."
        )

    # Preserve the evaluator's own method, such as TEST_EVALUATOR.
    method_value = (
        raw_result.get("evaluation_method")
        or raw_result.get("method")
        or METHOD_CUSTOM
    )

    if not isinstance(method_value, str) or not method_value.strip():
        method_value = METHOD_CUSTOM

    method = method_value.strip().upper()

    return {
        **raw_result,
        "status": STATUS_EVALUATED,
        "evaluation_status": STATUS_EVALUATED,
        "score": round(score, 4),
        "max_score": effective_max,
        "evaluation_method": method,
        "method": method,
        "feedback": str(
            raw_result.get("feedback")
            or "Answer evaluated by the configured custom evaluator."
        ),
    }


# ============================================================
# REVIEW RESULT
# ============================================================

def _needs_review(
    feedback: str,
    *,
    method: str = METHOD_NONE,
) -> dict[str, Any]:
    """Build a consistent result for answers requiring manual review."""

    return {
        "status": STATUS_NEEDS_REVIEW,
        "evaluation_status": STATUS_NEEDS_REVIEW,
        "score": None,
        "max_score": None,
        "evaluation_method": method,
        "method": method,
        "feedback": feedback,
    }


# ============================================================
# PUBLIC API
# ============================================================

def evaluate_answer(
    question: dict[str, Any],
    answer: Any,
    evaluator: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """
    Evaluate one screening answer.

    Evaluation order:
    1. Validate input.
    2. Handle unanswered questions.
    3. Use an explicitly configured custom evaluator when supplied.
    4. Evaluate an explicit objective answer key.
    5. Evaluate a configured keyword rubric.
    6. Otherwise return NEEDS_REVIEW.

    Exceptions from evaluation configuration or a custom evaluator are
    converted into NEEDS_REVIEW so a single bad answer does not crash
    the complete screening evaluation.
    """

    if not isinstance(question, dict):
        return _needs_review("Invalid question configuration.")

    # Invalid scoring configuration is a caller/configuration error, not a
    # candidate-answer evaluation failure. Raise it explicitly so it can be
    # caught during question-bank/session validation.
    _get_configured_max_score(question)

    if not _is_answered(answer):
        # An unanswered response is not automatically scored as incorrect.
        # Flag it for review so the screening workflow can apply its
        # mandatory-question policy without silently rejecting a candidate.
        return _needs_review(
            "The candidate did not provide an answer. Manual review is required."
        )

    try:
        evaluation_type = str(
            question.get("evaluation_type") or ""
        ).strip().upper()

        # An explicitly supplied evaluator takes priority. This permits
        # custom evaluation for open-ended questions without an evaluation_type.
        if evaluator is not None:
            return _evaluate_with_custom_evaluator(
                question=question,
                answer=answer,
                evaluator=evaluator,
            )

        # Objective scoring is permitted only with an explicit answer key.
        if evaluation_type in {"OBJECTIVE", "EXACT_MATCH", "RULE_BASED"}:
            if _has_answer_key(question):
                return _evaluate_objective(question, answer)

            if evaluation_type == "RULE_BASED":
                return _needs_review(
                    "Rule-based evaluation requires explicit rules or an "
                    "answer key and a configured evaluator."
                )

            return _needs_review(
                "Objective evaluation requires an explicit answer key."
            )

        if evaluation_type in {"RUBRIC", "RUBRIC_REVIEW", "KEYWORD_RUBRIC"}:
            if not _get_rubric(question):
                return _needs_review(
                    "Rubric evaluation requires configured evaluation criteria."
                )

            return _evaluate_rubric(question, answer)

        if evaluation_type in {"HUMAN_REVIEW", "MANUAL", "MANUAL_REVIEW"}:
            return _needs_review(
                "This question requires human review.",
                method=METHOD_NONE,
            )

        # If there is no explicit evaluation type, use an answer key only
        # when one is actually present. Do not guess a scoring strategy.
        if not evaluation_type and _has_answer_key(question):
            return _evaluate_objective(question, answer)

        if not evaluation_type and _get_rubric(question):
            return _evaluate_rubric(question, answer)

        return _needs_review(
            "No supported evaluation configuration is available for this question."
        )

    except (AnswerEvaluationError, TypeError, ValueError, ArithmeticError):
        return _needs_review(
            "Answer could not be evaluated safely. Manual review is required.",
            method=METHOD_CUSTOM if evaluator is not None else METHOD_NONE,
        )

    except Exception:
        # Do not leak internal exception details to candidate-facing reports.
        return _needs_review(
            "An unexpected evaluation error occurred. Manual review is required.",
            method=METHOD_CUSTOM if evaluator is not None else METHOD_NONE,
        )
