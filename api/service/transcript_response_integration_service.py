"""Link processed transcripts to screening answers and synchronize reviewed text.

This module intentionally reuses the existing JSON-backed screening response
service. It does not create a second response store or alter the response schema.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from api.schemas.transcript_integration_schema import (
    TranscriptResponseLinkRequest,
    TranscriptReviewUpdate,
)
from api.schemas.transcript_schema import TranscriptRecord, TranscriptReview
from api.service import screening_response_service as response_store
from api.service.transcript_service import (
    TranscriptInputError,
    TranscriptNotFoundError,
    TranscriptPersistenceError,
    get_transcript,
)

logger = logging.getLogger(__name__)


class TranscriptIntegrationError(Exception):
    """Base error for transcript/response integration."""


class TranscriptLinkConflictError(TranscriptIntegrationError):
    """Raised when linking would overwrite an existing answer."""


class TranscriptReviewRequiredError(TranscriptIntegrationError):
    """Raised when evaluation is attempted before linked transcripts are reviewed."""


class TranscriptIntegrationDataError(TranscriptIntegrationError):
    """Raised when transcript, session, or response data is inconsistent."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _validate_transcript_matches_session(
    transcript: TranscriptRecord,
    session: dict[str, Any],
    *,
    candidate_id: str,
) -> None:
    if transcript.session_id != session.get("session_id"):
        raise TranscriptIntegrationDataError("Transcript session does not match the requested session.")
    if transcript.candidate_id != session.get("candidate_id") or transcript.candidate_id != candidate_id:
        raise TranscriptIntegrationDataError("Transcript candidate does not match the screening session.")
    if transcript.job_id != session.get("job_id"):
        raise TranscriptIntegrationDataError("Transcript job does not match the screening session.")


def link_transcript_to_screening_response(
    *,
    session_id: str,
    transcript_id: str,
    request: TranscriptResponseLinkRequest,
) -> dict[str, Any]:
    """Attach a processed transcript to its assigned TEXT question.

    A pending recruiter review is retained in the linked metadata. The linked
    text cannot be used for evaluation until it is approved or corrected.
    """
    if not isinstance(request, TranscriptResponseLinkRequest):
        request = TranscriptResponseLinkRequest.model_validate(request)

    session_id = response_store._validate_identifier(session_id, "session_id")
    candidate_id = response_store._validate_identifier(request.candidate_id, "candidate_id")

    with response_store._STORAGE_LOCK:
        session = response_store._load_session(session_id)
        if session.get("status") not in response_store.ALLOWED_SESSION_STATUSES:
            raise response_store.ScreeningSessionStateError(
                "This screening session cannot accept transcript responses."
            )
        if session.get("candidate_id") != candidate_id:
            raise response_store.ScreeningOwnershipError(
                "Candidate does not own this screening session."
            )

        try:
            transcript = get_transcript(session_id=session_id, transcript_id=transcript_id)
        except (TranscriptInputError, TranscriptNotFoundError, TranscriptPersistenceError):
            raise

        _validate_transcript_matches_session(transcript, session, candidate_id=candidate_id)
        if _enum_value(transcript.status) != "PROCESSED":
            raise TranscriptIntegrationDataError("Only PROCESSED transcripts can be linked to a screening answer.")

        question_map = response_store._build_question_map(session)
        question_key = response_store._normalize_question_id(transcript.question_id)
        question = question_map.get(question_key)
        if question is None:
            raise response_store.ScreeningQuestionError(
                "Transcript question is not assigned to this screening session."
            )
        if response_store._get_answer_type(question) != "TEXT":
            raise TranscriptIntegrationDataError(
                "Voice transcripts can only be linked to TEXT questions."
            )

        responses = response_store._load_responses(session_id)
        response_candidate = responses.get("candidate_id")
        if response_candidate and response_candidate != candidate_id:
            raise TranscriptIntegrationDataError("Stored response candidate does not match the screening session.")
        response_job = responses.get("job_id")
        if response_job and response_job != transcript.job_id:
            raise TranscriptIntegrationDataError("Stored response job does not match the screening session.")

        answers = dict(responses.get("answers", {}))
        canonical_question_id = question.get("question_id", question.get("id"))
        existing = answers.get(canonical_question_id)
        existing_link = (existing or {}).get("transcript") if isinstance(existing, dict) else None

        if isinstance(existing_link, dict) and existing_link.get("transcript_id") == transcript.transcript_id:
            return {
                "success": True,
                "message": "Transcript is already linked to this screening answer.",
                "session_id": session_id,
                "question_id": canonical_question_id,
                "transcript_id": transcript.transcript_id,
                "review_status": _enum_value(transcript.review.status),
                "idempotent": True,
            }

        if isinstance(existing, dict) and existing.get("answered") and not request.replace_existing:
            raise TranscriptLinkConflictError(
                "An answer already exists for this question. Set replace_existing=true to replace it."
            )

        now = _utc_now()
        normalized_text = transcript.normalized_text or transcript.original_text
        if not normalized_text.strip():
            raise TranscriptIntegrationDataError("Transcript contains no usable answer text.")

        answers[canonical_question_id] = {
            "question_id": canonical_question_id,
            "answer": normalized_text,
            "selected_options": None,
            "answered": True,
            "updated_at": now,
            "transcript": {
                "transcript_id": transcript.transcript_id,
                "source": _enum_value(transcript.source),
                "language": transcript.language,
                "status": _enum_value(transcript.status),
                "review_status": _enum_value(transcript.review.status),
                "linked_at": now,
            },
        }
        responses["session_id"] = session_id
        responses["candidate_id"] = candidate_id
        responses["job_id"] = transcript.job_id
        responses["answers"] = answers
        responses["updated_at"] = now

        # Persist the response first, matching submit_screening_responses' ordering.
        response_store._write_json_atomic(response_store._response_path(session_id), responses)
        session["status"] = "IN_PROGRESS"
        session["updated_at"] = now
        response_store._write_json_atomic(response_store._session_path(session_id), session)

        return {
            "success": True,
            "message": "Transcript linked to screening response.",
            "session_id": session_id,
            "candidate_id": candidate_id,
            "job_id": transcript.job_id,
            "question_id": canonical_question_id,
            "transcript_id": transcript.transcript_id,
            "review_status": _enum_value(transcript.review.status),
            "answer_saved": True,
            "idempotent": False,
            "updated_at": now,
        }


def _transcript_path(session_id: str, transcript_id: str) -> Path:
    # The existing service owns path validation; reuse its validated path helper.
    from api.service import transcript_service
    return transcript_service._transcript_file_path(session_id, transcript_id)


def _replace_json_atomically(target: Path, data: dict[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=target.parent,
            prefix=f".{target.stem}_", suffix=".tmp", delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(data, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, target)
    except OSError as exc:
        logger.exception("Unable to update transcript review record.")
        raise TranscriptPersistenceError("Unable to update transcript review.") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Unable to remove temporary transcript review file.")


def update_transcript_review(
    *,
    session_id: str,
    transcript_id: str,
    request: TranscriptReviewUpdate,
) -> TranscriptRecord:
    """Approve or correct a transcript, recording reviewer and timestamp."""
    if not isinstance(request, TranscriptReviewUpdate):
        request = TranscriptReviewUpdate.model_validate(request)

    with response_store._STORAGE_LOCK:
        record = get_transcript(session_id=session_id, transcript_id=transcript_id)
        if _enum_value(record.status) != "PROCESSED":
            raise TranscriptIntegrationDataError("Only PROCESSED transcripts can be reviewed.")

        now = datetime.now(timezone.utc)
        review = TranscriptReview(
            status=request.status,
            corrected_text=request.corrected_text,
            reviewer_id=request.reviewer_id.strip(),
            reviewed_at=now,
        )
        updated_record = record.model_copy(update={"review": review, "updated_at": now})
        target = _transcript_path(session_id, transcript_id)
        _replace_json_atomically(target, updated_record.model_dump(mode="json"))
        return updated_record


def synchronize_linked_transcripts_for_evaluation(
    session_id: str,
    responses: dict,
) -> dict:
    """
    Synchronize linked transcripts before screening evaluation.

    Rules:
    1. Answers without transcript metadata remain unchanged.
    2. Linked transcripts must exist and match the screening session,
       candidate, and question.
    3. Pending transcripts block evaluation.
    4. Only APPROVED and CORRECTED transcripts can be evaluated.
    5. APPROVED transcripts use normalized_text, falling back to
       original_text.
    6. CORRECTED transcripts use corrected_text.
    7. Updated responses are persisted atomically.
    """
    if not isinstance(responses, dict):
        raise TranscriptIntegrationDataError(
            "Screening responses must be a dictionary."
        )

    answers = responses.get("answers")

    if not isinstance(answers, (dict, list)):
        raise TranscriptIntegrationDataError(
            "Screening response answers must be a dictionary or list."
        )

    # Normalize the answer collection for iteration while preserving
    # the original response structure for persistence.
    if isinstance(answers, dict):
        answer_items = list(answers.items())
        answers_are_dict = True
    else:
        answer_items = [
            (
                answer.get("question_id"),
                answer,
            )
            for answer in answers
            if isinstance(answer, dict)
        ]
        answers_are_dict = False

    if not answers_are_dict and len(answer_items) != len(answers):
        raise TranscriptIntegrationDataError(
            "Screening answer record is invalid."
        )

    
    response_candidate_id = responses.get("candidate_id")

    changed = False


    for question_id, answer_record in answer_items:
        if not isinstance(answer_record, dict):
            raise TranscriptIntegrationDataError(
                "Screening answer record is invalid."
            )

        # Normal typed answers do not need transcript synchronization.
        
        transcript_metadata = answer_record.get("transcript")
        if transcript_metadata is None:
            continue

        # A candidate ID is required only when validating a linked transcript.
        if (
            not isinstance(response_candidate_id, str)
            or not response_candidate_id.strip()
        ):
            raise TranscriptIntegrationDataError(
                "Screening response candidate ID is missing or invalid "
                "for a linked transcript."
            )


        if not isinstance(transcript_metadata, dict):
            raise TranscriptIntegrationDataError(
                "Linked transcript metadata is invalid."
            )

        transcript_id = transcript_metadata.get("transcript_id")

        if not isinstance(transcript_id, str) or not transcript_id.strip():
            raise TranscriptIntegrationDataError(
                "Linked transcript ID is missing or invalid."
            )

        # Load the linked transcript.
        try:
            transcript = get_transcript(
                session_id=session_id,
                transcript_id=transcript_id,
            )
        except Exception as exc:
            raise TranscriptIntegrationDataError(
                "Unable to load a linked transcript. "
                "Verify the transcript record and storage."
            ) from exc

        if transcript is None:
            raise TranscriptIntegrationDataError(
                "A linked transcript could not be found."
            )

        # Validate that the transcript belongs to this screening session.
        if transcript.session_id != session_id:
            raise TranscriptIntegrationDataError(
                "Linked transcript session does not match."
            )

        if transcript.candidate_id != response_candidate_id:
            raise TranscriptIntegrationDataError(
                "Linked transcript candidate does not match."
            )

        # Compare question IDs case-insensitively.
        transcript_question_id = response_store._normalize_question_id(
            transcript.question_id
        )
        response_question_id = response_store._normalize_question_id(
            question_id
        )

        if transcript_question_id != response_question_id:
            raise TranscriptIntegrationDataError(
                "Linked transcript question does not match its screening answer."
            )

        if transcript.status != "PROCESSED":
            raise TranscriptIntegrationDataError(
                "Linked transcript has not been processed."
            )

        # Resolve the authoritative review status from the transcript.
        review = transcript.review

        if review is None:
            review_status = "PENDING"
        else:
            review_status = (
                review.status.value
                if hasattr(review.status, "value")
                else str(review.status)
            )
            review_status = review_status.strip().upper()

        if review_status == "PENDING":
            raise TranscriptReviewRequiredError(
                "Evaluation cannot proceed until all linked transcripts "
                "have been reviewed."
            )

        if review_status not in {"APPROVED", "CORRECTED"}:
            raise TranscriptIntegrationDataError(
                "Linked transcript has an unsupported review status."
            )

        # Select the text that is allowed to reach evaluation.
        if review_status == "CORRECTED":
            final_text = review.corrected_text

            if not isinstance(final_text, str) or not final_text.strip():
                raise TranscriptIntegrationDataError(
                    "Corrected transcript text is missing."
                )
        else:
            final_text = (
                transcript.normalized_text
                or transcript.original_text
            )

            if not isinstance(final_text, str) or not final_text.strip():
                raise TranscriptIntegrationDataError(
                    "Approved transcript text is missing."
                )

        # Update the screening answer.
        if answer_record.get("answer") != final_text:
            answer_record["answer"] = final_text
            changed = True

        # Keep transcript metadata synchronized with the review record.
        updated_metadata = dict(transcript_metadata)
        updated_metadata["review_status"] = review_status

        if review is not None:
            updated_metadata["reviewer_id"] = review.reviewer_id
            updated_metadata["reviewed_at"] = (
                review.reviewed_at.isoformat()
                if hasattr(review.reviewed_at, "isoformat")
                else review.reviewed_at
            )

        updated_metadata["status"] = transcript.status

        if updated_metadata != transcript_metadata:
            answer_record["transcript"] = updated_metadata
            changed = True

    # Persist only when synchronization changed the response.
    if changed:
        with response_store._STORAGE_LOCK:
            response_store._write_json_atomic(
                response_store._response_path(session_id),
                responses,
            )

    return responses