import pytest

from api.service.intent_classification_service import (
    classify_intent,
    extract_skills,
    extract_experience,
    extract_availability,
    extract_salary,
    detect_answer_quality,
    process_candidate_answer,
)


def test_classify_skills_intent():

    question = {
        "question_id": "PYF_SKILL_001",
        "category": "SKILLS",
    }

    result = classify_intent(
        "I know Python and Django.",
        question,
    )

    assert result["category"] == "SKILLS"


def test_extract_skills():

    result = extract_skills(
        "I have worked with Python, Django, FastAPI and SQL."
    )

    assert "Python" in result
    assert "Django" in result
    assert "FastAPI" in result
    assert "SQL" in result


def test_extract_experience():

    result = extract_experience(
        "I have 3 years of experience as a Python developer."
    )

    assert result["years"] == 3.0
    assert result["role"] == "Python Developer"


def test_extract_availability():

    result = extract_availability(
        "I can join immediately."
    )

    assert result["status"] == "IMMEDIATE"


def test_extract_notice_period():

    result = extract_availability(
        "My notice period is 30 days."
    )

    assert result["notice_period"]["value"] == 30
    assert result["notice_period"]["unit"] == "DAY"


def test_extract_salary():

    result = extract_salary(
        "My expected salary is 5-7 LPA."
    )

    assert result["minimum"] == 5
    assert result["maximum"] == 7
    assert result["period"] == "YEARLY"


def test_missing_answer():

    result = detect_answer_quality(
        "",
        "SKILLS",
    )

    assert result["is_missing"] is True


def test_vague_answer():

    result = detect_answer_quality(
        "Good",
        "EXPERIENCE",
    )

    assert result["is_vague"] is True


def test_off_topic_answer():

    result = detect_answer_quality(
        "I like watching movies.",
        "SKILLS",
    )

    assert result["is_off_topic"] is True


def test_complete_semantic_answer():

    question = {
        "question_id": "PYF_SKILL_001",
        "category": "SKILLS",
    }

    result = process_candidate_answer(
        "I know Python, Django and SQL.",
        question,
    )

    assert result["question_id"] == "PYF_SKILL_001"
    assert result["intent"]["category"] == "SKILLS"
    assert "Python" in result["entities"]["skills"]
    assert isinstance(result["quality"]["issues"], list)
    


from api.service.intent_classification_service import (
    process_candidate_answer,
)


def test_experience_semantic_object():
    question = {
        "question_id": "PYF_EXP_001",
        "category": "EXPERIENCE",
        "question_text": "How many years of experience do you have?",
    }

    result = process_candidate_answer(
        "I have 3 years of experience as a Python developer.",
        question,
    )

    assert result["intent"]["category"] == "EXPERIENCE"
    assert result["entities"]["experience"]["years"] == 3.0
    assert result["entities"]["experience"]["role"] == "Python Developer"


def test_availability_semantic_object():
    question = {
        "question_id": "PYF_AVAIL_001",
        "category": "AVAILABILITY",
        "question_text": "When can you join?",
    }

    result = process_candidate_answer(
        "I can join immediately.",
        question,
    )

    assert result["intent"]["category"] == "AVAILABILITY"
    assert result["entities"]["availability"]["availability_status"] == "IMMEDIATE"


def test_salary_semantic_object():
    question = {
        "question_id": "PYF_SALARY_001",
        "category": "SALARY",
        "question_text": "What is your expected salary?",
    }

    result = process_candidate_answer(
        "My expected salary is 5-7 LPA.",
        question,
    )

    assert result["intent"]["category"] == "SALARY"
    assert result["entities"]["salary"]["expected_salary_min"] == 500000.0
    assert result["entities"]["salary"]["expected_salary_max"] == 700000.0


def test_semantic_object_preserves_evidence():
    question = {
        "question_id": "PYF_SKILL_001",
        "category": "SKILLS",
        "question_text": "What are your technical skills?",
    }

    answer = "I know Python, Django and SQL."

    result = process_candidate_answer(answer, question)

    assert result["question_id"] == "PYF_SKILL_001"
    assert result["answer"] == answer
    assert result["evidence"]["answer"] == answer
    assert result["entities"]["skills"]
    assert isinstance(result["quality"]["issues"], list)
