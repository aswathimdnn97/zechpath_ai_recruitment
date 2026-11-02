"""Tests for recruiter transcript approval/correction and audit preservation.

Run from the ZechPath repository root:
    python -m pytest tests/transcript/test_transcript_recruiter_review.py -v
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from api.schemas.transcript_integration_schema import TranscriptReviewUpdate
from api.schemas.transcript_schema import (
    TranscriptCreate,
    TranscriptRecord,
    TranscriptReviewStatus,
    TranscriptStatus,
)
from api.service import transcript_service
from api.service import transcript_response_integration_service as review_service


SESSION_ID = "SCREEN_123456789ABC"
TRANSCRIPT_ID = "TRN_123456789ABC"


@pytest.fixture
def stored_transcript(tmp_path, monkeypatch):
    """Create a real transcript JSON record in isolated test storage."""
    monkeypatch.setattr(transcript_service, "TRANSCRIPT_ROOT", tmp_path)
    record = TranscriptRecord.model_validate({
        "session_id": SESSION_ID,
        "candidate_id": "CAN_123456789ABC",
        "job_id": "JOB_123456789ABC",
        "question_id": "PYF_INTRO_001",
        "source": "VOICE",
        "language": "en",
        "original_text": "  My   name is Anu.  ",
        "normalized_text": "My name is Anu.",
        "transcription": {"provider": "test-provider", "model_version": "test-v1"},
        "timing": {"transcribed_at": datetime.now(timezone.utc), "duration_ms": 1200},
        "transcript_id": TRANSCRIPT_ID,
        "status": TranscriptStatus.PROCESSED,
    })
    target = tmp_path / SESSION_ID / f"{TRANSCRIPT_ID}.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(record.model_dump(mode="json")), encoding="utf-8")
    return target, record


def test_approve_transcript_records_reviewer_and_preserves_original(stored_transcript):
    target, before = stored_transcript

    updated = review_service.update_transcript_review(
        session_id=SESSION_ID,
        transcript_id=TRANSCRIPT_ID,
        request=TranscriptReviewUpdate(status="APPROVED", reviewer_id="REC_0001"),
    )

    saved = TranscriptRecord.model_validate_json(target.read_text(encoding="utf-8"))
    assert updated.review.status == TranscriptReviewStatus.APPROVED
    assert updated.review.reviewer_id == "REC_0001"
    assert updated.review.reviewed_at is not None
    assert updated.review.reviewed_at.tzinfo is not None
    assert updated.original_text == before.original_text
    assert saved.original_text == before.original_text
    assert saved.normalized_text == before.normalized_text
    assert len(saved.review_history) == 1
    assert saved.review_history[0].reviewer_id == "REC_0001"


def test_correct_transcript_preserves_original_and_saves_correction(stored_transcript):
    target, before = stored_transcript
    corrected = "My name is Anu, and I am learning Python."

    updated = review_service.update_transcript_review(
        session_id=SESSION_ID,
        transcript_id=TRANSCRIPT_ID,
        request=TranscriptReviewUpdate(
            status="CORRECTED",
            reviewer_id="REC_0002",
            corrected_text=corrected,
        ),
    )

    saved = TranscriptRecord.model_validate_json(target.read_text(encoding="utf-8"))
    assert updated.review.status == TranscriptReviewStatus.CORRECTED
    assert updated.review.corrected_text == corrected
    assert updated.review.reviewer_id == "REC_0002"
    assert updated.review.reviewed_at is not None
    assert updated.original_text == before.original_text
    assert saved.original_text == before.original_text
    assert saved.normalized_text == before.normalized_text
    assert saved.review_history[-1].corrected_text == corrected


def test_re_review_appends_history_instead_of_erasing_previous_review(stored_transcript):
    target, before = stored_transcript
    review_service.update_transcript_review(
        session_id=SESSION_ID,
        transcript_id=TRANSCRIPT_ID,
        request=TranscriptReviewUpdate(status="APPROVED", reviewer_id="REC_0001"),
    )
    updated = review_service.update_transcript_review(
        session_id=SESSION_ID,
        transcript_id=TRANSCRIPT_ID,
        request=TranscriptReviewUpdate(
            status="CORRECTED",
            reviewer_id="REC_0002",
            corrected_text="Corrected text.",
        ),
    )

    saved = TranscriptRecord.model_validate_json(target.read_text(encoding="utf-8"))
    assert updated.review.status == TranscriptReviewStatus.CORRECTED
    assert len(saved.review_history) == 2
    assert [event.status for event in saved.review_history] == [
        TranscriptReviewStatus.APPROVED,
        TranscriptReviewStatus.CORRECTED,
    ]
    assert [event.reviewer_id for event in saved.review_history] == ["REC_0001", "REC_0002"]
    assert saved.original_text == before.original_text


def test_corrected_review_requires_nonblank_text():
    with pytest.raises(ValidationError):
        TranscriptReviewUpdate(
            status="CORRECTED", reviewer_id="REC_0001", corrected_text="   "
        )


def test_approved_review_rejects_correction_text():
    with pytest.raises(ValidationError):
        TranscriptReviewUpdate(
            status="APPROVED", reviewer_id="REC_0001", corrected_text="Unexpected"
        )


def test_review_model_requires_reviewer_and_timestamp_for_approved_status():
    with pytest.raises(ValidationError):
        from api.schemas.transcript_schema import TranscriptReview
        TranscriptReview(status="APPROVED")


def test_legacy_record_without_review_history_remains_valid():
    data = {
        "session_id": SESSION_ID,
        "candidate_id": "CAN_123456789ABC",
        "job_id": "JOB_123456789ABC",
        "question_id": "PYF_INTRO_001",
        "language": "en",
        "original_text": "Original words.",
        "transcription": {"provider": "test-provider"},
        "transcript_id": TRANSCRIPT_ID,
        "status": "PROCESSED",
    }
    record = TranscriptRecord.model_validate(data)
    assert record.review_history == []
