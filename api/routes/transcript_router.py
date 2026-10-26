
"""
transcript_router.py

Responsibilities
----------------
1. Create and persist transcript records.
2. Retrieve a transcript by session and transcript ID.
3. List transcripts for a screening session.
4. Map service exceptions to safe HTTP responses.
5. Keep business logic inside transcript_service.py.

This router does not transcribe audio or evaluate candidate answers.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from api.schemas.transcript_schema import (
    TranscriptCreate,
    TranscriptRecord,
)
from api.service.transcript_service import (
    TranscriptAlreadyExistsError,
    TranscriptInputError,
    TranscriptNotFoundError,
    TranscriptPersistenceError,
    TranscriptSessionNotFoundError,
    create_transcript,
    get_transcript,
    list_transcripts,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transcripts",
    tags=["Transcript Management"],
)


# ============================================================
# EXCEPTION MAPPING
# ============================================================

def _raise_http_exception(exc: Exception) -> None:
    """Convert transcript service exceptions into safe HTTP responses."""

    if isinstance(exc, TranscriptSessionNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screening session was not found.",
        ) from exc

    if isinstance(exc, TranscriptInputError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if isinstance(exc, TranscriptNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if isinstance(exc, TranscriptAlreadyExistsError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if isinstance(exc, TranscriptPersistenceError):
        logger.exception("Transcript persistence operation failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete the transcript storage operation.",
        ) from exc

    logger.error(
        "Unexpected transcript service error: %s",
        type(exc).__name__,
    )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected transcript service error occurred.",
    ) from exc


# ============================================================
# CREATE TRANSCRIPT
# ============================================================

@router.post(
    "",
    response_model=TranscriptRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Create a transcript",
)
def create_transcript_endpoint(
    payload: TranscriptCreate,
) -> TranscriptRecord:
    """
    Validate, verify session ownership, normalize, and persist a transcript.

    The service generates the transcript ID automatically.
    """

    try:
        return create_transcript(payload)

    except (
        TranscriptSessionNotFoundError,
        TranscriptInputError,
        TranscriptAlreadyExistsError,
        TranscriptPersistenceError,
    ) as exc:
        _raise_http_exception(exc)


# ============================================================
# LIST SESSION TRANSCRIPTS
# ============================================================

@router.get(
    "/{session_id}",
    response_model=list[TranscriptRecord],
    status_code=status.HTTP_200_OK,
    summary="List session transcripts",
)
def list_transcripts_endpoint(
    session_id: str,
) -> list[TranscriptRecord]:
    """Return transcript records stored for the specified session."""

    try:
        return list_transcripts(session_id)

    except (
        TranscriptInputError,
        TranscriptPersistenceError,
    ) as exc:
        _raise_http_exception(exc)


# ============================================================
# GET ONE TRANSCRIPT
# ============================================================

@router.get(
    "/{session_id}/{transcript_id}",
    response_model=TranscriptRecord,
    status_code=status.HTTP_200_OK,
    summary="Get a transcript",
)
def get_transcript_endpoint(
    session_id: str,
    transcript_id: str,
) -> TranscriptRecord:
    """Retrieve one transcript within its specified screening session."""

    try:
        return get_transcript(
            session_id=session_id,
            transcript_id=transcript_id,
        )

    except (
        TranscriptInputError,
        TranscriptNotFoundError,
        TranscriptPersistenceError,
    ) as exc:
        _raise_http_exception(exc)
