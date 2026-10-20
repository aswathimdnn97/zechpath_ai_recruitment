
import json
from pathlib import Path

import pytest

import api.service.hr_screening_evaluation_service as service


@pytest.fixture
def screening_storage(tmp_path, monkeypatch):
    """Create isolated storage for each persistence test."""

    sessions_dir = tmp_path / "sessions"
    responses_dir = tmp_path / "responses"
    evaluations_dir = tmp_path / "evaluations"

    sessions_dir.mkdir()
    responses_dir.mkdir()
    evaluations_dir.mkdir()

    monkeypatch.setattr(service, "SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr(service, "RESPONSES_DIR", responses_dir)
    monkeypatch.setattr(service, "EVALUATIONS_DIR", evaluations_dir)

    monkeypatch.setattr(
        service,
        "QUESTION_BANK_PATH",
        tmp_path / "question_bank_not_present.json",
    )

    session_id = "SCREEN_TEST123"

    session = {
        "session_id": session_id,
        "candidate_id": "CAN_TEST123",
        "job_id": "JOB_TEST123",
        "role_id": "PYTHON_DEV_FRESHER",
        "status": "SUBMITTED",
        "assigned_questions": [
            {
                "question_id": "PYF_TEST_001",
                "question_text": {
                    "en": "Describe your Python preparation."
                },
                "answer_type": "TEXT",
                "mandatory": True,
                "evaluation_type": "HUMAN_REVIEW",
            }
        ],
    }

    responses = {
        "session_id": session_id,
        "candidate_id": "CAN_TEST123",
        "job_id": "JOB_TEST123",
        "answers": [
            {
                "question_id": "PYF_TEST_001",
                "answer": "first answer",
            }
        ],
    }

    (sessions_dir / f"{session_id}.json").write_text(
        json.dumps(session),
        encoding="utf-8",
    )

    (responses_dir / f"{session_id}.json").write_text(
        json.dumps(responses),
        encoding="utf-8",
    )

    return {
        "session_id": session_id,
        "sessions_dir": sessions_dir,
        "responses_dir": responses_dir,
        "evaluations_dir": evaluations_dir,
    }


def fake_evaluate_question(question, answer, evaluator=None):
    """Deterministic evaluator for testing persistence behavior."""

    answer_text = answer.get("answer", "")
    score = 1 if answer_text == "first answer" else 2

    return {
        "question_id": question["question_id"],
        "mandatory": True,
        "answered": True,
        "evaluation_method": "TEST",
        "evaluation_status": "EVALUATED",
        "score": score,
        "max_score": 5,
        "feedback": "Test evaluation.",
    }


def install_fake_evaluator(monkeypatch):
    monkeypatch.setattr(
        service,
        "_evaluate_question",
        fake_evaluate_question,
    )


def test_first_evaluation_is_saved(screening_storage, monkeypatch):
    """A missing report should be evaluated and persisted."""

    install_fake_evaluator(monkeypatch)

    session_id = screening_storage["session_id"]
    report_path = (
        screening_storage["evaluations_dir"]
        / f"{session_id}.json"
    )

    report = service.evaluate_screening_session(
        session_id,
        force=False,
    )

    assert report_path.is_file()

    saved_report = json.loads(
        report_path.read_text(encoding="utf-8")
    )

    assert saved_report == report
    assert report["session_id"] == session_id
    assert report["summary"]["evaluated_questions"] == 1
    assert report["summary"]["total_score"] == 1
    assert report["summary"]["max_score"] == 5


def test_force_false_reuses_cached_report(
    screening_storage,
    monkeypatch,
):
    """A valid cached report should be reused without reevaluation."""

    install_fake_evaluator(monkeypatch)

    session_id = screening_storage["session_id"]

    first_report = service.evaluate_screening_session(
        session_id,
        force=False,
    )

    def fail_if_evaluated(*args, **kwargs):
        pytest.fail("Cached report should not be reevaluated.")

    monkeypatch.setattr(
        service,
        "_evaluate_question",
        fail_if_evaluated,
    )

    second_report = service.evaluate_screening_session(
        session_id,
        force=False,
    )

    assert second_report == first_report


def test_force_true_recalculates_and_persists_latest_result(
    screening_storage,
    monkeypatch,
):
    """Forced evaluation should use the latest submitted answer."""

    install_fake_evaluator(monkeypatch)

    session_id = screening_storage["session_id"]

    first_report = service.evaluate_screening_session(
        session_id,
        force=False,
    )

    assert first_report["summary"]["total_score"] == 1

    response_path = (
        screening_storage["responses_dir"]
        / f"{session_id}.json"
    )

    responses = json.loads(
        response_path.read_text(encoding="utf-8")
    )
    responses["answers"][0]["answer"] = "updated answer"

    response_path.write_text(
        json.dumps(responses),
        encoding="utf-8",
    )

    calls = []
    original_evaluator = service._evaluate_question

    def tracked_evaluator(question, answer, evaluator=None):
        calls.append(question["question_id"])
        return original_evaluator(
            question,
            answer,
            evaluator=evaluator,
        )

    monkeypatch.setattr(
        service,
        "_evaluate_question",
        tracked_evaluator,
    )

    forced_report = service.evaluate_screening_session(
        session_id,
        force=True,
    )

    assert calls == ["PYF_TEST_001"]
    assert forced_report["summary"]["total_score"] == 2

    saved_report = service.get_screening_evaluation(session_id)

    assert saved_report == forced_report
    assert saved_report["summary"]["total_score"] == 2


def test_saved_report_can_be_retrieved_independently(
    screening_storage,
    monkeypatch,
):
    """The saved JSON report must be readable independently."""

    install_fake_evaluator(monkeypatch)

    session_id = screening_storage["session_id"]

    created_report = service.evaluate_screening_session(
        session_id,
        force=True,
    )

    retrieved_report = service.get_screening_evaluation(
        session_id
    )

    assert retrieved_report == created_report


def test_corrupt_cached_report_raises_data_error(screening_storage):
    """Invalid cached JSON must not be returned as a valid report."""

    session_id = screening_storage["session_id"]

    report_path = (
        screening_storage["evaluations_dir"]
        / f"{session_id}.json"
    )

    report_path.write_text(
        "{invalid-json",
        encoding="utf-8",
    )

    with pytest.raises(service.ScreeningDataError):
        service.evaluate_screening_session(
            session_id,
            force=False,
        )


def test_failed_persistence_does_not_return_success(
    screening_storage,
    monkeypatch,
):
    """A report write failure must propagate as an error."""

    install_fake_evaluator(monkeypatch)

    session_id = screening_storage["session_id"]

    def fail_write(path: Path, data: dict):
        raise service.ScreeningEvaluationError(
            "Simulated persistence failure."
        )

    monkeypatch.setattr(
        service,
        "_write_json_atomic",
        fail_write,
    )

    with pytest.raises(service.ScreeningEvaluationError):
        service.evaluate_screening_session(
            session_id,
            force=True,
        )

    report_path = (
        screening_storage["evaluations_dir"]
        / f"{session_id}.json"
    )

    assert not report_path.exists()
