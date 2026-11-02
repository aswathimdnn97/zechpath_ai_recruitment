
"""
intent_classification_service.py

Responsibilities
-----------------
1. Identify candidate response intent using interview question context.
2. Assess answer quality.
3. Detect off-topic responses.
4. Route answers to the appropriate extraction service.
5. Return a unified semantic answer object.
6. Preserve extraction evidence for recruiter review.

This service coordinates existing services.
It does not duplicate their extraction logic.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional
import re

from api.service.transcript_skill_extraction_service import (
    extract_transcript_skills,
)
from api.service.experience_intent_service import (
    extract_experience_intent,
)
from api.service.availability_intent_service import (
    extract_availability_intent,
)
from api.service.salary_expectation_intent_service import (
    extract_salary_expectation_intent,
)
from api.service.off_topic_detection_service import (
    detect_off_topic_response,
)
from api.service.answer_quality_service import (
    assess_answer_quality,
)



SUPPORTED_LANGUAGES = frozenset({"en", "ml", "hi"})

INTENT_PATTERNS = {
    "SKILLS": re.compile(
        r"\b(?:technical skills|skills|programming languages|"
        r"technologies|tools|frameworks|technical knowledge)\b",
        re.IGNORECASE,
    ),
    "EXPERIENCE": re.compile(
        r"\b(?:experience|work history|professional background|"
        r"previous job|previous role|worked|how long|"
        r"how many years)\b",
        re.IGNORECASE,
    ),
    "AVAILABILITY": re.compile(
        r"\b(?:availability|available|when can you join|"
        r"joining date|notice period|join the company)\b",
        re.IGNORECASE,
    ),
    "SALARY": re.compile(
        r"\b(?:salary|expected compensation|salary expectation|"
        r"expected ctc|compensation|remuneration|pay package)\b",
        re.IGNORECASE,
    ),
}


class IntentClassificationError(ValueError):
    """Raised when intent classification input is invalid."""


def _validate_input(
    question_text: str,
    answer_text: Optional[str],
    language: str,
) -> None:
    if not isinstance(question_text, str):
        raise IntentClassificationError(
            "question_text must be a string."
        )

    if answer_text is not None and not isinstance(answer_text, str):
        raise IntentClassificationError(
            "answer_text must be a string or None."
        )

    if language not in SUPPORTED_LANGUAGES:
        raise IntentClassificationError(
            "language must be one of: en, ml, hi."
        )


def _identify_intent(question_text: str) -> str:
    """
    Identify the expected answer intent from the interview question.

    Question context is used to route the answer to the correct
    extraction service.
    """

    for intent, pattern in INTENT_PATTERNS.items():
        if pattern.search(question_text):
            return intent

    return "GENERAL"


def _should_extract(
    answer_quality: dict[str, Any],
    off_topic_result: dict[str, Any],
) -> bool:
    """
    Avoid extracting information from missing, empty, vague,
    or clearly off-topic answers.
    """

    quality_status = answer_quality.get("status")

    if quality_status in {"MISSING", "EMPTY", "VAGUE"}:
        return False

    if off_topic_result.get("is_off_topic") is True:
        return False

    if off_topic_result.get("status") in {
        "OFF_TOPIC",
        "EMPTY_ANSWER",
        "UNCLEAR",
    }:
        return False

    return True


def _extract_intent_data(
    intent: str,
    answer_text: str,
    language: str,
    reference_date: Optional[date] = None,
) -> dict[str, Any]:
    """
    Call the existing extraction service for the identified intent.
    """

    if intent == "SKILLS":
        skill_result = extract_transcript_skills({
            "original_text": answer_text,
            "normalized_text": answer_text,
            "language": language,
        })

        return {
            "skills": _get_skill_names(skill_result),
            "skill_count": skill_result.get("skill_count", 0),
            "language": skill_result.get("language"),
        }
    if intent == "EXPERIENCE":
        return extract_experience_intent(answer_text)

    if intent == "AVAILABILITY":
        return extract_availability_intent(
            transcript_text=answer_text,
            reference_date=reference_date,
        )

    if intent == "SALARY":
        return extract_salary_expectation_intent(answer_text)

    return {}



def _get_question_details(question: Any) -> dict[str, Any]:
    """Normalize a question string or question dictionary."""

    if isinstance(question, dict):
        return {
            "question_id": question.get("question_id"),
            "category": str(
                question.get("category", "GENERAL")
            ).upper(),
            "question_text": (
                question.get("question_text")
                or question.get("question")
                or question.get("category", "GENERAL")
            ),
        }

    if isinstance(question, str):
        return {
            "question_id": None,
            "category": "GENERAL",
            "question_text": question,
        }

    raise IntentClassificationError(
        "Question must be a string or dictionary."
    )



def _get_skill_names(skill_result: dict[str, Any]) -> list[str]:
    """Convert extracted skill objects into canonical skill names."""

    skills = (
        skill_result.get("recognized_skills")
        or skill_result.get("skills")
        or skill_result.get("extracted_skills")
        or []
    )

    names = []

    for item in skills:
        if isinstance(item, str):
            names.append(item)

        elif isinstance(item, dict):
            name = (
                item.get("skill")
                or item.get("canonical_name")
                or item.get("skill_name")
                or item.get("name")
            )

            if name:
                names.append(name)

    return list(dict.fromkeys(names))


def extract_skills(
    answer_text: str,
    language: str = "en",
) -> list[str]:
    """Extract canonical skill names from a candidate answer."""

    if not isinstance(answer_text, str):
        raise IntentClassificationError(
            "answer_text must be a string."
        )

    result = extract_transcript_skills({
        "original_text": answer_text,
        "normalized_text": answer_text.strip(),
        "language": language,
    })

    return _get_skill_names(result)



def extract_experience(answer_text: str) -> dict[str, Any]:
    """Extract experience and expose simplified public fields."""

    result = extract_experience_intent(answer_text)
    output = dict(result)

    output["years"] = result.get("total_experience_years")

    job_roles = result.get("job_roles", [])

    output["role"] = (
        job_roles[0].get("title")
        if job_roles and isinstance(job_roles[0], dict)
        else None
    )

    return output




def extract_availability(
    answer_text: str,
    reference_date: Optional[date] = None,
) -> dict[str, Any]:
    """Extract availability and notice-period information."""

    result = extract_availability_intent(
        transcript_text=answer_text,
        reference_date=reference_date,
    )

    output = dict(result)

    output["status"] = result.get(
        "availability_status",
        "UNKNOWN",
    )

    notice_days = result.get("notice_period_days")

    if notice_days is not None:
        output["notice_period"] = {
            "value": notice_days,
            "unit": "DAY",
        }

    return output



def extract_salary(answer_text: str) -> dict[str, Any]:
    """Extract salary and expose a simplified salary range."""

    result = extract_salary_expectation_intent(answer_text)
    output = dict(result)

    minimum = result.get("expected_salary_min")
    maximum = result.get("expected_salary_max")
    frequency = result.get("pay_frequency")

    # Convert annual INR amounts to LPA for the public API.
    if result.get("currency") == "INR" and frequency == "ANNUAL":
        if minimum is not None:
            minimum = minimum / 100000

        if maximum is not None:
            maximum = maximum / 100000

    output["minimum"] = minimum
    output["maximum"] = maximum

    output["period"] = (
        "YEARLY" if frequency == "ANNUAL" else frequency
    )

    return output


def detect_answer_quality(
    answer_text: Optional[str],
    category: str = "GENERAL",
) -> dict[str, Any]:
    """
    Assess missing, vague, incomplete and off-topic answers.

    Public argument order:
        detect_answer_quality(answer_text, category)
    """

    category = str(category).upper()
    question_text = category.replace("_", " ").lower()

    answer = answer_text or ""

    quality = assess_answer_quality(
        question_text=question_text,
        answer_text=answer,
    )

    off_topic = detect_off_topic_response(
        question_text=question_text,
        answer_text=answer,
    )

    result = dict(quality)

    status = str(quality.get("status", "")).upper()

    result["is_missing"] = status in {"MISSING", "EMPTY"}
    result["is_vague"] = status == "VAGUE"
    result["is_off_topic"] = (
        off_topic.get("is_off_topic") is True
        or off_topic.get("status") == "OFF_TOPIC"
    )

    result["off_topic_detection"] = off_topic

    return result




def classify_intent(
    first: Any,
    second: Any,
    language: str = "en",
    reference_date: Optional[date] = None,
) -> dict[str, Any]:

    # Support both argument orders.
    if isinstance(second, dict):
        answer_text = first
        question = second

    elif isinstance(first, dict):
        question = first
        answer_text = second

    else:
        raise IntentClassificationError(
            "One argument must be a question dictionary."
        )

    if answer_text is not None and not isinstance(answer_text, str):
        raise IntentClassificationError(
            "answer_text must be a string or None."
        )

    question_data = _get_question_details(question)

    result = classify_candidate_answer(
        question_text=question_data["question_text"],
        answer_text=answer_text,
        language=language,
        reference_date=reference_date,
    )

    return {
        **result,
        "question_id": question_data["question_id"],
        "category": question_data["category"],
    }

def process_candidate_answer(
    answer_text: Optional[str],
    question: Any,
    language: str = "en",
    reference_date: Optional[date] = None,
) -> dict[str, Any]:
    """
    Build the complete semantic answer expected by HR screening.
    """

    question_data = _get_question_details(question)

    result = classify_candidate_answer(
        question_text=question_data["question_text"],
        answer_text=answer_text,
        language=language,
        reference_date=reference_date,
    )

    extracted_data = result.get("extracted_data", {})
    quality = result.get("answer_quality", {})

    return {
        **result,
        "question_id": question_data["question_id"],
        "intent": {
            "category": question_data["category"],
            "type": result.get("intent"),
        },
        "entities": {
            "skills": _get_skill_names(
                {
                    "skills": extracted_data.get("skills", [])
                }
            ),
            "experience": extracted_data.get("experience", {}),
            "availability": extracted_data.get("availability", {}),
            "salary": extracted_data.get("salary", {}),
        },
        "quality": {
            "status": quality.get("status"),
            "issues": quality.get("flags", []),
            "requires_review": quality.get("requires_review", False),
        },
    }



def process_candidate_answer(
    answer_text: Optional[str],
    question: Any,
    language: str = "en",
    reference_date: Optional[date] = None,
) -> dict[str, Any]:
    """
    Build a unified semantic answer object for HR screening.
    """

    question_data = _get_question_details(question)

    result = classify_candidate_answer(
        question_text=question_data["question_text"],
        answer_text=answer_text,
        language=language,
        reference_date=reference_date,
    )

    extracted_data = result.get("extracted_data") or {}
    quality = result.get("answer_quality") or {}

    detected_intent = str(
        result.get("intent", "GENERAL")
    ).upper()

    # Keep a consistent entity structure.
    entities = {
        "skills": [],
        "experience": {},
        "availability": {},
        "salary": {},
    }

    # Map extraction output according to detected intent.
    if detected_intent == "SKILLS":
        entities["skills"] = _get_skill_names(extracted_data)

    elif detected_intent == "EXPERIENCE":
        experience_data = dict(extracted_data)

        # Map total experience to a simplified field.
        experience_data["years"] = extracted_data.get(
            "total_experience_years"
        )

        # Map the first recognized job role.
        job_roles = extracted_data.get("job_roles", [])

        experience_data["role"] = (
            job_roles[0].get("title")
            if job_roles and isinstance(job_roles[0], dict)
            else None
        )

        entities["experience"] = experience_data

    elif detected_intent == "AVAILABILITY":
        entities["availability"] = extracted_data

    elif detected_intent == "SALARY":
        entities["salary"] = extracted_data

    # Use detected intent when question category is not provided.
    category = question_data["category"]

    if category == "GENERAL":
        category = detected_intent

    # Preserve existing quality flags.
    issues = quality.get("flags", [])

    if not isinstance(issues, list):
        issues = []

    issues = list(issues)

    quality_status = str(
        quality.get("status", "UNKNOWN")
    ).upper()

    if (
        quality_status in {
            "MISSING",
            "EMPTY",
            "VAGUE",
            "INCOMPLETE",
        }
        and quality_status not in issues
    ):
        issues.append(quality_status)

    off_topic = result.get("off_topic_detection") or {}

    if (
        off_topic.get("is_off_topic") is True
        and "OFF_TOPIC" not in issues
    ):
        issues.append("OFF_TOPIC")

    requires_review = (
        result.get("requires_review", False)
        or quality.get("requires_review", False)
        or bool(issues)
    )

    return {
        **result,

        "question_id": question_data["question_id"],

        "intent": {
            "category": category,
            "type": detected_intent,
        },

        "entities": entities,

        "quality": {
            "status": quality_status,
            "issues": issues,
            "requires_review": requires_review,
        },
    }


def classify_candidate_answer(
    question_text: str,
    answer_text: Optional[str],
    language: str = "en",
    reference_date: Optional[date] = None,
) -> dict[str, Any]:
    """
    Classify and extract information from one candidate answer.

    This function coordinates the existing extraction services.
    """

    _validate_input(
        question_text=question_text,
        answer_text=answer_text,
        language=language,
    )

    question = question_text.strip()

    answer = (
        answer_text.strip()
        if isinstance(answer_text, str)
        else None
    )

    # Stage 1: Identify intent from the interview question.
    intent = _identify_intent(question)

    # Stage 2: Assess answer quality.
    quality_result = assess_answer_quality(
        question_text=question,
        answer_text=answer,
    )

    # Stage 3: Detect off-topic responses.
    off_topic_result = detect_off_topic_response(
        question_text=question,
        answer_text=answer or "",
    )

    # Stage 4: Decide whether extraction should be performed.
    should_extract = _should_extract(
        answer_quality=quality_result,
        off_topic_result=off_topic_result,
    )

    extracted_data = {}

    if should_extract:
        extracted_data = _extract_intent_data(
            intent=intent,
            answer_text=answer or "",
            language=language,
            reference_date=reference_date,
        )

    # Stage 5: Determine recruiter review requirement.
    requires_review = (
        quality_result.get("requires_review", False)
        or off_topic_result.get("is_off_topic", False)
        or quality_result.get("status") in {
            "MISSING",
            "EMPTY",
            "VAGUE",
            "INCOMPLETE",
        }
    )

    # Stage 6: Return unified classification result.
    return {
        "intent": intent,
        "answer": answer,
        "language": language,
        "extracted_data": extracted_data,
        "answer_quality": quality_result,
        "off_topic_detection": off_topic_result,
        "extraction_performed": should_extract,
        "requires_review": requires_review,
        "evidence": {
            "question": question,
            "answer": answer,
            "intent": intent,
            "answer_quality_status": quality_result.get("status"),
            "off_topic_status": off_topic_result.get("status"),
        },
    }


def process_intent_classification(
    question_text: str,
    answer_text: Optional[str],
    language: str = "en",
    reference_date: Optional[date] = None,
) -> dict[str, Any]:
    """Compatibility wrapper for the main classification service."""

    return classify_candidate_answer(
        question_text=question_text,
        answer_text=answer_text,
        language=language,
        reference_date=reference_date,
    )
    
