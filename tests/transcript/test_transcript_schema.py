
"""
test_transcript_schema.py

Tests for:
- Transcript schema validation
- English, Malayalam, and Hindi support
- Confidence validation
- Timestamp validation
- Segment ordering and duration
- Empty transcript rejection
- Recruiter review validation
- Unknown field rejection
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from api.schemas.transcript_schema import (
    TranscriptCreate,
    TranscriptRecord,
    TranscriptReview,
    TranscriptReviewStatus,
    TranscriptSegment,
    TranscriptStatus,
)


@pytest.fixture
def valid_payload():
    return {
        "session_id": "SCREEN_0B4F4DA9183D",
        "candidate_id": "CAN_C0CC88823474",
        "job_id": "JOB_BF2FEFE4A4A3",
        "question_id": "PYF_EXP_001",
        "source": "VOICE",
        "language": "en",
        "original_text": "I have worked on Python and Django projects",
        "normalized_text": (
            "I have worked on Python and Django projects."
        ),
        "segments": [
            {
                "start_ms": 0,
                "end_ms": 2000,
                "text": "I have worked on Python",
                "confidence": 0.96,
            },
            {
                "start_ms": 2000,
                "end_ms": 4000,
                "text": "and Django projects",
                "confidence": 0.94,
            },
        ],
        "transcription": {
            "provider": "test-provider",
            "model_version": "test-v1",
            "confidence": 0.95,
        },
        "timing": {
            "recorded_at": "2026-10-20T10:30:00Z",
            "transcribed_at": "2026-10-20T10:30:04Z",
            "duration_ms": 4000,
        },
        "normalization": {
            "version": "1.0",
            "language_preserved": True,
            "pii_redacted": False,
        },
    }


@pytest.mark.parametrize(
    ("language", "answer"),
    [
        ("en", "I am a Python developer."),
        ("ml", "ഞാൻ ഒരു Python ഡെവലപ്പറാണ്."),
        ("hi", "मैं एक Python डेवलपर हूँ।"),
    ],
)
def test_supported_languages(valid_payload, language, answer):
    valid_payload["language"] = language
    valid_payload["original_text"] = answer
    valid_payload["normalized_text"] = answer
    valid_payload["segments"] = []

    transcript = TranscriptCreate(**valid_payload)

    assert transcript.language == language
    assert transcript.original_text == answer


def test_valid_transcript_create(valid_payload):
    transcript = TranscriptCreate(**valid_payload)

    assert transcript.candidate_id == "CAN_C0CC88823474"
    assert transcript.job_id == "JOB_BF2FEFE4A4A3"
    assert transcript.question_id == "PYF_EXP_001"
    assert transcript.transcription.confidence == 0.95
    assert len(transcript.segments) == 2


@pytest.mark.parametrize(
    "field",
    ["session_id", "candidate_id", "job_id", "question_id"],
)
def test_required_identifiers(valid_payload, field):
    valid_payload.pop(field)

    with pytest.raises(ValidationError):
        TranscriptCreate(**valid_payload)


@pytest.mark.parametrize("confidence", [-0.01, 1.01, 2.0])
def test_invalid_transcription_confidence(
    valid_payload, confidence
):
    valid_payload["transcription"]["confidence"] = confidence

    with pytest.raises(ValidationError):
        TranscriptCreate(**valid_payload)


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_invalid_segment_confidence(confidence):
    with pytest.raises(ValidationError):
        TranscriptSegment(
            start_ms=0,
            end_ms=1000,
            text="Python",
            confidence=confidence,
        )


def test_missing_confidence_is_allowed(valid_payload):
    valid_payload["transcription"]["confidence"] = None
    valid_payload["segments"] = []

    transcript = TranscriptCreate(**valid_payload)

    assert transcript.transcription.confidence is None


def test_segment_end_must_exceed_start():
    with pytest.raises(ValidationError):
        TranscriptSegment(
            start_ms=1000,
            end_ms=1000,
            text="Python",
        )


def test_negative_segment_start_is_rejected():
    with pytest.raises(ValidationError):
        TranscriptSegment(
            start_ms=-1,
            end_ms=1000,
            text="Python",
        )


def test_overlapping_segments_are_rejected(valid_payload):
    valid_payload["segments"] = [
        {
            "start_ms": 0,
            "end_ms": 2500,
            "text": "First segment",
        },
        {
            "start_ms": 2000,
            "end_ms": 3000,
            "text": "Overlapping segment",
        },
    ]

    with pytest.raises(ValidationError):
        TranscriptCreate(**valid_payload)


def test_segment_exceeding_duration_is_rejected(valid_payload):
    valid_payload["timing"]["duration_ms"] = 1000

    with pytest.raises(ValidationError):
        TranscriptCreate(**valid_payload)


def test_timezone_naive_timestamp_is_rejected(valid_payload):
    valid_payload["timing"]["recorded_at"] = (
        datetime(2026, 10, 20, 10, 30, 0)
    )

    with pytest.raises(ValidationError):
        TranscriptCreate(**valid_payload)


@pytest.mark.parametrize(
    "field",
    ["original_text", "normalized_text"],
)
def test_blank_text_is_rejected(valid_payload, field):
    valid_payload[field] = "   "

    with pytest.raises(ValidationError):
        TranscriptCreate(**valid_payload)


def test_normalized_text_can_be_none(valid_payload):
    valid_payload["normalized_text"] = None

    transcript = TranscriptCreate(**valid_payload)

    assert transcript.normalized_text is None


def test_unsupported_language_is_rejected(valid_payload):
    valid_payload["language"] = "fr"

    with pytest.raises(ValidationError):
        TranscriptCreate(**valid_payload)


def test_unknown_field_is_rejected(valid_payload):
    valid_payload["unexpected_field"] = "unexpected"

    with pytest.raises(ValidationError):
        TranscriptCreate(**valid_payload)


def test_corrected_review_requires_reviewer_and_timestamp():
    with pytest.raises(ValidationError):
        TranscriptReview(
            status=TranscriptReviewStatus.CORRECTED,
            corrected_text="Corrected answer",
        )


def test_valid_corrected_review():
    review = TranscriptReview(
        status=TranscriptReviewStatus.CORRECTED,
        corrected_text="Corrected answer",
        reviewer_id="HR_001",
        reviewed_at=datetime.now(timezone.utc),
    )

    assert review.status == TranscriptReviewStatus.CORRECTED
    assert review.reviewer_id == "HR_001"


def test_transcript_record_defaults(valid_payload):
    record = TranscriptRecord(
        **valid_payload,
        transcript_id="TRN_8F3A21C9D102",
    )

    assert record.status == TranscriptStatus.PENDING
    assert record.review.status == TranscriptReviewStatus.PENDING
    assert record.transcript_id == "TRN_8F3A21C9D102"
    assert record.created_at.tzinfo is not None
    assert record.updated_at.tzinfo is not None
