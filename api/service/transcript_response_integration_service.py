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
        answer_text = (
            transcript.cleaned_text
            or transcript.normalized_text
            or transcript.original_text
        )
        if not answer_text.strip():
            raise TranscriptIntegrationDataError("Transcript contains no usable answer text.")

        answers[canonical_question_id] = {
            "question_id": canonical_question_id,
            "answer": answer_text,
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

        # Preserve every completed review event. The immutable source fields
        # (especially original_text) are copied through unchanged.
        history = list(record.review_history)
        # Backfill a prior completed review if this record predates the
        # review_history field or has an incomplete audit trail.
        if (
            _enum_value(record.review.status) != "PENDING"
            and (not history or history[-1] != record.review)
        ):
            history.append(record.review)
        history.append(review)
        updated_data = record.model_dump(mode="python")
        updated_data.update({
            "review": review,
            "review_history": history,
            "updated_at": now,
        })
        updated_record = TranscriptRecord.model_validate(updated_data)

        target = _transcript_path(session_id, transcript_id)
        _replace_json_atomically(target, updated_record.model_dump(mode="json"))
        return updated_record



def synchronize_linked_transcripts_for_evaluation(
    *,
    session_id: str,
    responses: dict[str, Any],
) -> dict[str, Any]:
    """
    Refresh linked screening answers using the latest reviewed transcripts.

    Supports both existing answer formats:
        1. List:
           [{"question_id": "Q001", "answer": "..."}]

        2. Dictionary:
           {"Q001": {"answer": "..."}}

    Rules:
        - Pending transcripts block evaluation.
        - Approved transcripts use cleaned/normalized/original text.
        - Corrected transcripts use recruiter-corrected text.
        - Unlinked answers remain unchanged.
        - Updated responses are persisted atomically.
    """

    if not isinstance(responses, dict):
        raise TranscriptIntegrationDataError(
            "Stored screening responses are invalid."
        )

    answers = responses.get("answers")

    # ---------------------------------------------------------
    # 1. Support both list-based and dictionary-based answers
    # ---------------------------------------------------------
    if isinstance(answers, list):
        answer_items = []

        for answer in answers:
            if not isinstance(answer, dict):
                raise TranscriptIntegrationDataError(
                    "Stored screening answers contain an invalid entry."
                )

            question_id = answer.get("question_id")

            if not isinstance(question_id, str) or not question_id.strip():
                raise TranscriptIntegrationDataError(
                    "A stored answer is missing its question ID."
                )

            answer_items.append((question_id, answer))

    elif isinstance(answers, dict):
        answer_items = []

        for question_id, answer in answers.items():
            if not isinstance(answer, dict):
                raise TranscriptIntegrationDataError(
                    "Stored screening answers contain an invalid entry."
                )

            answer_items.append((str(question_id), answer))

    else:
        raise TranscriptIntegrationDataError(
            "Stored screening answers are invalid."
        )

    changed = False
    now = _utc_now()

    # ---------------------------------------------------------
    # 2. Synchronize linked transcripts
    # ---------------------------------------------------------
    with response_store._STORAGE_LOCK:

        for question_id, answer in answer_items:

            link = answer.get("transcript")

            # Ordinary screening answers do not need synchronization.
            if not isinstance(link, dict):
                continue

            transcript_id = link.get("transcript_id")

            if not transcript_id:
                continue

            # -------------------------------------------------
            # 3. Retrieve linked transcript
            # -------------------------------------------------
            try:
                transcript = get_transcript(
                    session_id=session_id,
                    transcript_id=str(transcript_id),
                )

            except (
                TranscriptInputError,
                TranscriptNotFoundError,
                TranscriptPersistenceError,
            ) as exc:
                raise TranscriptIntegrationDataError(
                    "A linked transcript record is missing or invalid."
                ) from exc

            # -------------------------------------------------
            # 4. Validate transcript ownership and question
            # -------------------------------------------------
            if str(transcript.question_id) != str(question_id):
                raise TranscriptIntegrationDataError(
                    "Linked transcript question does not match "
                    "its screening answer."
                )

            if str(transcript.candidate_id) != str(
                responses.get("candidate_id")
            ):
                raise TranscriptIntegrationDataError(
                    "Linked transcript candidate does not match "
                    "its screening response."
                )

            if str(transcript.session_id) != str(session_id):
                raise TranscriptIntegrationDataError(
                    "Linked transcript belongs to another session."
                )

            # -------------------------------------------------
            # 5. Validate recruiter review status
            # -------------------------------------------------
            review_status = _enum_value(transcript.review.status)

            if review_status == "PENDING":
                raise TranscriptReviewRequiredError(
                    "Transcript review is required before evaluation "
                    f"(question_id={question_id})."
                )

            if review_status not in {"APPROVED", "CORRECTED"}:
                raise TranscriptIntegrationDataError(
                    "Transcript has an unsupported review status."
                )

            # -------------------------------------------------
            # 6. Select final reviewed transcript text
            # -------------------------------------------------
            
            if review_status == "CORRECTED":
                final_text = getattr(
                    transcript.review,
                    "corrected_text",
                    None,
                )
            else:
                final_text = (
                    getattr(transcript, "cleaned_text", None)
                    or getattr(transcript, "normalized_text", None)
                    or getattr(transcript, "original_text", None)
                )

            if not isinstance(final_text, str) or not final_text.strip():
                raise TranscriptIntegrationDataError(
                    "Reviewed transcript has no usable answer text."
                )

            final_text = final_text.strip()

            # -------------------------------------------------
            # 7. Prepare synchronized transcript metadata
            # -------------------------------------------------
            transcript_status = _enum_value(transcript.status)

            reviewed_at_value = getattr(
                transcript.review,
                "reviewed_at",
                None,
            )

            reviewed_at = (
                reviewed_at_value.isoformat()
                if reviewed_at_value
                else None
            )

            reviewer_id = getattr(
                transcript.review,
                "reviewer_id",
                None,
            )

            updated_link = {
                **link,
                "status": transcript_status,
                "review_status": review_status,
                "reviewer_id": reviewer_id,
                "reviewed_at": reviewed_at,
            }

            # -------------------------------------------------
            # 8. Update answer and transcript metadata
            # -------------------------------------------------
            answer_changed = (
                answer.get("answer") != final_text
                or answer.get("answered") is not True
                or link != updated_link
            )

            if answer_changed:
                answer["answer"] = final_text
                answer["answered"] = True
                answer["updated_at"] = now
                answer["transcript"] = updated_link

                changed = True

    # ---------------------------------------------------------
    # 9. Persist only when changes were made
    # ---------------------------------------------------------
    if changed:
        responses["updated_at"] = now

        try:
            with response_store._STORAGE_LOCK:
                response_store._write_json_atomic(
                    response_store._response_path(session_id),
                    responses,
                )

        except (OSError, TypeError, ValueError) as exc:
            raise TranscriptIntegrationDataError(
                "Failed to persist synchronized screening responses."
            ) from exc

    return responses
