
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.transcript_router import router
from api.service.transcript_service import TRANSCRIPT_ROOT
import api.service.screening_session_service as session_service


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create an isolated app with temporary transcript and session storage."""

    monkeypatch.setenv("ZECHPATH_STORAGE_BACKEND", "json")

    transcript_root = tmp_path / "transcripts"
    sessions_dir = tmp_path / "sessions"

    transcript_root.mkdir()
    sessions_dir.mkdir()

    monkeypatch.setattr(
        "api.service.transcript_service.TRANSCRIPT_ROOT",
        transcript_root,
    )
    monkeypatch.setattr(
        session_service,
        "SESSION_DIR",
        sessions_dir,
    )

    app = FastAPI()
    app.include_router(router)

    return TestClient(app)

@pytest.fixture
def transcript_payload():
    return {
        "session_id": "SCREEN_0B4F4DA9183D",
        "candidate_id": "CAN_B3B39704E1FF",
        "job_id": "JOB_BF2FEFE4A4A3",
        "question_id": "PYF_INTRO_001",
        "source": "VOICE",
        "language": "ml",
        "original_text": "ഞാൻ ഒരു Python ഡെവലപ്പർ ആകാൻ ആഗ്രഹിക്കുന്നു.",
        "transcription": {
            "provider": "manual"
            # Use the exact fields and structure
            # required by your TranscriptCreate schema.
        },
    }
    

@pytest.fixture
def screening_session(tmp_path, monkeypatch, transcript_payload):
    import json

    import api.service.screening_session_service as session_service

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    # Ensure the session service uses the test directory.
    monkeypatch.setattr(
        session_service,
        "SESSION_DIR",
        sessions_dir,
    )

    session_id = transcript_payload["session_id"]

    session = {
        "session_id": session_id,
        "candidate_id": transcript_payload["candidate_id"],
        "job_id": transcript_payload["job_id"],
        "role_id": "PYTHON_DEV_FRESHER",
        "language": transcript_payload["language"],
        "status": "SUBMITTED",
        "questions": [
            {
                "question_id": transcript_payload["question_id"],
                "question_text": "നിങ്ങളെക്കുറിച്ച് പറയൂ.",
                "answer_type": "TEXT",
                "mandatory": True,
            }
        ],
    }

    (sessions_dir / f"{session_id}.json").write_text(
        json.dumps(session, ensure_ascii=False),
        encoding="utf-8",
    )

    return session

def test_create_transcript(client, transcript_payload,screening_session):
    response = client.post(
        "/transcripts",
        json=transcript_payload,
    )
    
    print("Status:", response.status_code)
    print("Response:", response.json())

    assert response.status_code == 201
    assert response.json()["original_text"] == (
        "ഞാൻ ഒരു Python ഡെവലപ്പർ ആകാൻ ആഗ്രഹിക്കുന്നു."
    )
    assert response.json()["normalized_text"] == (
        "ഞാൻ ഒരു Python ഡെവലപ്പർ ആകാൻ ആഗ്രഹിക്കുന്നു."
    )


def test_list_transcripts(client, transcript_payload,screening_session):
    client.post("/transcripts", json=transcript_payload)

    response = client.get(
        "/transcripts/SCREEN_0B4F4DA9183D"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_transcript(client, transcript_payload,screening_session):
    created = client.post(
        "/transcripts",
        json=transcript_payload,
    ).json()

    response = client.get(
        f"/transcripts/{created['session_id']}/"
        f"{created['transcript_id']}"
    )

    assert response.status_code == 200
    assert response.json()["transcript_id"] == (
        created["transcript_id"]
    )


def test_missing_transcript_returns_404(client):
    response = client.get(
        "/transcripts/SCREEN_0B4F4DA9183D/TRN_A1B2C3D4E5F6"
    )

    assert response.status_code == 404


def test_invalid_session_id_returns_422(client):
    response = client.get("/transcripts/../invalid")

    assert response.status_code in (404, 422)
