
import pytest

from api.service.answer_evaluator import (
    AnswerEvaluationError,
    evaluate_answer,
)


def test_open_ended_answer_needs_review_without_evaluator():
    result = evaluate_answer(
        {"question_id": "Q001", "answer_type": "TEXT"},
        {"question_id": "Q001", "answer": "I have learned Python."},
    )

    assert result["evaluation_status"] == "NEEDS_REVIEW"
    assert result["evaluation_method"] == "NONE"
    assert result["score"] is None
    assert result["max_score"] is None


def test_objective_answer_matches_case_insensitively():
    result = evaluate_answer(
        {
            "question_id": "Q002",
            "answer_type": "TEXT",
            "answer_key": "Python",
            "max_score": 2,
        },
        {"answer": "  python  "},
    )

    assert result["evaluation_status"] == "EVALUATED"
    assert result["evaluation_method"] == "OBJECTIVE"
    assert result["score"] == 2
    assert result["max_score"] == 2


def test_incorrect_objective_answer_scores_zero():
    result = evaluate_answer(
        {
            "question_id": "Q003",
            "answer_key": "Django",
            "max_score": 1,
        },
        {"answer": "Flask"},
    )

    assert result["evaluation_status"] == "EVALUATED"
    assert result["score"] == 0
    assert result["max_score"] == 1


def test_multiple_choice_answers_are_order_independent():
    result = evaluate_answer(
        {
            "question_id": "Q004",
            "answer_type": "MULTIPLE_CHOICE",
            "accepted_answers": ["Python", "Django"],
            "max_score": 3,
        },
        {"selected_options": ["Django", "Python"]},
    )

    assert result["score"] == 3
    assert result["max_score"] == 3


def test_unanswered_question_needs_review():
    result = evaluate_answer(
        {"question_id": "Q005", "answer_key": "Yes"},
        {"answer": "   ", "selected_options": None},
    )

    assert result["evaluation_status"] == "NEEDS_REVIEW"
    assert result["score"] is None


def test_custom_evaluator_scores_open_ended_answer():
    def fake_evaluator(*, question, answer):
        assert question["question_id"] == "Q006"
        assert answer["answer"]
        return {"score": 4, "feedback": "Relevant and clear answer."}

    result = evaluate_answer(
        {
            "question_id": "Q006",
            "answer_type": "TEXT",
            "max_score": 5,
        },
        {"answer": "I used Python to build an API."},
        evaluator=fake_evaluator,
    )

    assert result["evaluation_method"] == "CUSTOM"
    assert result["evaluation_status"] == "EVALUATED"
    assert result["score"] == 4
    assert result["max_score"] == 5
    assert result["feedback"] == "Relevant and clear answer."


def test_custom_evaluator_invalid_score_fails_safely():
    def fake_evaluator(*, question, answer):
        return {"score": 10, "feedback": "Invalid score"}

    result = evaluate_answer(
        {"question_id": "Q007", "max_score": 5},
        {"answer": "Some answer"},
        evaluator=fake_evaluator,
    )

    assert result["evaluation_status"] == "NEEDS_REVIEW"
    assert result["score"] is None


def test_custom_evaluator_exception_fails_safely():
    def failing_evaluator(*, question, answer):
        raise RuntimeError("Evaluator unavailable")

    result = evaluate_answer(
        {"question_id": "Q008", "max_score": 5},
        {"answer": "Some answer"},
        evaluator=failing_evaluator,
    )

    assert result["evaluation_status"] == "NEEDS_REVIEW"
    assert result["score"] is None


def test_invalid_max_score_is_rejected():
    with pytest.raises(AnswerEvaluationError):
        evaluate_answer(
            {
                "question_id": "Q009",
                "answer_key": "Python",
                "max_score": 0,
            },
            {"answer": "Python"},
        )


def test_boolean_answer_key():
    result = evaluate_answer(
        {
            "question_id": "Q010",
            "answer_type": "BOOLEAN",
            "answer_key": True,
            "max_score": 1,
        },
        {"answer": True},
    )

    assert result["score"] == 1
    assert result["evaluation_status"] == "EVALUATED"
