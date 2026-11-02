
from unittest.mock import Mock

import pytest

from api.service import transcript_skill_workflow_service as workflow
from api.service.transcript_service import TranscriptServiceError
from api.service.transcript_service import TranscriptNotFoundError


def test_processes_saved_transcript(monkeypatch):
    transcript = {
        "session_id": "SCREEN_3F897D8A2CDE",
        "transcript_id": "TRN_428A03F8246C",
        "candidate_id": "CAN_123456789ABC",
        "job_id": "JOB_BF2FEFE4A4A3",
        "question_id": "PYF_EDU_001",
        "source": "VOICE",
        "language": "en",
        "original_text": "I have learned Python.",
        "normalized_text": "I have learned Python.",
        "status": "PROCESSED",
    }

    record = Mock()
    record.model_dump.return_value = transcript

    monkeypatch.setattr(
        workflow,
        "get_transcript",
        lambda session_id, transcript_id: record,
    )

    expected_result = {
        "transcript_id": transcript["transcript_id"],
        "session_id": transcript["session_id"],
        "recognized_skills": [{"skill": "Python"}],
        "skill_count": 1,
        "status": "COMPLETED",
    }

    monkeypatch.setattr(
        workflow,
        "process_and_save_transcript_skills",
        lambda transcript: expected_result,
    )

    result = workflow.process_saved_transcript_skills(
        session_id=transcript["session_id"],
        transcript_id=transcript["transcript_id"],
    )

    assert result == expected_result



def test_missing_transcript_raises_workflow_error(monkeypatch):
    def fail_lookup(session_id, transcript_id):
        raise TranscriptNotFoundError("Transcript not found")

    monkeypatch.setattr(
        workflow,
        "get_transcript",
        fail_lookup,
    )

    with pytest.raises(workflow.TranscriptSkillWorkflowError):
        workflow.process_saved_transcript_skills(
            "SCREEN_3F897D8A2CDE",
            "TRN_428A03F8246C",
        )
