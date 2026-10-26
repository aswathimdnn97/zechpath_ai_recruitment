"""HTTP endpoints for linking and reviewing screening transcripts."""

import logging

from fastapi import APIRouter, HTTPException, status

from api.schemas.transcript_integration_schema import (
    TranscriptResponseLinkRequest,
    TranscriptReviewUpdate,
)
from api.schemas.transcript_schema import TranscriptRecord
from api.service.transcript_response_integration_service import (
    TranscriptIntegrationDataError,
    TranscriptLinkConflictError,
    TranscriptReviewRequiredError,
    link_transcript_to_screening_response,
    update_transcript_review,
)
from api.service import screening_response_service as response_service
from api.service import transcript_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Transcript / Screening Response Integration"])


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, response_service.ScreeningSessionNotFoundError):
        raise HTTPException(status_code=404, detail="Screening session was not found.") from exc
    if isinstance(exc, response_service.ScreeningOwnershipError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, response_service.ScreeningSessionStateError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, response_service.ScreeningQuestionError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, transcript_service.TranscriptNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, transcript_service.TranscriptInputError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, TranscriptLinkConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, TranscriptIntegrationDataError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, TranscriptReviewRequiredError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, response_service.ScreeningStorageError):
        logger.exception("Screening response storage failed during transcript integration.")
        raise HTTPException(status_code=500, detail="Unable to update screening response.") from exc
    if isinstance(exc, transcript_service.TranscriptPersistenceError):
        logger.exception("Transcript storage failed during transcript integration.")
        raise HTTPException(status_code=500, detail="Unable to update transcript data.") from exc
    logger.exception("Unexpected transcript integration failure.")
    raise HTTPException(status_code=500, detail="Unexpected transcript integration error.") from exc


@router.post(
    "/transcripts/{session_id}/{transcript_id}/link",
    status_code=status.HTTP_200_OK,
    summary="Link a transcript to a screening response",
)
def link_transcript_endpoint(
    session_id: str,
    transcript_id: str,
    payload: TranscriptResponseLinkRequest,
) -> dict:
    """Attach a processed transcript to the assigned TEXT answer."""
    try:
        return link_transcript_to_screening_response(
            session_id=session_id,
            transcript_id=transcript_id,
            request=payload,
        )
    except Exception as exc:
        _raise_http(exc)


@router.patch(
    "/transcripts/{session_id}/{transcript_id}/review",
    response_model=TranscriptRecord,
    status_code=status.HTTP_200_OK,
    summary="Approve or correct a transcript",
)
def review_transcript_endpoint(
    session_id: str,
    transcript_id: str,
    payload: TranscriptReviewUpdate,
) -> TranscriptRecord:
    """Record a recruiter approval or corrected transcript text.

    Add the project's authenticated recruiter dependency before production use;
    reviewer_id in a request body is an audit field, not authentication.
    """
    try:
        return update_transcript_review(
            session_id=session_id,
            transcript_id=transcript_id,
            request=payload,
        )
    except Exception as exc:
        _raise_http(exc)
