import pytest

from api.service import hr_screening_evaluation_service as evaluation_service
from api.service.transcript_response_integration_service import (
    TranscriptReviewRequiredError,
)


def test_pending_transcript_blocks_evaluation(monkeypatch):
    session_id = "SCREEN_24E4C01EA193"

    responses = {
        "session_id": session_id,
        "candidate_id": "CAN_TEST",
        "answers": {
            "PYF_INTRO_001": {
                "question_id": "PYF_INTRO_001",
                "answer": "Original speech transcript",
                "answered": True,
                "transcript": {
                    "transcript_id": "TRN_TEST",
                    "review_status": "PENDING",
                },
            }
        },
    }

    def fake_sync(*, session_id, responses):
        raise TranscriptReviewRequiredError(
            "Recruiter review is required."
        )

    monkeypatch.setattr(
        "api.service.transcript_response_integration_service."
        "synchronize_linked_transcripts_for_evaluation",
        fake_sync,
    )

    with pytest.raises(
        evaluation_service.TranscriptReviewPrerequisiteError
    ):
        evaluation_service._synchronize_transcripts_before_evaluation(
            session_id,
            responses,
        )