
import pytest
from pydantic import ValidationError

from api.schemas.hr_screening_schema import (
    ScreeningAnswerSubmission,
    ScreeningResponseSubmissionRequest,
)


def test_yes_no_answer_with_details():
    answer = ScreeningAnswerSubmission(
        question_id="Q1",
        answer="yes",
        details="I can work from the office.",
    )
    assert answer.answer == "yes"
    assert answer.details == "I can work from the office."


def test_multi_select_answer_with_details():
    answer = ScreeningAnswerSubmission(
        question_id="Q2",
        selected_options=["Python", "Django"],
        details="I used both in a project.",
    )
    assert answer.selected_options == ["Python", "Django"]


def test_currency_range_is_structured():
    answer = ScreeningAnswerSubmission(
        question_id="Q3",
        currency="inr",
        minimum_amount=400000,
        maximum_amount=600000,
    )
    assert answer.currency == "INR"
    assert answer.minimum_amount == 400000
    assert answer.maximum_amount == 600000


def test_currency_range_rejects_reversed_values():
    with pytest.raises(ValidationError):
        ScreeningAnswerSubmission(
            question_id="Q3",
            currency="INR",
            minimum_amount=600000,
            maximum_amount=400000,
        )


def test_date_or_duration_accepts_duration():
    answer = ScreeningAnswerSubmission(
        question_id="Q4",
        duration="Within 30 days",
    )
    assert answer.duration == "Within 30 days"


def test_submission_rejects_duplicate_question_ids():
    with pytest.raises(ValidationError):
        ScreeningResponseSubmissionRequest(
            answers=[
                {"question_id": "Q1", "answer": "First answer"},
                {"question_id": "q1", "answer": "Duplicate answer"},
            ],
            final_submission=False,
        )
