"""
hr_screening_response_router.py

Responsibilities
----------------
1. Expose endpoints for candidate screening response submission.
2. Support draft saving and final submission.
3. Retrieve screening response status.
4. Convert service exceptions into appropriate HTTP responses.

Business logic and storage remain in screening_response_service.py.
"""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from api.schemas.hr_screening_schema import (
    ScreeningResponseSubmissionRequest,
)
from api.service.screening_response_service import (
    ScreeningResponseError,
    ScreeningSessionNotFoundError,
    ScreeningOwnershipError,
    ScreeningSessionStateError,
    ScreeningQuestionError,
    ScreeningAnswerError,
    ScreeningMandatoryQuestionsError,
    ScreeningStorageError,
    submit_screening_responses,
    get_screening_responses,
)
from typing import NoReturn

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hr-screening",
    tags=["HR Screening Responses"],
)


def _raise_http_exception(
    exc: ScreeningResponseError,
) -> NoReturn:
    
    """Translate screening service exceptions into HTTP errors."""

    if isinstance(exc, ScreeningSessionNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND

    elif isinstance(exc, ScreeningOwnershipError):
        status_code = status.HTTP_403_FORBIDDEN

    elif isinstance(exc, ScreeningSessionStateError):
        status_code = status.HTTP_409_CONFLICT

    elif isinstance(
        exc,
        (
            ScreeningQuestionError,
            ScreeningAnswerError,
            ScreeningMandatoryQuestionsError,
        ),
    ):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

    elif isinstance(exc, ScreeningStorageError):
        logger.exception("HR screening storage operation failed")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    else:
        logger.warning("HR screening request failed: %s", exc)
        status_code = status.HTTP_400_BAD_REQUEST

    # Avoid exposing internal storage or implementation details.
    if status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        detail = "Unable to process screening responses at this time."
    else:
        detail = str(exc)

    raise HTTPException(
        status_code=status_code,
        detail=detail,
    ) from exc


@router.post(
    "/sessions/{session_id}/responses",
    status_code=status.HTTP_200_OK,
    summary="Submit HR screening responses",
    description=(
        "Save candidate responses as a draft or submit them finally. "
        "Final submission requires all mandatory questions to be answered."
    ),
)
def submit_screening_response(
    session_id: str,
    request: ScreeningResponseSubmissionRequest,
    candidate_id: str = Query(
        ...,
        min_length=1,
        description="Candidate identifier associated with the screening session.",
    ),
):
    """
    Submit or save candidate answers.

    The service validates session ownership, session state, question IDs,
    answer types, allowed options, and mandatory-question completion.
    """

    try:
        return submit_screening_responses(
            session_id=session_id,
            candidate_id=candidate_id,
            request=request,
        )

    except ScreeningResponseError as exc:
        _raise_http_exception(exc)

    except Exception:
        logger.exception(
            "Unexpected error submitting screening responses; session_id=%s",
            session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while submitting screening responses.",
        ) from None


@router.get(
    "/sessions/{session_id}/responses",
    status_code=status.HTTP_200_OK,
    summary="Get HR screening response status",
    description=(
        "Retrieve the answered-question status for a candidate's screening "
        "session without returning the actual answer content."
    ),
)
def retrieve_screening_responses(
    session_id: str,
    candidate_id: str = Query(
        ...,
        min_length=1,
        description="Candidate identifier associated with the screening session.",
    ),
):
    """
    Retrieve response status after validating session ownership.

    The service controls which response fields are returned.
    """

    try:
        return get_screening_responses(
            session_id=session_id,
            candidate_id=candidate_id,
        )

    except ScreeningResponseError as exc:
        _raise_http_exception(exc)

    except Exception:
        logger.exception(
            "Unexpected error retrieving screening responses; session_id=%s",
            session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving screening responses.",
        ) from None
