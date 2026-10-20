
"""Tests for the ZechPath HR screening evaluation service."""

import json
from pathlib import Path

import pytest

from api.service import hr_screening_evaluation_service as service
from api.service.hr_screening_evaluation_service import (
    _extract_answers,
    ScreeningDataError,
)


@pytest.fixture
def screening_storage(tmp_path, monkeypatch):
    """Isolate all evaluation files inside a temporary directory."""
    root = tmp_path / "hr_screening"

    sessions = root / "sessions"
    responses = root / "responses"
    evaluations = root / "evaluations"

    sessions.mkdir(parents=True)
    responses.mkdir(parents=True)
    evaluations.mkdir(parents=True)

    monkeypatch.setattr(service, "SESSIONS_DIR", sessions)
    monkeypatch.setattr(service, "RESPONSES_DIR", responses)
    monkeypatch.setattr(service, "EVALUATIONS_DIR", evaluations)
    monkeypatch.setattr(
        service,
        "QUESTION_BANK_PATH",
        root / "question_bank.json",
    )

    return {
        "root": root,
        "sessions": sessions,
        "responses": responses,
        "evaluations": evaluations,
    }


@pytest.fixture
def valid_session():
    return {
        "session_id": "SCREEN_TEST001",
        "candidate_id": "CAN_TEST001",
        "job_id": "JOB_TEST001",
        "role_id": "PYTHON_DEV_FRESHER",
        "status": "SUBMITTED",
        "assigned_questions": [
            {
                "question_id": "Q001",
                "question_text": "Which language is used?",
                "question_type": "MCQ",
                "mandatory": True,
                "correct_option_ids": ["A"],
                "max_score": 2,
            },
            {
                "question_id": "Q002",
                "question_text": "What is Python?",
                "question_type": "TEXT",
                "mandatory": False,
            },
        ],
    }


@pytest.fixture
def valid_responses():
    return {
        "session_id": "SCREEN_TEST001",
        "candidate_id": "CAN_TEST001",
        "job_id": "JOB_TEST001",
        "answers": [
            {
                "question_id": "Q001",
                "selected_option": "A",
            },
            {
                "question_id": "Q002",
                "answer": "Python is a programming language.",
            },
        ],
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )


def seed_files(storage, session, responses):
    """Write a session and response document using the service schema."""
    write_json(
        storage["sessions"] / f"{session['session_id']}.json",
        session,
    )
    write_json(
        storage["responses"] / f"{session['session_id']}.json",
        responses,
    )


def test_evaluate_submitted_session_and_save_report(
    screening_storage,
    valid_session,
    valid_responses,
):
    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session("SCREEN_TEST001")

    assert report["session_id"] == "SCREEN_TEST001"
    assert report["candidate_id"] == "CAN_TEST001"
    assert report["job_id"] == "JOB_TEST001"
    assert report["status"] == "NEEDS_REVIEW"

    # Q001 is evaluated objectively; Q002 requires review.
    assert report["summary"]["total_questions"] == 2
    assert report["summary"]["answered_questions"] == 2
    assert report["summary"]["mandatory_questions"] == 1
    assert report["summary"]["answered_mandatory_questions"] == 1
    assert report["summary"]["evaluated_questions"] == 1
    assert report["summary"]["total_score"] == 2.0
    assert report["summary"]["max_score"] == 2.0
    assert report["summary"]["score_percentage"] == 100.0

    report_path = (
        screening_storage["evaluations"] / "SCREEN_TEST001.json"
    )
    assert report_path.is_file()

    saved_report = json.loads(
        report_path.read_text(encoding="utf-8")
    )
    assert saved_report["evaluation_id"] == report["evaluation_id"]


def test_correct_objective_answer_receives_full_score(
    screening_storage,
    valid_session,
    valid_responses,
):
    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session("SCREEN_TEST001")

    result = next(
        item for item in report["question_results"]
        if item["question_id"] == "Q001"
    )

    assert result["evaluation_status"] == "EVALUATED"
    assert result["evaluation_method"] == "EXACT_MATCH"
    assert result["score"] == 2.0
    assert result["max_score"] == 2.0


def test_incorrect_objective_answer_receives_zero_score(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_responses["answers"][0]["selected_option"] = "B"
    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session("SCREEN_TEST001")

    result = next(
        item for item in report["question_results"]
        if item["question_id"] == "Q001"
    )

    assert result["evaluation_status"] == "EVALUATED"
    assert result["score"] == 0.0
    assert result["max_score"] == 2.0


def test_objective_answer_comparison_is_case_insensitive(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_session["assigned_questions"][0][
        "correct_option_ids"
    ] = ["Python"]

    valid_responses["answers"][0]["selected_option"] = "python"
    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session("SCREEN_TEST001")

    result = report["question_results"][0]
    assert result["score"] == 2.0


def test_open_ended_answer_requires_manual_review(
    screening_storage,
    valid_session,
    valid_responses,
):
    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session("SCREEN_TEST001")

    result = next(
        item for item in report["question_results"]
        if item["question_id"] == "Q002"
    )

    assert result["answered"] is True
    assert result["evaluation_status"] == "NEEDS_REVIEW"
    assert result["score"] is None
    assert report["decision"]["recommendation"] == "MANUAL_REVIEW"
    assert report["decision"]["automatic_rejection"] is False


def test_missing_mandatory_answer_requires_review(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_responses["answers"] = [
        valid_responses["answers"][1]
    ]
    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session("SCREEN_TEST001")

    assert report["status"] == "NEEDS_REVIEW"
    assert report["summary"]["unanswered_mandatory_questions"] == ["Q001"]
    assert report["summary"]["answered_mandatory_questions"] == 0


def test_unanswered_optional_question_is_recorded(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_responses["answers"] = [
        valid_responses["answers"][0]
    ]
    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session("SCREEN_TEST001")

    optional_result = next(
        item for item in report["question_results"]
        if item["question_id"] == "Q002"
    )

    assert optional_result["answered"] is False
    assert optional_result["evaluation_status"] == "UNANSWERED"
    assert report["summary"]["unanswered_mandatory_questions"] == []


def test_all_objective_answers_can_complete_evaluation(
    screening_storage,
):
    session = {
        "session_id": "SCREEN_TEST001",
        "candidate_id": "CAN_TEST001",
        "status": "SUBMITTED",
        "assigned_questions": [
            {
                "question_id": "Q001",
                "mandatory": True,
                "correct_option_ids": ["A"],
                "max_score": 1,
            },
            {
                "question_id": "Q002",
                "mandatory": False,
                "correct_option_ids": ["B"],
                "max_score": 1,
            },
        ],
    }
    responses = {
        "session_id": "SCREEN_TEST001",
        "answers": [
            {"question_id": "Q001", "selected_option": "A"},
            {"question_id": "Q002", "selected_option": "B"},
        ],
    }
    seed_files(screening_storage, session, responses)

    report = service.evaluate_screening_session("SCREEN_TEST001")

    assert report["status"] == "COMPLETED"
    assert report["summary"]["score_percentage"] == 100.0
    assert report["summary"]["questions_needing_review"] == 0


def test_non_submitted_session_is_rejected(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_session["status"] = "IN_PROGRESS"
    seed_files(screening_storage, valid_session, valid_responses)

    with pytest.raises(service.InvalidScreeningStateError):
        service.evaluate_screening_session("SCREEN_TEST001")


def test_missing_session_raises_error(screening_storage):
    with pytest.raises(service.ScreeningSessionNotFoundError):
        service.evaluate_screening_session("SCREEN_TEST001")


def test_missing_response_document_raises_error(
    screening_storage,
    valid_session,
):
    write_json(
        screening_storage["sessions"] / "SCREEN_TEST001.json",
        valid_session,
    )

    with pytest.raises(service.ScreeningResponseNotFoundError):
        service.evaluate_screening_session("SCREEN_TEST001")


def test_response_session_id_mismatch_is_rejected(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_responses["session_id"] = "SCREEN_OTHER"
    seed_files(screening_storage, valid_session, valid_responses)

    with pytest.raises(service.ScreeningDataError):
        service.evaluate_screening_session("SCREEN_TEST001")


def test_candidate_id_mismatch_is_rejected(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_responses["candidate_id"] = "CAN_OTHER"
    seed_files(screening_storage, valid_session, valid_responses)

    with pytest.raises(service.ScreeningDataError):
        service.evaluate_screening_session("SCREEN_TEST001")


def test_duplicate_answers_are_rejected(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_responses["answers"].append(
        {"question_id": "Q001", "selected_option": "A"}
    )
    seed_files(screening_storage, valid_session, valid_responses)

    with pytest.raises(service.ScreeningDataError):
        service.evaluate_screening_session("SCREEN_TEST001")


def test_unassigned_question_answer_is_rejected(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_responses["answers"].append(
        {"question_id": "Q999", "answer": "Unexpected"}
    )
    seed_files(screening_storage, valid_session, valid_responses)

    with pytest.raises(service.ScreeningDataError):
        service.evaluate_screening_session("SCREEN_TEST001")


def test_invalid_session_id_is_rejected(screening_storage):
    with pytest.raises(ValueError):
        service.evaluate_screening_session("../invalid")


def test_custom_evaluator_scores_open_ended_answer(
    screening_storage,
    valid_session,
    valid_responses,
):
    def evaluator(*, question, answer):
        assert question["question_id"] == "Q002"
        assert answer["answer"]
        return {
            "score": 4,
            "max_score": 5,
            "method": "TEST_EVALUATOR",
            "status": "EVALUATED",
            "feedback": "Relevant answer; some details could improve.",
        }

    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session(
        "SCREEN_TEST001",
        evaluator=evaluator,
    )

    result = next(
        item for item in report["question_results"]
        if item["question_id"] == "Q002"
    )

    assert result["evaluation_status"] == "EVALUATED"
    assert result["evaluation_method"] == "TEST_EVALUATOR"
    assert result["score"] == 4.0
    assert result["max_score"] == 5.0
    assert report["summary"]["total_score"] == 6.0
    assert report["summary"]["max_score"] == 7.0
    assert report["summary"]["score_percentage"] == pytest.approx(85.71)


def test_invalid_custom_evaluator_score_requires_review(
    screening_storage,
    valid_session,
    valid_responses,
):
    def evaluator(*, question, answer):
        return {
            "score": 10,
            "max_score": 5,
            "status": "EVALUATED",
        }

    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session(
        "SCREEN_TEST001",
        evaluator=evaluator,
    )

    result = next(
        item for item in report["question_results"]
        if item["question_id"] == "Q002"
    )

    assert result["evaluation_status"] == "NEEDS_REVIEW"
    assert result["score"] is None
    assert report["status"] == "NEEDS_REVIEW"


def test_custom_evaluator_exception_does_not_crash(
    screening_storage,
    valid_session,
    valid_responses,
):
    def evaluator(*, question, answer):
        raise RuntimeError("Evaluator unavailable")

    seed_files(screening_storage, valid_session, valid_responses)

    report = service.evaluate_screening_session(
        "SCREEN_TEST001",
        evaluator=evaluator,
    )

    result = next(
        item for item in report["question_results"]
        if item["question_id"] == "Q002"
    )

    assert result["evaluation_status"] == "NEEDS_REVIEW"
    assert "manual review" in result["feedback"].lower()


def test_existing_report_is_returned_without_re_evaluation(
    screening_storage,
    valid_session,
    valid_responses,
):
    seed_files(screening_storage, valid_session, valid_responses)

    original = service.evaluate_screening_session("SCREEN_TEST001")

    def should_not_run(*, question, answer):
        raise AssertionError("Evaluator should not run for cached report")

    cached = service.evaluate_screening_session(
        "SCREEN_TEST001",
        evaluator=should_not_run,
    )

    assert cached == original


def test_force_re_evaluates_existing_report(
    screening_storage,
    valid_session,
    valid_responses,
):
    seed_files(screening_storage, valid_session, valid_responses)

    first = service.evaluate_screening_session("SCREEN_TEST001")

    def evaluator(*, question, answer):
        return {
            "score": 3,
            "max_score": 3,
            "method": "FORCED_TEST",
            "status": "EVALUATED",
        }

    second = service.evaluate_screening_session(
        "SCREEN_TEST001",
        evaluator=evaluator,
        force=True,
    )

    assert second["question_results"][1]["evaluation_method"] == "FORCED_TEST"
    assert second["summary"]["total_score"] == 5.0
    assert second["summary"]["max_score"] == 5.0
    assert second["evaluation_id"] == first["evaluation_id"]


def test_get_saved_evaluation(
    screening_storage,
    valid_session,
    valid_responses,
):
    seed_files(screening_storage, valid_session, valid_responses)

    original = service.evaluate_screening_session("SCREEN_TEST001")
    retrieved = service.get_screening_evaluation("SCREEN_TEST001")

    assert retrieved == original


def test_get_missing_evaluation_raises_error(screening_storage):
    with pytest.raises(service.ScreeningEvaluationError):
        service.get_screening_evaluation("SCREEN_TEST001")


def test_invalid_max_score_is_rejected(
    screening_storage,
    valid_session,
    valid_responses,
):
    valid_session["assigned_questions"][0]["max_score"] = -1
    seed_files(screening_storage, valid_session, valid_responses)

    with pytest.raises(service.ScreeningDataError):
        service.evaluate_screening_session("SCREEN_TEST001")


def test_empty_question_list_is_rejected(screening_storage):
    session = {
        "session_id": "SCREEN_TEST001",
        "candidate_id": "CAN_TEST001",
        "status": "SUBMITTED",
        "assigned_questions": [],
    }
    responses = {
        "session_id": "SCREEN_TEST001",
        "answers": [],
    }
    seed_files(screening_storage, session, responses)

    with pytest.raises(service.ScreeningDataError):
        service.evaluate_screening_session("SCREEN_TEST001")






def test_extract_answers_from_dictionary_format():
    response_data = {
        "answers": {
            "Q001": {
                "question_id": "Q001",
                "answer": "Python developer",
            },
            "Q002": {
                "question_id": "Q002",
                "answer": "I learned Django",
            },
        }
    }

    answers = _extract_answers(response_data)

    assert len(answers) == 2
    assert answers[0]["question_id"] == "Q001"
    assert answers[1]["question_id"] == "Q002"


def test_extract_answers_uses_dictionary_key_as_question_id():
    response_data = {
        "answers": {
            "Q001": {
                "answer": "Python developer",
            }
        }
    }

    answers = _extract_answers(response_data)

    assert answers == [
        {
            "question_id": "Q001",
            "answer": "Python developer",
        }
    ]


def test_extract_answers_from_list_format():
    response_data = {
        "answers": [
            {
                "question_id": "Q001",
                "answer": "Python developer",
            }
        ]
    }

    answers = _extract_answers(response_data)

    assert len(answers) == 1
    assert answers[0]["question_id"] == "Q001"


def test_extract_answers_rejects_invalid_answers_format():
    response_data = {
        "answers": "invalid",
    }

    try:
        _extract_answers(response_data)
        assert False, "Expected ScreeningDataError"
    except ScreeningDataError:
        pass
