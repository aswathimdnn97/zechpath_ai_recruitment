
import pytest

from api.service.off_topic_detection_service import (
    detect_off_topic_response,
    process_off_topic_detection,
)


# ---------------------------------------------------------
# Relevant Answers
# ---------------------------------------------------------

def test_relevant_python_experience_answer():
    result = detect_off_topic_response(
        "What is your experience with Python?",
        "I have developed web applications using Django and Flask for two years.",
    )

    assert result["status"] == "ON_TOPIC"
    assert result["is_off_topic"] is False
    assert result["relevance_score"] >= 0.65


def test_relevant_sql_answer():
    result = detect_off_topic_response(
        "Do you have experience with SQL databases?",
        "I have worked with MySQL and PostgreSQL and written database queries.",
    )

    assert result["status"] == "ON_TOPIC"
    assert result["is_off_topic"] is False


def test_relevant_availability_answer():
    result = detect_off_topic_response(
        "When can you join the company?",
        "I can join immediately after my notice period.",
    )

    assert result["status"] == "ON_TOPIC"


def test_relevant_salary_answer():
    result = detect_off_topic_response(
        "What is your expected salary?",
        "I am looking for 8 LPA.",
    )

    assert result["status"] == "ON_TOPIC"


def test_relevant_education_answer():
    result = detect_off_topic_response(
        "What is your educational qualification?",
        "I completed BTech in Electronics Engineering.",
    )

    assert result["status"] == "ON_TOPIC"


def test_relevant_project_answer():
    result = detect_off_topic_response(
        "Tell me about your Python projects.",
        "I built a Python application using Django and MySQL.",
    )

    assert result["status"] == "ON_TOPIC"


def test_relevant_fresher_experience_answer():
    result = detect_off_topic_response(
        "How much professional experience do you have?",
        "I am a fresher and have completed two academic projects.",
    )

    assert result["status"] == "ON_TOPIC"


def test_relevant_introduction_answer():
    result = detect_off_topic_response(
        "Tell me about yourself.",
        "I completed BTech and have experience building Python projects.",
    )

    assert result["status"] == "ON_TOPIC"


# ---------------------------------------------------------
# Partially Relevant Answers
# ---------------------------------------------------------

def test_partially_relevant_python_answer():
    result = detect_off_topic_response(
        "Explain your Python experience and the projects you developed.",
        "I have learned Python basics.",
    )

    assert result["status"] == "PARTIALLY_RELEVANT"
    assert result["requires_review"] is True


def test_partially_relevant_answer():
    result = detect_off_topic_response(
        "What are your technical skills and work experience?",
        "I know Python and HTML.",
    )

    assert result["status"] == "PARTIALLY_RELEVANT"


# ---------------------------------------------------------
# Off-topic Answers
# ---------------------------------------------------------

def test_completely_unrelated_answer():
    result = detect_off_topic_response(
        "What is your experience with Python?",
        "I enjoy travelling and watching movies.",
    )

    assert result["status"] == "OFF_TOPIC"
    assert result["is_off_topic"] is True
    assert result["requires_review"] is True


def test_unrelated_personal_answer():
    result = detect_off_topic_response(
        "What is your expected salary?",
        "My favourite food is biryani.",
    )

    assert result["status"] == "OFF_TOPIC"
    assert result["is_off_topic"] is True


def test_unrelated_answer_to_sql_question():
    result = detect_off_topic_response(
        "Explain your SQL knowledge.",
        "I completed my graduation in 2022.",
    )

    assert result["status"] == "OFF_TOPIC"


# ---------------------------------------------------------
# Empty Answers
# ---------------------------------------------------------

def test_empty_answer():
    result = detect_off_topic_response(
        "What is your Python experience?",
        "",
    )

    assert result["status"] == "EMPTY_ANSWER"
    assert result["is_off_topic"] is False
    assert result["requires_review"] is True


def test_whitespace_answer():
    result = detect_off_topic_response(
        "What is your Python experience?",
        "   ",
    )

    assert result["status"] == "EMPTY_ANSWER"


# ---------------------------------------------------------
# Unclear Answers
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "answer",
    [
        "Yes",
        "No",
        "Maybe",
        "I don't know",
        "I am not sure",
        "No idea",
    ],
)
def test_unclear_answers(answer):
    result = detect_off_topic_response(
        "What is your Python experience?",
        answer,
    )

    assert result["status"] == "UNCLEAR"
    assert result["is_off_topic"] is False
    assert result["requires_review"] is True


# ---------------------------------------------------------
# Input Validation
# ---------------------------------------------------------

def test_missing_question():
    result = detect_off_topic_response(
        "",
        "I have two years of Python experience.",
    )

    assert result["status"] == "UNCLEAR"
    assert result["requires_review"] is True


def test_missing_both_question_and_answer():
    result = detect_off_topic_response(
        "",
        "",
    )

    assert result["status"] == "UNCLEAR"


def test_non_string_answer():
    result = detect_off_topic_response(
        "What is your Python experience?",
        None,
    )

    assert result["status"] == "EMPTY_ANSWER"


# ---------------------------------------------------------
# Structured Output
# ---------------------------------------------------------

def test_response_contains_required_semantic_fields():
    result = detect_off_topic_response(
        "What is your Python experience?",
        "I have worked with Django for two years.",
    )

    required_fields = {
        "intent",
        "status",
        "is_off_topic",
        "relevance_score",
        "reason",
        "confidence",
        "requires_review",
        "evidence",
    }

    assert required_fields.issubset(result.keys())


def test_evidence_contains_question_and_answer():
    question = "What is your Python experience?"
    answer = "I have worked with Django."

    result = detect_off_topic_response(
        question,
        answer,
    )

    assert result["evidence"]["question"] == question
    assert result["evidence"]["answer"] == answer
    assert "matched_terms" in result["evidence"]


def test_compatibility_function():
    result = process_off_topic_detection(
        "What is your Python experience?",
        "I have worked with Django for two years.",
    )

    assert result["intent"] == "OFF_TOPIC_DETECTION"
    assert result["status"] == "ON_TOPIC"
