
import json

import api.service.screening_response_service as service
from api.schemas.hr_screening_schema import (
    ScreeningResponseSubmissionRequest,
)


def test_submit_screening_draft(tmp_path, monkeypatch):
    sessions_dir = tmp_path / "sessions"
    responses_dir = tmp_path / "responses"

    sessions_dir.mkdir()
    responses_dir.mkdir()

    # Match the actual constant names in the service.
    monkeypatch.setattr(service, "SESSION_DIR", sessions_dir)
    monkeypatch.setattr(service, "RESPONSE_DIR", responses_dir)

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
            }
        ],
    }

    (sessions_dir / "SCREEN_001.json").write_text(
        json.dumps(session),
        encoding="utf-8",
    )

    request = ScreeningResponseSubmissionRequest(
        answers=[
            {
                "question_id": "PYTHON_Q001",
                "answer": (
                    "Python supports object-oriented programming."
                ),
            }
        ],
        final_submission=False,
    )

    result = service.submit_screening_responses(
        session_id="SCREEN_001",
        candidate_id="CAN_123456789ABC",
        request=request,
    )

    assert result["success"] is True
    assert result["session_id"] == "SCREEN_001"
    assert result["status"] == "IN_PROGRESS"
    assert result["submitted_answers"] == 1
    assert result["answered_questions"] == 1
    assert result["answered_mandatory_questions"] == 1

    # Verify that the response was persisted.
    response_data = json.loads(
        (responses_dir / "SCREEN_001.json").read_text(
            encoding="utf-8"
        )
    )

    assert "PYTHON_Q001" in response_data["answers"]
