"""
hybrid_speech_to_text_service.py

Responsibilities
----------------
1. Route English audio to local Whisper.
2. Route Malayalam and Hindi audio to Indic Conformer.
3. Return consistent transcript and segment fields.
4. Convert Whisper segment timestamps from seconds to milliseconds.
5. Preserve the distinction between reported interruption and detection.
6. Avoid fabricating segment timing or confidence values.
7. Measure provider and total processing time for optimization.
"""

import logging
from pathlib import Path
from time import perf_counter
from typing import Any

from api.service.speech_to_text_service import SpeechToTextService
from api.service.indicconformer_speech_to_text_service import (
    transcribe_audio,
)

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {"en", "ml", "hi"}
SUPPORTED_DECODING_METHODS = {"rnnt", "ctc"}


class HybridSpeechToTextError(RuntimeError):
    """Raised when hybrid transcription fails."""


def _map_whisper_segments(
    segments: list[dict[str, Any]],
    duration_seconds: float | None,
) -> list[dict[str, Any]]:
    """Convert valid Whisper segments to the transcript schema format."""
    mapped: list[dict[str, Any]] = []

    for segment in segments:
        text = str(segment.get("text") or "").strip()
        start = segment.get("start")
        end = segment.get("end")

        if not text or start is None or end is None:
            continue

        try:
            start_ms = round(float(start) * 1000)
            end_ms = round(float(end) * 1000)
        except (TypeError, ValueError, OverflowError):
            continue

        if start_ms < 0 or end_ms <= start_ms:
            continue

        if duration_seconds is not None:
            duration_ms = round(duration_seconds * 1000)
            if end_ms > duration_ms:
                continue

        mapped.append({
            "start_ms": start_ms,
            "end_ms": end_ms,
            "text": text,
            "confidence": None,
        })

    mapped.sort(key=lambda item: (item["start_ms"], item["end_ms"]))

    non_overlapping: list[dict[str, Any]] = []
    previous_end = 0

    for segment in mapped:
        if segment["start_ms"] < previous_end:
            continue
        non_overlapping.append(segment)
        previous_end = segment["end_ms"]

    return non_overlapping


class HybridSpeechToTextService:
    """Language-based speech recognition router."""

    def __init__(
        self,
        whisper_model: str = "base",
        indic_decoding_method: str = "rnnt",
    ) -> None:
        method = indic_decoding_method.strip().lower()

        if method not in SUPPORTED_DECODING_METHODS:
            raise ValueError(
                f"Unsupported Indic decoding method '{indic_decoding_method}'. "
                f"Supported methods: {sorted(SUPPORTED_DECODING_METHODS)}"
            )

        self.indic_decoding_method = method
        self.whisper_service = SpeechToTextService(
            model_name=whisper_model
        )

    def transcribe_file(
        self,
        audio_path: str | Path,
        language: str,
        *,
        interrupted: bool = False,
    ) -> dict[str, Any]:
        total_start = perf_counter()
        language = language.strip().lower()

        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{language}'. "
                f"Supported languages: {sorted(SUPPORTED_LANGUAGES)}"
            )

        path = Path(audio_path)

        if not path.is_file():
            raise FileNotFoundError(f"Audio file does not exist: {path}")

        provider_seconds = 0.0
        mapping_seconds = 0.0

        try:
            if language == "en":
                provider_start = perf_counter()
                provider_result = self.whisper_service.transcribe_file(
                    path,
                    language="en",
                    interrupted=interrupted,
                )
                provider_seconds = perf_counter() - provider_start

                mapping_start = perf_counter()
                raw_text = str(
                    provider_result.get("original_text") or ""
                ).strip()
                duration = provider_result.get("duration_seconds")
                segments = _map_whisper_segments(
                    provider_result.get("segments") or [],
                    duration,
                )
                mapping_seconds = perf_counter() - mapping_start

                result = {
                    "original_text": raw_text,
                    "language": "en",
                    "provider": "local_whisper",
                    "model": provider_result.get("model", "base"),
                    "device": provider_result.get("device", "cpu"),
                    "status": (
                        "silence_or_no_speech" if not raw_text
                        else "partial" if interrupted
                        else "transcribed"
                    ),
                    "is_partial": bool(interrupted and raw_text),
                    "interruption_reported": interrupted,
                    "duration_seconds": duration,
                    "segments": segments,
                    "decoding_method": None,
                    "router_model": "whisper",
                }

            else:
                provider_start = perf_counter()
                provider_result = transcribe_audio(
                    str(path),
                    language=language,
                    decoding_method=self.indic_decoding_method,
                )
                provider_seconds = perf_counter() - provider_start

                mapping_start = perf_counter()
                raw_text = str(
                    provider_result.get("transcript") or ""
                ).strip()
                duration = provider_result.get("audio_duration_seconds")

                result = {
                    "original_text": raw_text,
                    "language": language,
                    "provider": "indic_conformer",
                    "model": provider_result.get(
                        "model_name",
                        "ai4bharat/indic-conformer-600m-multilingual",
                    ),
                    "device": provider_result.get("device", "cpu"),
                    "status": (
                        "silence_or_no_speech" if not raw_text
                        else "partial" if interrupted
                        else "transcribed"
                    ),
                    "is_partial": bool(interrupted and raw_text),
                    "interruption_reported": interrupted,
                    "duration_seconds": duration,
                    "segments": [],
                    "decoding_method": self.indic_decoding_method,
                    "router_model": "indic_conformer",
                }
                mapping_seconds = perf_counter() - mapping_start

            total_seconds = perf_counter() - total_start

            logger.info(
                "Speech-to-text timing | language=%s | provider=%s "
                "| provider_seconds=%.3f | mapping_seconds=%.3f "
                "| total_seconds=%.3f | audio_duration=%s",
                language,
                result["provider"],
                provider_seconds,
                mapping_seconds,
                total_seconds,
                result["duration_seconds"],
            )

            return result

        except Exception as exc:
            if isinstance(exc, (ValueError, FileNotFoundError)):
                raise

            logger.exception(
                "Speech-to-text failed | language=%s | path=%s",
                language,
                path,
            )
            raise HybridSpeechToTextError(
                f"Transcription failed for language '{language}'."
            ) from exc
