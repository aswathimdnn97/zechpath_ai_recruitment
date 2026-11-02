
"""
audio_transcript_pipeline_service.py

Responsibilities
----------------
1. Transcribe audio using IndicConformer.
2. Convert transcription output into TranscriptCreate input.
3. Delegate normalization, validation, session verification,
   and JSON persistence to transcript_service.py.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from api.schemas.transcript_schema import (
    TranscriptCreate,
    TranscriptMetadata,
    TranscriptTiming,
)
from api.service.indicconformer_speech_to_text_service import (
    transcribe_audio,
)
from api.service.transcript_service import create_transcript

logger = logging.getLogger(__name__)

LanguageCode = Literal["en", "ml", "hi"]
Decoder = Literal["ctc", "rnnt"]


class AudioTranscriptPipelineError(Exception):
    """Raised when audio transcription or pipeline preparation fails."""


def transcribe_and_store_audio(
    *,
    audio_path: str | Path,
    session_id: str,
    candidate_id: str,
    job_id: str,
    question_id: str,
    language: LanguageCode,
    decoding_method: Decoder = "rnnt",
) -> dict[str, Any]:
    """
    Transcribe an audio recording and save the validated transcript.

    The screening session must already exist. Candidate, job,
    language, and question IDs must match that session.
    """

    path = Path(audio_path)

    if not path.is_file():
        raise AudioTranscriptPipelineError(
            f"Audio file does not exist: {path}"
        )

    # 1. Speech-to-text conversion.
    try:
        result = transcribe_audio(
            audio_path=path,
            language=language,
            decoding_method=decoding_method,
        )
    except Exception as exc:
        logger.exception("IndicConformer transcription failed.")
        raise AudioTranscriptPipelineError(
            "Audio transcription failed."
        ) from exc

    if result.get("status") != "SUCCESS":
        raise AudioTranscriptPipelineError(
            "IndicConformer did not return a successful result."
        )

    raw_text = result.get("transcript")

    if not isinstance(raw_text, str) or not raw_text.strip():
        raise AudioTranscriptPipelineError(
            "IndicConformer returned an empty transcript."
        )

    # 2. Map model output to the existing transcript schema.
    duration_seconds = result.get("audio_duration_seconds")

    duration_ms = (
        round(duration_seconds * 1000)
        if isinstance(duration_seconds, (int, float))
        and duration_seconds >= 0
        else None
    )

    now = datetime.now(timezone.utc)

    payload = TranscriptCreate(
        session_id=session_id,
        candidate_id=candidate_id,
        job_id=job_id,
        question_id=question_id,
        language=language,
        original_text=raw_text,
        transcription=TranscriptMetadata(
            provider="AI4Bharat IndicConformer",
            model_version=str(result.get("model_name", ""))[:100],
        ),
        timing=TranscriptTiming(
            transcribed_at=now,
            duration_ms=duration_ms,
        ),
    )

    # 3. Delegate normalization, session verification, schema
    # validation, ID generation, and JSON persistence.
    try:
        record = create_transcript(payload)
    except Exception:
        logger.exception(
            "Transcript validation or persistence failed."
        )
        raise

    logger.info(
        "Audio transcript pipeline completed | "
        "session_id=%s | transcript_id=%s | language=%s",
        record.session_id,
        record.transcript_id,
        record.language,
    )

    # 4. Return the persisted record and additional model-run metadata.
    return {
        "success": True,
        "transcript": record.model_dump(mode="json"),
        "speech_to_text": {
            "model_name": result.get("model_name"),
            "decoding_method": result.get("decoding_method"),
            "sample_rate": result.get("sample_rate"),
            "audio_duration_seconds": duration_seconds,
            "processing_time_seconds": result.get(
                "processing_time_seconds"
            ),
        },
    }
