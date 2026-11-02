"""
speech_to_text_service.py

Responsibilities
----------------
1. Transcribe audio using a locally installed Whisper model.
2. Support English, Malayalam, and Hindi.
3. Return raw transcript text and segment metadata.
4. Identify empty/no-speech results.
5. Report interrupted recordings as partial.
6. Avoid external API calls and API keys.

Integration
-----------
Audio -> SpeechToTextService -> Transcript Normalization
      -> Transcript Service -> HR Screening Pipeline
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
from time import perf_counter

from api.service.partial_answer_detection_service import (
    PartialAnswerDetectionService,
)
from api.service.audio_silence_detection_service import (
    AudioSilenceDetectionService,
)

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {"en", "ml", "hi"}

# "base" is multilingual and suitable for initial development.
# Larger models may improve accuracy but require more resources.
DEFAULT_MODEL = "base"

MAX_AUDIO_BYTES = 100 * 1024 * 1024  # 100 MB


class SpeechToTextError(RuntimeError):
    """Base exception for speech-to-text errors."""


class AudioValidationError(SpeechToTextError, ValueError):
    """Raised when audio input is invalid."""


class UnsupportedLanguageError(SpeechToTextError, ValueError):
    """Raised when the requested language is unsupported."""


@lru_cache(maxsize=2)
def _load_model(model_name: str, device: str) -> Any:
    """
    Load and cache a Whisper model.

    Reusing the model avoids reloading it for every recording.
    """
    try:
        import whisper
    except ImportError as exc:
        raise SpeechToTextError(
            "Local Whisper is not installed. Run: "
            "python -m pip install -U openai-whisper"
        ) from exc

    try:
        logger.info(
            "Loading local Whisper model '%s' on '%s'.",
            model_name,
            device,
        )
        return whisper.load_model(model_name, device=device)

    except Exception as exc:
        logger.exception("Failed to load local Whisper model.")
        raise SpeechToTextError(
            f"Could not load Whisper model '{model_name}'."
        ) from exc


class SpeechToTextService:
    """Local speech recognition service for HR screening."""

    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str | None = None,
        *,
        model: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device or self._select_device()
        self._model = model
        self.partial_answer_detector = PartialAnswerDetectionService()
        self.silence_detector = AudioSilenceDetectionService()


    @staticmethod
    def _select_device() -> str:
        """Use CUDA when available; otherwise use CPU."""
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"

        except ImportError:
            logger.warning(
                "PyTorch CUDA detection unavailable; using CPU."
            )

        return "cpu"

    @staticmethod
    def _validate_language(language: str) -> str:
        if not isinstance(language, str) or not language.strip():
            raise UnsupportedLanguageError(
                "A supported language code is required."
            )

        language = language.strip().lower()

        if language not in SUPPORTED_LANGUAGES:
            raise UnsupportedLanguageError(
                f"Unsupported language: {language}. "
                f"Supported languages: {sorted(SUPPORTED_LANGUAGES)}"
            )

        return language

    @staticmethod
    def _validate_audio(audio_path: str | Path) -> Path:
        path = Path(audio_path)

        if not path.is_file():
            raise AudioValidationError(
                f"Audio file does not exist: {path}"
            )

        size = path.stat().st_size

        if size == 0:
            raise AudioValidationError("Audio file is empty.")

        if size > MAX_AUDIO_BYTES:
            raise AudioValidationError(
                "Audio file exceeds the 100 MB size limit."
            )

        return path

    
    def transcribe_file(
        self,
        audio_path: str | Path,
        language: str,
        *,
        interrupted: bool = False,
    ) -> dict[str, Any]:
        """
        Transcribe audio locally and report silence, partial answers,
        interruption metadata, and performance timings.

        Silence analysis is diagnostic only. Whisper still processes
        the audio so quiet speech is not discarded by a volume threshold.
        """
        total_start = perf_counter()

        language = self._validate_language(language)
        path = self._validate_audio(audio_path)

        # Measure diagnostic silence analysis.
        silence_start = perf_counter()
        silence_result = self.silence_detector.is_silent(path)
        silence_seconds = perf_counter() - silence_start

        logger.info(
            "STT timing | stage=silence_analysis | seconds=%.3f | file=%s",
            silence_seconds,
            path.name,
        )

        # Measure model lookup. A cache hit should normally be fast.
        model_start = perf_counter()

        if self._model is not None:
            model = self._model
            model_source = "injected"
        else:
            model = _load_model(self.model_name, self.device)
            model_source = "cached_loader"

        model_seconds = perf_counter() - model_start

        logger.info(
            "STT timing | stage=model_lookup | source=%s | seconds=%.3f",
            model_source,
            model_seconds,
        )

        # Measure Whisper transcription.
        inference_start = perf_counter()

        try:
            result = model.transcribe(
                str(path),
                language=language,
                task="transcribe",
                verbose=False,
                fp16=(self.device == "cuda"),
            )
        except Exception as exc:
            logger.exception(
                "Local Whisper transcription failed for %s.",
                path.name,
            )
            raise SpeechToTextError(
                "Local transcription failed. Check the audio format, "
                "FFmpeg installation, and available system resources."
            ) from exc

        inference_seconds = perf_counter() - inference_start

        logger.info(
            "STT timing | stage=whisper_transcribe | seconds=%.3f "
            "| model=%s | device=%s",
            inference_seconds,
            self.model_name,
            self.device,
        )

        if not isinstance(result, dict):
            raise SpeechToTextError(
                "Whisper returned an invalid transcription result."
            )

        raw_text = result.get("text") or ""

        if not isinstance(raw_text, str):
            raise SpeechToTextError(
                "Whisper returned an invalid transcript."
            )

        raw_text = raw_text.strip()
        raw_segments = result.get("segments") or []

        if not isinstance(raw_segments, list):
            raise SpeechToTextError(
                "Whisper returned invalid segment metadata."
            )

        segments = []

        for segment in raw_segments:
            if not isinstance(segment, dict):
                raise SpeechToTextError(
                    "Whisper returned an invalid audio segment."
                )

            segments.append(
                {
                    "text": str(segment.get("text") or "").strip(),
                    "start": segment.get("start"),
                    "end": segment.get("end"),
                    "avg_logprob": segment.get("avg_logprob"),
                }
            )

        # Determine status without modifying the recognized transcript.
        if not raw_text:
            status = "silence_or_no_speech"
            is_partial = False
        else:
            detection = self.partial_answer_detector.detect(
                raw_text,
                language,
            )

            is_partial = bool(
                interrupted or detection.is_partial
            )

            status = "partial" if is_partial else "transcribed"

        total_seconds = perf_counter() - total_start

        logger.info(
            "STT timing | stage=total | seconds=%.3f "
            "| language=%s | file=%s | silence=%s",
            total_seconds,
            language,
            path.name,
            silence_result,
        )

        return {
            "original_text": raw_text,
            "language": language,
            "provider": "local_whisper",
            "model": self.model_name,
            "device": self.device,
            "status": status,
            "is_partial": is_partial,
            "interruption_reported": bool(interrupted),
            "duration_seconds": (
                segments[-1]["end"] if segments else None
            ),
            "segments": segments,
        }
