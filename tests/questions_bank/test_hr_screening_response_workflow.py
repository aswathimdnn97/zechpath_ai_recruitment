import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.hr_screenig_response_router import router
from api.service import screening_response_service as response_service


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create an isolated FastAPI app and screening storage."""

    session_dir = tmp_path / "sessions"
    response_dir = tmp_path / "responses"

    session_dir.mkdir()
    response_dir.mkdir()

    monkeypatch.setattr(
        response_service,
        "SESSION_DIR",
        session_dir,
    )
    monkeypatch.setattr(
        response_service,
        "RESPONSE_DIR",
        response_dir,
    )

    app = FastAPI()
    app.include_router(router)

    session_id = "SCREEN_24E4C01EA193"
    candidate_id = "CAN_TEST00000001"
    job_id = "JOB_TEST00000001"

    session = {
        "session_id": session_id,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "role_id": "PYTHON_DEV_FRESHER",
        "language": "en",
        "status": "CREATED",
        "questions": [
            {
                "question_id": "PYF_INTRO_001",
                "answer_type": "TEXT",
                "mandatory": True,
            },
            {
                "question_id": "PYF_SKILL_001",
                "answer_type": "SINGLE_CHOICE",
                "mandatory": False,
                "options": [
                    {"option_id": "OPT_PYTHON"},
                    {"option_id": "OPT_JAVA"},
                ],
            },
        ],
    }

    (session_dir / f"{session_id}.json").write_text(
        json.dumps(session),
        encoding="utf-8",
    )

    return {
        "client": TestClient(app),
        "session_id": session_id,
        "candidate_id": candidate_id,
        "session_dir": session_dir,
        "response_dir": response_dir,
    }


def test_save_draft_and_retrieve_safe_status(client):
    test = client
    http = test["client"]

    response = http.post(
        f"/hr-screening/sessions/{test['session_id']}/responses",
        params={"candidate_id": test["candidate_id"]},
        json={
            "answers": [
                {
                    "question_id": "PYF_INTRO_001",
                    "answer": "I have experience with Java and Python.",
                }
            ],
            "final_submission": False,
        },
    )

    assert response.status_code == 200

    result = response.json()
    assert result["status"] == "IN_PROGRESS"
    assert result["answered_questions"] == 1
    assert result["answered_mandatory_questions"] == 1

    status_response = http.get(
        f"/hr-screening/sessions/{test['session_id']}/responses",
        params={"candidate_id": test["candidate_id"]},
    )

    assert status_response.status_code == 200

    status_result = status_response.json()
    assert status_result["answered_questions"] == 1

    # The status endpoint must not disclose answer content.
    serialized = json.dumps(status_result)
    assert "I have experience with Java and Python." not in serialized


def test_final_submission_succeeds_when_mandatory_answer_exists(client):
    test = client
    http = test["client"]

    response = http.post(
        f"/hr-screening/sessions/{test['session_id']}/responses",
        params={"candidate_id": test["candidate_id"]},
        json={
            "answers": [
                {
                    "question_id": "PYF_INTRO_001",
                    "answer": "I have experience with Python.",
                }
            ],
            "final_submission": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUBMITTED"

    saved_session = json.loads(
        (
            test["session_dir"]
            / f"{test['session_id']}.json"
        ).read_text(encoding="utf-8")
    )

    assert saved_session["status"] == "SUBMITTED"
    assert saved_session.get("submitted_at") is not None


def test_final_submission_fails_when_mandatory_answer_is_missing(client):
    test = client
    http = test["client"]

    response = http.post(
        f"/hr-screening/sessions/{test['session_id']}/responses",
        params={"candidate_id": test["candidate_id"]},
        json={
            "answers": [
                {
                    "question_id": "PYF_SKILL_001",
                    "selected_options": ["OPT_PYTHON"],
                }
            ],
            "final_submission": True,
        },
    )

    assert response.status_code == 422

    saved_session = json.loads(
        (
            test["session_dir"]
            / f"{test['session_id']}.json"
        ).read_text(encoding="utf-8")
    )

    assert saved_session["status"] == "CREATED"


def test_wrong_candidate_cannot_submit_responses(client):
    test = client

    response = test["client"].post(
        f"/hr-screening/sessions/{test['session_id']}/responses",
        params={"candidate_id": "CAN_WRONG0000001"},
        json={
            "answers": [
                {
                    "question_id": "PYF_INTRO_001",
                    "answer": "Test answer",
                }
            ],
            "final_submission": False,
        },
    )

    assert response.status_code == 403


def test_unassigned_question_is_rejected(client):
    test = client

    response = test["client"].post(
        f"/hr-screening/sessions/{test['session_id']}/responses",
        params={"candidate_id": test["candidate_id"]},
        json={
            "answers": [
                {
                    "question_id": "UNKNOWN_QUESTION",
                    "answer": "Test answer",
                }
            ],
            "final_submission": False,
        },
    )

    assert response.status_code == 422


def test_invalid_choice_option_is_rejected(client):
    test = client

    response = test["client"].post(
        f"/hr-screening/sessions/{test['session_id']}/responses",
        params={"candidate_id": test["candidate_id"]},
        json={
            "answers": [
                {
                    "question_id": "PYF_SKILL_001",
                    "selected_options": ["INVALID_OPTION"],
                }
            ],
            "final_submission": False,
        },
    )

    assert response.status_code == 422


def test_response_status_does_not_expose_answers(client):
    test = client
    http = test["client"]

    http.post(
        f"/hr-screening/sessions/{test['session_id']}/responses",
        params={"candidate_id": test["candidate_id"]},
        json={
            "answers": [
                {
                    "question_id": "PYF_INTRO_001",
                    "answer": "Private candidate response",
                }
            ],
            "final_submission": False,
        },
    )

    response = http.get(
        f"/hr-screening/sessions/{test['session_id']}/responses",
        params={"candidate_id": test["candidate_id"]},
    )

    assert response.status_code == 200
    assert "Private candidate response" not in response.text
