import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.hr_screenig_response_router import router
import api.service.screening_response_service as service


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Create an isolated FastAPI application and temporary screening storage.
    """

    sessions_dir = tmp_path / "sessions"
    responses_dir = tmp_path / "responses"

    sessions_dir.mkdir()
    responses_dir.mkdir()

    monkeypatch.setattr(service, "SESSION_DIR", sessions_dir)
    monkeypatch.setattr(service, "RESPONSE_DIR", responses_dir)

    app = FastAPI()
    app.include_router(router)

    return TestClient(app)


@pytest.fixture
def screening_session(tmp_path):
    """
    Create a screening session with one mandatory text question.
    """

    sessions_dir = tmp_path / "sessions"

    session = {
        "session_id": "SCREEN_001",
        "candidate_id": "CAN_123456789ABC",
        "job_id": "JOB_BF2FEFE4A4A3",
        "role_id": "PYTHON_DEV_FRESHER",
        "status": "CREATED",
        "questions": [
            {
                "question_id": "PYTHON_Q001",
                "mandatory": True,
                "answer_type": "TEXT",
                "question": "What is Python?",
            }
        ],
    }

    sessions_dir.mkdir(parents=True, exist_ok=True)

    (sessions_dir / "SCREEN_001.json").write_text(
        json.dumps(session),
        encoding="utf-8",
    )

    return session


def test_submit_screening_draft(
    client,
    screening_session,
    tmp_path,
):
    """A candidate can save a valid draft."""

    response = client.post(
        "/hr-screening/sessions/SCREEN_001/responses",
        params={"candidate_id": "CAN_123456789ABC"},
        json={
            "answers": [
                {
                    "question_id": "PYTHON_Q001",
                    "answer": "Python is a high-level programming language.",
                }
            ],
            "final_submission": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["session_id"] == "SCREEN_001"
    assert data["status"] == "IN_PROGRESS"
    assert data["submitted_answers"] == 1
    assert data["answered_questions"] == 1
    assert data["answered_mandatory_questions"] == 1

    saved_response = json.loads(
        (
            tmp_path
            / "responses"
            / "SCREEN_001.json"
        ).read_text(encoding="utf-8")
    )

    assert "PYTHON_Q001" in saved_response["answers"]


def test_submit_response_for_unknown_session(client):
    """A nonexistent session returns HTTP 404."""

    response = client.post(
        "/hr-screening/sessions/SCREEN_999/responses",
        params={"candidate_id": "CAN_123456789ABC"},
        json={
            "answers": [
                {
                    "question_id": "PYTHON_Q001",
                    "answer": "Python",
                }
            ],
            "final_submission": False,
        },
    )

    assert response.status_code == 404



def test_get_unknown_screening_session(client):
    """A valid-format but nonexistent session returns HTTP 404."""

    response = client.get(
        "/hr-screening/sessions/SCREEN_999/responses",
        params={"candidate_id": "CAN_123456789ABC"},
    )

    assert response.status_code == 404



def test_reject_candidate_who_does_not_own_session(
    client,
    screening_session,
):
    """A different candidate cannot submit answers to this session."""

    response = client.post(
        "/hr-screening/sessions/SCREEN_001/responses",
        params={"candidate_id": "CAN_OTHER123456"},
        json={
            "answers": [
                {
                    "question_id": "PYTHON_Q001",
                    "answer": "Python",
                }
            ],
            "final_submission": False,
        },
    )

    assert response.status_code == 403


def test_reject_unassigned_question(
    client,
    screening_session,
):
    """A candidate cannot answer a question outside the assigned session."""

    response = client.post(
        "/hr-screening/sessions/SCREEN_001/responses",
        params={"candidate_id": "CAN_123456789ABC"},
        json={
            "answers": [
                {
                    "question_id": "UNASSIGNED_Q999",
                    "answer": "Unexpected answer",
                }
            ],
            "final_submission": False,
        },
    )

    assert response.status_code == 422


def test_final_submission_requires_mandatory_answers(
    client,
    screening_session,
):
    """Final submission without a mandatory answer is rejected."""

    response = client.post(
        "/hr-screening/sessions/SCREEN_001/responses",
        params={"candidate_id": "CAN_123456789ABC"},
        json={
            "answers": [],
            "final_submission": True,
        },
    )

    assert response.status_code == 422


def test_get_screening_response_status(
    client,
    screening_session,
):
    """Response status can be retrieved by the session owner."""

    submit_response = client.post(
        "/hr-screening/sessions/SCREEN_001/responses",
        params={"candidate_id": "CAN_123456789ABC"},
        json={
            "answers": [
                {
                    "question_id": "PYTHON_Q001",
                    "answer": "Python supports object-oriented programming.",
                }
            ],
            "final_submission": False,
        },
    )

    assert submit_response.status_code == 200

    response = client.get(
        "/hr-screening/sessions/SCREEN_001/responses",
        params={"candidate_id": "CAN_123456789ABC"},
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert data["session_id"] == "SCREEN_001"

    # The retrieval endpoint should return status, not answer content.
    assert "Python supports object-oriented programming." not in response.text


def test_get_screening_responses_rejects_wrong_candidate(
    client,
    screening_session,
):
    """A different candidate cannot retrieve another candidate's status."""

    response = client.get(
        "/hr-screening/sessions/SCREEN_001/responses",
        params={"candidate_id": "CAN_OTHER123456"},
    )

    assert response.status_code == 403


