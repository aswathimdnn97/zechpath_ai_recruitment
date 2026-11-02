
import json

import api.service.screening_response_service as service
from api.schemas.hr_screening_schema import (
    ScreeningResponseSubmissionRequest,
)


def test_submit_screening_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("ZECHPATH_STORAGE_BACKEND", "json")

    sessions_dir = tmp_path / "sessions"
    responses_dir = tmp_path / "responses"

    sessions_dir.mkdir()
    responses_dir.mkdir()

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

import json

import api.service.screening_response_service as service
import api.service.intent_classification_service as intent_service

from api.schemas.hr_screening_schema import (
    ScreeningResponseSubmissionRequest,
)


def test_text_answer_persists_semantic_classification(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("ZECHPATH_STORAGE_BACKEND", "json")

    sessions_dir = tmp_path / "sessions"
    responses_dir = tmp_path / "responses"

    sessions_dir.mkdir()
    responses_dir.mkdir()

    monkeypatch.setattr(service, "SESSION_DIR", sessions_dir)
    monkeypatch.setattr(service, "RESPONSE_DIR", responses_dir)

    classification = {
        "intent": "SKILLS",
        "language": "en",
        "extracted_data": {
            "skills": ["Python", "Django"],
            "skill_count": 2,
        },
        "answer_quality": {
            "status": "CLEAR",
        },
        "off_topic_detection": {
            "status": "ON_TOPIC",
        },
        "extraction_performed": True,
        "requires_review": False,
        "evidence": [],
    }

    def fake_classifier(**kwargs):
        assert kwargs["question_text"] == "What are your technical skills?"
        assert kwargs["answer_text"] == "I know Python and Django."
        assert kwargs["language"] == "en"
        return classification

    monkeypatch.setattr(
        intent_service,
        "classify_candidate_answer",
        fake_classifier,
    )

    session = {
        "session_id": "SCREEN_001",
        "candidate_id": "CAN_123456789ABC",
        "job_id": "JOB_BF2FEFE4A4A3",
        "role_id": "PYTHON_DEV_FRESHER",
        "language": "en",
        "status": "CREATED",
        "questions": [
            {
                "question_id": "PYTHON_Q001",
                "question_text": "What are your technical skills?",
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
                "answer": "I know Python and Django.",
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

    response_data = json.loads(
        (responses_dir / "SCREEN_001.json").read_text(
            encoding="utf-8"
        )
    )

    saved_answer = response_data["answers"]["PYTHON_Q001"]

    assert saved_answer["answer"] == "I know Python and Django."
    assert saved_answer["semantic_classification"] == classification
    assert saved_answer["semantic_classification"]["intent"] == "SKILLS"


def test_vague_answer_semantic_flags_are_persisted(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("ZECHPATH_STORAGE_BACKEND", "json")

    sessions_dir = tmp_path / "sessions"
    responses_dir = tmp_path / "responses"

    sessions_dir.mkdir()
    responses_dir.mkdir()

    monkeypatch.setattr(service, "SESSION_DIR", sessions_dir)
    monkeypatch.setattr(service, "RESPONSE_DIR", responses_dir)

    classification = {
        "intent": "SKILLS",
        "language": "en",
        "extracted_data": {},
        "answer_quality": {
            "status": "VAGUE",
        },
        "off_topic_detection": {
            "status": "UNCLEAR",
        },
        "extraction_performed": False,
        "requires_review": True,
        "evidence": [],
    }

    monkeypatch.setattr(
        intent_service,
        "classify_candidate_answer",
        lambda **kwargs: classification,
    )

    session = {
        "session_id": "SCREEN_002",
        "candidate_id": "CAN_123456789ABC",
        "job_id": "JOB_BF2FEFE4A4A3",
        "status": "CREATED",
        "language": "en",
        "questions": [
            {
                "question_id": "PYTHON_Q002",
                "question_text": "What are your technical skills?",
                "mandatory": True,
                "answer_type": "TEXT",
            }
        ],
    }

    (sessions_dir / "SCREEN_002.json").write_text(
        json.dumps(session),
        encoding="utf-8",
    )

    request = ScreeningResponseSubmissionRequest(
        answers=[
            {
                "question_id": "PYTHON_Q002",
                "answer": "I am not sure.",
            }
        ],
        final_submission=False,
    )

    service.submit_screening_responses(
        session_id="SCREEN_002",
        candidate_id="CAN_123456789ABC",
        request=request,
    )

    response_data = json.loads(
        (responses_dir / "SCREEN_002.json").read_text(
            encoding="utf-8",
        )
    )

    saved_classification = response_data["answers"][
        "PYTHON_Q002"
    ]["semantic_classification"]

    assert saved_classification["answer_quality"]["status"] == "VAGUE"
    assert saved_classification["requires_review"] is True
    assert saved_classification["extraction_performed"] is False


def test_structured_answer_is_not_semantically_classified():
    normalized_answer = {
        "question_id": "PYTHON_Q003",
        "answer": None,
        "selected_options": ["OPTION_A"],
        "answered": True,
    }

    question = {
        "question_id": "PYTHON_Q003",
        "question_text": "Select your experience level.",
        "answer_type": "MCQ",
    }

    session = {
        "language": "en",
    }

    result = service._attach_semantic_classification(
        normalized_answer=normalized_answer,
        question=question,
        session=session,
    )

    assert "semantic_classification" not in result