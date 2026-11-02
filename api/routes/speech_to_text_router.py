
"""
speech_to_text_router.py

Responsibilities
----------------
1. Accept uploaded screening audio.
2. Route English, Malayalam, and Hindi to the hybrid STT service.
3. Report silence and partial-answer diagnostics.
4. Validate and persist valid transcripts through transcript_service.
5. Preserve original recognized text.
"""

import logging
import tempfile

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.schemas.transcript_schema import TranscriptCreate
from api.service.hybrid_speech_to_text_service import (
    HybridSpeechToTextService,
)
from api.service.partial_answer_detection_service import (
    PartialAnswerDetectionService,
)
from api.service.audio_silence_detection_service import (
    AudioSilenceDetectionService,
)
from api.service.transcript_service import (
    TranscriptAlreadyExistsError,
    TranscriptInputError,
    TranscriptPersistenceError,
    TranscriptSessionNotFoundError,
    create_transcript,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/speech-to-text",
    tags=["Speech-to-Text"],
)

SUPPORTED_LANGUAGES = {"en", "ml", "hi"}
ALLOWED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".webm",
    ".flac",
}
MAX_AUDIO_BYTES = 25 * 1024 * 1024


@lru_cache(maxsize=1)
def _get_stt_service() -> HybridSpeechToTextService:
    """Reuse the hybrid service rather than recreating it per request."""
    return HybridSpeechToTextService()


@lru_cache(maxsize=1)
def _get_partial_detector() -> PartialAnswerDetectionService:
    return PartialAnswerDetectionService()


@lru_cache(maxsize=1)
def _get_silence_detector() -> AudioSilenceDetectionService:
    return AudioSilenceDetectionService()


def _save_upload_to_temp(file: UploadFile) -> tuple[Path, str]:
    """
    Write uploaded audio to a temporary file.

    The client filename is used only to select an allowed suffix;
    it is never used as a filesystem path.
    """
    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported audio file extension.",
        )

    temp_path: Path | None = None
    total_bytes = 0

    try:
        with tempfile.NamedTemporaryFile(
            prefix="zechpath_audio_",
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

            while True:
                chunk = file.file.read(1024 * 1024)

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > MAX_AUDIO_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Audio upload exceeds the 25 MB limit.",
                    )

                temp_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded audio file is empty.",
            )

        return temp_path, suffix

    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


@router.post("/transcribe")
def transcribe_screening_audio(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    candidate_id: str = Form(...),
    job_id: str = Form(...),
    question_id: str = Form(...),
    language: str = Form(...),
    interrupted: bool = Form(False),
) -> dict[str, Any]:
    """
    Transcribe one audio answer and save it against its screening question.

    `interrupted` is a caller-provided signal. It is not automatically
    inferred from the audio.
    """
    language = language.strip().lower()

    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail="Language must be en, ml, or hi.",
        )

    temp_path: Path | None = None

    try:
        temp_path, _ = _save_upload_to_temp(file)

        # Diagnostic only: inability to analyze audio must not prevent STT.
        try:
            is_silent = _get_silence_detector().is_silent(temp_path)
        except Exception:
            logger.exception("Silence analysis failed.")
            is_silent = None

        result = _get_stt_service().transcribe_file(
            str(temp_path),
            language=language,
            interrupted=interrupted,
        )

        original_text = result.get("original_text", "")
        if not isinstance(original_text, str):
            original_text = ""

        original_text = original_text.strip()

        # Do not attempt to persist a blank transcript.
        if not original_text:
            return {
                "success": True,
                "message": "No speech was recognized; no transcript was saved.",
                "transcript_saved": False,
                "transcription_status": result.get(
                    "status", "silence_or_no_speech"
                ),
                "silence_detected": is_silent,
                "is_partial": False,
                "partial_reason": None,
                "interruption_reported": interrupted,
                "transcript": None,
            }

        partial_result = _get_partial_detector().detect(
            text=original_text,
            language=language,
        )

        duration_seconds = result.get("duration_seconds")
        duration_ms = (
            round(float(duration_seconds) * 1000)
            if isinstance(duration_seconds, (int, float))
            and duration_seconds >= 0
            else None
        )

        segments = result.get("segments") or []

        payload = TranscriptCreate(
            session_id=session_id,
            candidate_id=candidate_id,
            job_id=job_id,
            question_id=question_id,
            language=language,
            original_text=original_text,
            segments=segments,
            transcription={
                "provider": result.get("provider"),
                "model_version": result.get("model"),
                "confidence": None,
            },
            timing={
                "transcribed_at": datetime.now(timezone.utc),
                "duration_ms": duration_ms,
            },
            normalization={
                "language_preserved": True,
                "pii_redacted": False,
            },
        )

        # Existing service validates session ownership and question
        # assignment, normalizes the text, and saves atomically.
        record = create_transcript(payload)

        return {
            "success": True,
            "message": "Audio transcribed and transcript saved.",
            "transcript_saved": True,
            "transcription_status": result.get("status", "transcribed"),
            "silence_detected": is_silent,
            "is_partial": partial_result.is_partial,
            "partial_reason": partial_result.reason,
            "interruption_reported": interrupted,
            "transcript": record.model_dump(mode="json"),
        }

    except HTTPException:
        raise

    except TranscriptSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except TranscriptInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except TranscriptAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    except TranscriptPersistenceError as exc:
        raise HTTPException(
            status_code=500,
            detail="Transcript could not be saved.",
        ) from exc

    except FileNotFoundError as exc:
        logger.exception("Audio file was not available to the STT service.")
        raise HTTPException(
            status_code=400,
            detail="The audio file could not be processed.",
        ) from exc

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    except Exception as exc:
        logger.exception("Speech-to-text request failed.")
        raise HTTPException(
            status_code=500,
            detail="Speech-to-text processing failed.",
        ) from exc

    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

        try:
            file.file.close()
        except Exception:
            logger.warning("Unable to close uploaded audio stream.")
