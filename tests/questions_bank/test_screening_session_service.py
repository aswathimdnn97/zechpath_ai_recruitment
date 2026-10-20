import json
import re

import pytest

import api.service.screening_session_service as service


@pytest.fixture
def mock_question_bank(monkeypatch):
    """Provide predictable questions without reading the real question bank."""

    questions = [
        {
            "question_id": "PYTHON_Q001",
            "question": "What is Python?",
            "answer_type": "TEXT",
            "mandatory": True,
            "category": "technical",
        },
        {
            "question_id": "PYTHON_Q002",
            "question": "Explain a Python list.",
            "answer_type": "TEXT",
            "mandatory": False,
            "category": "technical",
        },
    ]

    calls = []

    def fake_get_candidate_questions(
        *,
        role_id,
        language,
        category,
        include_optional,
    ):
        calls.append(
            {
                "role_id": role_id,
                "language": language,
                "category": category,
                "include_optional": include_optional,
            }
        )

        selected = questions

        if category is not None:
            selected = [
                question
                for question in selected
                if question["category"] == category
            ]

        if not include_optional:
            selected = [
                question
                for question in selected
                if question["mandatory"]
            ]

        return selected

    monkeypatch.setattr(
        service,
        "get_candidate_questions",
        fake_get_candidate_questions,
    )

    return questions, calls


@pytest.fixture
def session_storage(tmp_path, monkeypatch):
    """Redirect session files to a temporary directory."""

    session_dir = tmp_path / "sessions"
    session_dir.mkdir()

    monkeypatch.setattr(service, "SESSION_DIR", session_dir)

    return session_dir


def test_create_screening_session_success(
    mock_question_bank,
    session_storage,
):
    """A session is created, assigned an ID, and saved as JSON."""

    session = service.create_screening_session(
        candidate_id="CAN_123456789ABC",
        job_id="JOB_BF2FEFE4A4A3",
        role_id="PYTHON_DEV_FRESHER",
        language="en",
        include_optional=False,
    )

    assert session["session_id"].startswith("SCREEN_")
    assert re.fullmatch(
        r"SCREEN_[A-F0-9]{12}",
        session["session_id"],
    )

    assert session["candidate_id"] == "CAN_123456789ABC"
    assert session["job_id"] == "JOB_BF2FEFE4A4A3"
    assert session["role_id"] == "PYTHON_DEV_FRESHER"
    assert session["status"] == "CREATED"

    # Optional questions are excluded by the mocked question bank.
    assert session["total_questions"] == 1
    assert session["mandatory_questions"] == 1
    assert session["questions"][0]["question_id"] == "PYTHON_Q001"

    saved_file = (
        session_storage / f"{session['session_id']}.json"
    )

    assert saved_file.exists()

    saved_session = json.loads(
        saved_file.read_text(encoding="utf-8")
    )

    assert saved_session["session_id"] == session["session_id"]
    assert saved_session["candidate_id"] == "CAN_123456789ABC"
    assert saved_session["status"] == "CREATED"


def test_create_screening_session_filters_and_deduplicates_categories(
    mock_question_bank,
    session_storage,
):
    """Repeated categories do not duplicate assigned questions."""

    _, calls = mock_question_bank

    session = service.create_screening_session(
        candidate_id="CAN_123456789ABC",
        job_id="JOB_BF2FEFE4A4A3",
        role_id="PYTHON_DEV_FRESHER",
        categories=["technical", "technical"],
        include_optional=True,
    )

    assert len(calls) == 1
    assert calls[0]["category"] == "technical"

    question_ids = [
        question["question_id"]
        for question in session["questions"]
    ]

    assert question_ids == ["PYTHON_Q001", "PYTHON_Q002"]
    assert len(question_ids) == len(set(question_ids))


def test_create_screening_session_rejects_empty_candidate_id(
    mock_question_bank,
    session_storage,
):
    """Invalid candidate identifiers are rejected."""

    with pytest.raises(service.ScreeningSessionValidationError):
        service.create_screening_session(
            candidate_id=" ",
            job_id="JOB_BF2FEFE4A4A3",
            role_id="PYTHON_DEV_FRESHER",
        )


def test_create_screening_session_rejects_empty_question_bank(
    monkeypatch,
    session_storage,
):
    """A session cannot be created without usable questions."""

    monkeypatch.setattr(
        service,
        "get_candidate_questions",
        lambda **kwargs: [],
    )

    with pytest.raises(service.ScreeningQuestionsUnavailableError):
        service.create_screening_session(
            candidate_id="CAN_123456789ABC",
            job_id="JOB_BF2FEFE4A4A3",
            role_id="PYTHON_DEV_FRESHER",
        )

    assert list(session_storage.glob("*.json")) == []


def test_create_screening_session_handles_storage_failure(
    mock_question_bank,
    monkeypatch,
    session_storage,
):
    """Storage errors are reported instead of returning a fake session."""

    def fail_write(path, payload):
        raise service.ScreeningSessionStorageError(
            "Unable to save the screening session."
        )

    monkeypatch.setattr(service, "_write_json_atomic", fail_write)

    with pytest.raises(service.ScreeningSessionStorageError):
        service.create_screening_session(
            candidate_id="CAN_123456789ABC",
            job_id="JOB_BF2FEFE4A4A3",
            role_id="PYTHON_DEV_FRESHER",
        )
