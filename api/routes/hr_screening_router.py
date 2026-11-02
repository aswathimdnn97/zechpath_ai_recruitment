
"""
hr_screening_router.py

Responsibilities
----------------
1. Expose HR screening roles and categories.
2. Retrieve candidate-safe questions by role, category, and language.
3. Support mandatory-only question retrieval.
4. Expose supported screening languages.
5. Evaluate submitted screening sessions.
6. Retrieve saved screening evaluation reports.
7. Convert service errors into safe HTTP responses.

Business logic remains in service modules.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from api.service.question_bank_service import (
    QuestionBankError,
    get_available_categories,
    get_available_languages,
    get_available_roles,
    get_candidate_question,
    get_candidate_questions,
)

from api.service.hr_screening_evaluation_service import (
    InvalidScreeningStateError,
    ScreeningDataError,
    ScreeningEvaluationError,
    ScreeningResponseNotFoundError,
    ScreeningSessionNotFoundError,
    RecruiterDecisionPrerequisiteError,
    evaluate_screening_session,
    get_screening_evaluation,
    review_screening_question,
    save_recruiter_decision,  

)

from api.schemas.hr_screening_schema import (
    RecruiterQuestionReviewRequest,
    RecruiterDecisionRequest,
)

from api.service.transcript_skill_workflow_service import (
    process_saved_transcript_skills,
    TranscriptSkillWorkflowError,
)
from api.service.hr_screening_evaluation_service import (
    TranscriptReviewPrerequisiteError,
    # Keep your existing imports
)
from api.service.transcript_service import TranscriptNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/hr-screening",
    tags=["HR Screening"],
)


# ============================================================
# QUESTION BANK ERROR HANDLING
# ============================================================

def _handle_question_bank_error(
    exc: QuestionBankError,
) -> HTTPException:
    """Log internal failures and return a safe API response."""

    logger.error(
        "HR screening question bank operation failed: %s",
        type(exc).__name__,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to load HR screening data.",
    )


# ============================================================
# EVALUATION ERROR HANDLING
# ============================================================

def _handle_evaluation_error(
    exc: ScreeningEvaluationError,
    *,
    operation: str,
) -> HTTPException:
    """Translate known evaluation service errors into HTTP errors."""

    if isinstance(exc, ScreeningSessionNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screening session not found.",
        )

    if isinstance(exc, ScreeningResponseNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submitted screening responses not found.",
        )

    if isinstance(exc, InvalidScreeningStateError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only submitted screening sessions can be evaluated.",
        )
    
    if isinstance(exc, TranscriptReviewPrerequisiteError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "All linked transcripts must be approved or corrected "
                "by a recruiter before evaluation."
            ),
        )

    if isinstance(exc, ScreeningDataError):
        logger.error(
            "Invalid stored screening data during %s: %s",
            operation,
            type(exc).__name__,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored screening data is invalid.",
        )

    # Backward compatibility for the current evaluation service.
    if (
        operation == "retrieve_report"
        and str(exc).startswith("No evaluation report exists")
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screening evaluation report not found.",
        )

    logger.error(
        "HR screening evaluation operation failed: %s (%s)",
        operation,
        type(exc).__name__,
        exc_info=(type(exc), exc, exc.__traceback__),
    )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to process the HR screening request.",
    )


# ============================================================
# GET AVAILABLE ROLES
# ============================================================

@router.get(
    "/roles",
    response_model=list[str],
    summary="Get available screening roles",
)
def list_screening_roles() -> list[str]:
    """Return role IDs supported by the question bank."""

    try:
        return get_available_roles()
    except QuestionBankError as exc:
        raise _handle_question_bank_error(exc) from exc


# ============================================================
# GET AVAILABLE CATEGORIES
# ============================================================

@router.get(
    "/categories",
    summary="Get screening categories",
)
def list_screening_categories() -> list[Any]:
    """Return categories configured in the question bank."""

    try:
        return get_available_categories()
    except QuestionBankError as exc:
        raise _handle_question_bank_error(exc) from exc


# ============================================================
# GET SUPPORTED LANGUAGES
# ============================================================

@router.get(
    "/languages",
    response_model=list[str],
    summary="Get supported screening languages",
)
def list_screening_languages() -> list[str]:
    """
    Return language codes configured in the multilingual question bank.

    Example response:
        ["en", "ml", "hi"]
    """

    try:
        return get_available_languages()
    except QuestionBankError as exc:
        raise _handle_question_bank_error(exc) from exc


# ============================================================
# GET QUESTIONS FOR A ROLE
# ============================================================

@router.get(
    "/questions",
    summary="Get screening questions",
)
def list_screening_questions(
    role_id: str = Query(
        ...,
        min_length=1,
        description="Role ID, e.g. PYTHON_DEV_FRESHER",
    ),
    language: str = Query(
        default="en",
        min_length=2,
        max_length=10,
        description="Requested language code, e.g. en, ml, hi",
    ),
    category: str | None = Query(
        default=None,
        min_length=1,
        description="Optional category, e.g. SKILLS or EDUCATION",
    ),
    include_optional: bool = Query(
        default=True,
        description=(
            "True includes optional questions; false returns "
            "mandatory questions only."
        ),
    ),
) -> dict[str, Any]:
    """
    Return candidate-facing questions for a role.

    Language selection and translation fallback are handled by
    question_bank_service.py.
    """

    try:
        questions = get_candidate_questions(
            role_id=role_id,
            language=language,
            category=category,
            include_optional=include_optional,
        )

        return {
            "success": True,
            "role_id": role_id,
            "requested_language": language,
            "category": category,
            "include_optional": include_optional,
            "total_questions": len(questions),
            "questions": questions,
        }

    except ValueError as exc:
        # Invalid language, role, category, or query configuration.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid screening question request.",
        ) from exc

    except QuestionBankError as exc:
        raise _handle_question_bank_error(exc) from exc


# ============================================================
# GET ONE QUESTION
# ============================================================

@router.get(
    "/questions/{question_id}",
    summary="Get one screening question",
)
def retrieve_screening_question(
    question_id: str,
    language: str = Query(
        default="en",
        min_length=2,
        max_length=10,
        description="Requested language code, e.g. en, ml, hi",
    ),
) -> dict[str, Any]:
    """
    Retrieve one candidate-safe question in the requested language.
    """

    try:
        question = get_candidate_question(
            question_id=question_id,
            language=language,
        )

        if question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Screening question not found.",
            )

        return {
            "success": True,
            "question": question,
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid screening question request.",
        ) from exc

    except QuestionBankError as exc:
        raise _handle_question_bank_error(exc) from exc


# ============================================================
# EVALUATE SUBMITTED SCREENING SESSION
# ============================================================

@router.post(
    "/sessions/{session_id}/evaluate",
    summary="Evaluate a submitted screening session",
)
def evaluate_screening_session_endpoint(
    session_id: str,
    force: bool = Query(
        default=False,
        description=(
            "Re-evaluate an existing report when true. "
            "Restrict this operation to authorized users in production."
        ),
    ),
) -> dict[str, Any]:
    """
    Evaluate submitted answers and persist the evaluation report.

    Session validation, answer evaluation, scoring, and persistence
    belong to the evaluation service.
    """

    try:
        report = evaluate_screening_session(
            session_id,
            force=force,
        )

        return {
            "success": True,
            "message": "Screening evaluation processed successfully.",
            "evaluation": report,
        }

    except ScreeningEvaluationError as exc:
        raise _handle_evaluation_error(
            exc,
            operation="evaluate_session",
        ) from exc

    except ValueError as exc:
        logger.warning(
            "Invalid screening evaluation request: %s",
            type(exc).__name__,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid screening evaluation request.",
        ) from exc

    except Exception as exc:
        logger.error(
            "Unexpected HR screening evaluation failure: %s",
            type(exc).__name__,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during evaluation.",
        ) from exc



# ============================================================
# RECRUITER REVIEW
# ============================================================

@router.post(
    "/sessions/{session_id}/review",
    summary="Review a screening answer",
)
def review_screening_question_endpoint(
    session_id: str,
    request: RecruiterQuestionReviewRequest,
) -> dict[str, Any]:
    """Record recruiter feedback and a score for one answer."""

    try:
        report = review_screening_question(
            session_id,
            question_id=request.question_id,
            reviewer_id=request.reviewer_id,
            score=request.score,
            max_score=request.max_score,
            feedback=request.feedback,
        )

        return {
            "success": True,
            "message": "Recruiter review saved successfully.",
            "evaluation": report,
        }

    except ScreeningEvaluationError as exc:
        # Invalid review state or missing evaluation report.
        message = str(exc)

        if "not found" in message.lower() or "does not belong" in message.lower():
            code = status.HTTP_404_NOT_FOUND
        else:
            code = status.HTTP_409_CONFLICT

        raise HTTPException(
            status_code=code,
            detail=message,
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

# ============================================================
# GET SAVED EVALUATION REPORT
# ============================================================

@router.get(
    "/sessions/{session_id}/evaluation",
    summary="Get screening evaluation report",
)
def retrieve_screening_evaluation(
    session_id: str,
) -> dict[str, Any]:
    """Retrieve a previously saved evaluation report."""

    try:
        report = get_screening_evaluation(session_id)

        return {
            "success": True,
            "evaluation": report,
        }

    except ScreeningEvaluationError as exc:
        raise _handle_evaluation_error(
            exc,
            operation="retrieve_report",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid screening report request.",
        ) from exc

    except Exception as exc:
        logger.error(
            "Unexpected HR screening report retrieval failure: %s",
            type(exc).__name__,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve screening evaluation.",
        ) from exc


# ============================================================
# RECRUITER CANDIDATE-LEVEL DECISION
# ============================================================

@router.post(
    "/sessions/{session_id}/decision",
    summary="Record an overall recruiter decision",
    status_code=status.HTTP_201_CREATED,
)
def save_recruiter_decision_endpoint(
    session_id: str,
    request: RecruiterDecisionRequest,
) -> dict[str, Any]:
    """
    Save the recruiter's overall decision for a screening session.

    Decisions are stored separately from question-level reviews.
    A saved evaluation report must exist before a decision is recorded.
    """

    try:
        review = save_recruiter_decision(
            session_id,
            reviewer_id=request.reviewer_id,
            decision=request.decision.value,
            comments=request.comments,
        )

        return {
            "success": True,
            "message": "Recruiter decision saved successfully.",
            "review": review,
        }

    except ScreeningSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screening session not found.",
        ) from exc
        
    
    except RecruiterDecisionPrerequisiteError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "Evaluate the screening session before "
                "recording a recruiter decision."
            ),
        ) from exc


    except ScreeningEvaluationError as exc:
        message = str(exc)

        if "no evaluation report exists" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Evaluate the screening session before recording a decision.",
            ) from exc

        logger.error(
            "Recruiter decision save failed: %s",
            type(exc).__name__,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save the recruiter decision.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recruiter decision request.",
        ) from exc

    except Exception as exc:
        logger.error(
            "Unexpected recruiter decision failure: %s",
            type(exc).__name__,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while saving the decision.",
        ) from exc



# ============================================================
# TRANSCRIPT SKILL EXTRACTION
# ============================================================

@router.post(
    "/sessions/{session_id}/transcripts/{transcript_id}/skills",
    summary="Extract and save skills from a transcript",
)
def extract_transcript_skills_endpoint(
    session_id: str,
    transcript_id: str,
) -> dict[str, Any]:
    """
    Extract skills from a saved transcript and persist the result.

    Transcript retrieval, skill extraction, and result persistence
    remain the responsibility of the service layer.
    """

    try:
        result = process_saved_transcript_skills(
            session_id=session_id,
            transcript_id=transcript_id,
        )

        return {
            "success": True,
            "message": "Transcript skills processed successfully.",
            "skill_extraction": result,
        }

    except TranscriptSkillWorkflowError as exc:
        # The workflow wraps errors from the transcript service.
        if isinstance(exc.__cause__, TranscriptNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript not found.",
            ) from exc

        logger.error(
            "Transcript skill extraction failed: %s",
            type(exc).__name__,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process transcript skills.",
        ) from exc

    except Exception as exc:
        logger.error(
            "Unexpected transcript skill extraction failure: %s",
            type(exc).__name__,
            exc_info=(type(exc), exc, exc.__traceback__),
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during skill extraction.",
        ) from exc
