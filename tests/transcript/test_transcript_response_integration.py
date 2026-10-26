"""Focused contract tests for transcript-to-response integration helpers.

These tests assume the ZechPath project and transcript schema/service are on
PYTHONPATH. Run them from the repository root after copying the patch files.
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from api.service import transcript_response_integration_service as integration


def test_pending_transcript_blocks_evaluation(monkeypatch):
    transcript = SimpleNamespace(
        session_id="SCREEN_123456789ABC",
        transcript_id="TRN_123456789ABC",
        question_id="PYF_INTRO_001",
        candidate_id="CAN_123456789ABC",
        status="PROCESSED",
        review=SimpleNamespace(status="PENDING", corrected_text=None, reviewer_id=None, reviewed_at=None),
        normalized_text="My name is Anu.",
        original_text="My name is Anu.",
    )
    monkeypatch.setattr(integration, "get_transcript", lambda **kwargs: transcript)
    responses = {
        "session_id": "SCREEN_123456789ABC",
        "candidate_id": "CAN_123456789ABC",
        "answers": {
            "PYF_INTRO_001": {
                "question_id": "PYF_INTRO_001",
                "answer": "My name is Anu.",
                "answered": True,
                "transcript": {"transcript_id": "TRN_123456789ABC", "review_status": "PENDING"},
            }
        },
    }
    with pytest.raises(integration.TranscriptReviewRequiredError):
        integration.synchronize_linked_transcripts_for_evaluation(
            session_id="SCREEN_123456789ABC", responses=responses
        )


def test_approved_transcript_refreshes_answer(monkeypatch):
    transcript = SimpleNamespace(
        session_id="SCREEN_123456789ABC",
        transcript_id="TRN_123456789ABC",
        question_id="PYF_INTRO_001",
        candidate_id="CAN_123456789ABC",
        status="PROCESSED",
        review=SimpleNamespace(
            status="APPROVED", corrected_text=None, reviewer_id="REC_1",
            reviewed_at=datetime(2026, 10, 21, tzinfo=timezone.utc),
        ),
        normalized_text="Approved normalized answer.",
        original_text="un-normalized answer",
    )
    monkeypatch.setattr(integration, "get_transcript", lambda **kwargs: transcript)
    monkeypatch.setattr(integration.response_store, "_write_json_atomic", lambda *args: None)
    monkeypatch.setattr(integration.response_store, "_response_path", lambda session_id: session_id)
    responses = {
        "session_id": "SCREEN_123456789ABC",
        "candidate_id": "CAN_123456789ABC",
        "answers": {
            "PYF_INTRO_001": {
                "question_id": "PYF_INTRO_001",
                "answer": "un-normalized answer",
                "answered": True,
                "transcript": {"transcript_id": "TRN_123456789ABC", "review_status": "PENDING"},
            }
        },
    }
    result = integration.synchronize_linked_transcripts_for_evaluation(
        session_id="SCREEN_123456789ABC", responses=responses
    )
    answer = result["answers"]["PYF_INTRO_001"]
    assert answer["answer"] == "Approved normalized answer."
    assert answer["transcript"]["review_status"] == "APPROVED"
    assert answer["transcript"]["reviewer_id"] == "REC_1"

