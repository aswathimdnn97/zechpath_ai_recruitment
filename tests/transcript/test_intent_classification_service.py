
from datetime import date

from api.service.intent_classification_service import (
    classify_candidate_answer,
)


def test_skill_intent_integration():
    result = classify_candidate_answer(
        question_text="What are your technical skills?",
        answer_text="I know Python, Django, SQL and HTML.",
        language="en",
    )

    assert result["intent"] == "SKILLS"
    assert result["extraction_performed"] is True
    assert result["answer_quality"]["status"] == "CLEAR"
    assert result["extracted_data"]["skill_count"] >= 1


def test_experience_intent_integration():
    result = classify_candidate_answer(
        question_text="Tell me about your work experience.",
        answer_text="I have worked as a Python developer for 2 years.",
        language="en",
    )

    assert result["intent"] == "EXPERIENCE"
    assert result["extraction_performed"] is True


def test_availability_intent_integration():
    result = classify_candidate_answer(
        question_text="When can you join our company?",
        answer_text="I can join immediately.",
        language="en",
    )

    assert result["intent"] == "AVAILABILITY"
    assert result["extraction_performed"] is True


def test_salary_intent_integration():
    result = classify_candidate_answer(
        question_text="What is your expected salary?",
        answer_text="I expect 6 LPA.",
        language="en",
    )

    assert result["intent"] == "SALARY"
    assert result["extraction_performed"] is True


def test_vague_answer_skips_extraction():
    result = classify_candidate_answer(
        question_text="What are your technical skills?",
        answer_text="I am not sure.",
        language="en",
    )

    assert result["answer_quality"]["status"] == "VAGUE"
    assert result["extraction_performed"] is False
    assert result["requires_review"] is True


def test_off_topic_answer_skips_extraction():
    result = classify_candidate_answer(
        question_text="What are your technical skills?",
        answer_text="I enjoy watching movies and playing cricket.",
        language="en",
    )

    assert result["extraction_performed"] is False
    assert result["requires_review"] is True
