
import pytest

from api.service.question_bank_service import (
    validate_question_data,
    get_candidate_questions,
    get_candidate_question,
    get_question_templates,
)


def test_question_data_is_valid():
    result = validate_question_data()

    assert result["question_count"] > 0
    assert result["template_count"] > 0
    assert result["role_count"] > 0


def test_get_questions_for_python_fresher():
    questions = get_candidate_questions(
        role_id="PYTHON_DEV_FRESHER",
        language="en",
    )

    assert len(questions) > 0
    assert all(
        question["role_id"] == "PYTHON_DEV_FRESHER"
        for question in questions
    )


def test_filter_by_category():
    questions = get_candidate_questions(
        role_id="PYTHON_DEV_FRESHER",
        language="en",
        category="SKILLS",
    )

    assert len(questions) > 0
    assert all(
        question["category"] == "SKILLS"
        for question in questions
    )


def test_mandatory_questions_only():
    questions = get_candidate_questions(
        role_id="PYTHON_DEV_FRESHER",
        language="en",
        include_optional=False,
    )

    assert len(questions) > 0
    assert all(question["mandatory"] for question in questions)


def test_candidate_response_excludes_scoring_metadata():
    questions = get_candidate_questions(
        role_id="PYTHON_DEV_FRESHER",
        language="en",
    )

    internal_fields = {
        "scoring_importance",
        "evaluation_type",
        "translation_status",
    }

    for question in questions:
        assert internal_fields.isdisjoint(question.keys())


def test_get_one_question():
    questions = get_candidate_questions(
        role_id="PYTHON_DEV_FRESHER",
        language="en",
    )

    question = get_candidate_question(
        question_id=questions[0]["question_id"],
        language="en",
    )

    assert question is not None
    assert question["question_id"] == questions[0]["question_id"]


def test_unknown_role_is_rejected():
    with pytest.raises(ValueError):
        get_candidate_questions(
            role_id="UNKNOWN_ROLE",
            language="en",
        )


def test_templates_can_be_filtered():
    templates = get_question_templates(
        category="SKILLS",
        active_only=True,
    )

    assert all(template["category"] == "SKILLS" for template in templates)
    assert all(template["active"] for template in templates)


from api.service.question_bank_service import get_candidate_questions

questions = get_candidate_questions(
    role_id="PYTHON_DEV_FRESHER",
    language="ml",
)

print("Question count:", len(questions))

if questions:
    print("Question:", questions[0]["question_text"])
    print("Language:", questions[0]["language"])
    print("Fallback:", questions[0]["translation_fallback"])
    print("Options:", questions[0].get("options"))