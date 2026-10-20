"""
hr_screening_session_router.py

Responsibilities
----------------
1. Expose the endpoint to create an HR screening session.
2. Validate incoming requests through Pydantic.
3. Delegate session creation to screening_session_service.
4. Translate known service errors into safe HTTP responses.
5. Avoid exposing unexpected internal errors to clients.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from api.schemas.hr_screening_schema import (
    ScreeningSessionCreateRequest,
)
from api.service.screening_session_service import (
    ScreeningQuestionsUnavailableError,
    ScreeningSessionStorageError,
    ScreeningSessionValidationError,
    create_screening_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hr-screening",
    tags=["HR Screening Sessions"],
)


@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    summary="Create an HR screening session",
    description=(
        "Creates a candidate screening session, assigns candidate-safe "
        "questions, persists the session, and returns the session details."
    ),
    responses={
        201: {
            "description": "Screening session created successfully.",
        },
        422: {
            "description": "Invalid request or screening questions unavailable.",
        },
        500: {
            "description": "Unable to create the screening session.",
        },
    },
)
def create_hr_screening_session(
    request: ScreeningSessionCreateRequest,
) -> dict[str, Any]:
    """Create and return a screening session."""

    try:
        session = create_screening_session(
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            role_id=request.role_id,
            language=request.language,
            categories=request.categories,
            include_optional=request.include_optional,
        )

        logger.info(
            "HR screening session created | session_id=%s | "
            "candidate_id=%s | job_id=%s | role_id=%s",
            session.get("session_id"),
            request.candidate_id,
            request.job_id,
            request.role_id,
        )

        return session

    except ScreeningSessionValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    except ScreeningQuestionsUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    except ScreeningSessionStorageError as exc:
        logger.exception(
            "Unable to persist HR screening session."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the screening session at this time.",
        ) from exc

    except Exception:
        logger.exception(
            "Unexpected error creating HR screening session."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "An unexpected error occurred while creating "
                "the screening session."
            ),
        ) from None
