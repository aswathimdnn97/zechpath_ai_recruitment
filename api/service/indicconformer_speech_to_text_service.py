
"""
indicconformer_speech_to_text_service.py

Responsibilities
----------------
1. Load the IndicConformer model lazily.
2. Load audio and convert it to mono, 16 kHz.
3. Transcribe audio using CTC or RNNT decoding.
4. Return transcript text and processing metadata.
5. Report audio, model-loading, and transcription errors clearly.

This service does not normalize or persist transcripts.
"""

from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any, Literal
import logging
from time import perf_counter

import torch
import torchaudio
from transformers import AutoModel


MODEL_NAME = "ai4bharat/indic-conformer-600m-multilingual"
TARGET_SAMPLE_RATE = 16000

SupportedLanguage = Literal["en", "ml", "hi"]
DecodingMethod = Literal["ctc", "rnnt"]

_SUPPORTED_LANGUAGES = {"en", "ml", "hi"}
_SUPPORTED_DECODERS = {"ctc", "rnnt"}

_model: Any = None
_model_lock = Lock()

logger = logging.getLogger(__name__)

class IndicConformerError(RuntimeError):
    """Raised when IndicConformer loading or transcription fails."""


def _load_model() -> Any:
    """Load the model once and reuse it for subsequent requests."""
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        # Another request may have loaded the model while we waited.
        if _model is None:
            try:
                loaded_model = AutoModel.from_pretrained(
                    MODEL_NAME,
                    trust_remote_code=True,
                )
                loaded_model.eval()
                _model = loaded_model

            except Exception as exc:
                raise IndicConformerError(
                    "Failed to load IndicConformer. Check model access, "
                    "authentication, dependencies, and available memory."
                ) from exc

    return _model


def _load_audio(audio_path: Path) -> torch.Tensor:
    """Load audio, convert it to mono, and resample to 16 kHz."""

    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file does not exist: {audio_path}"
        )

    if not audio_path.is_file():
        raise ValueError(
            f"Audio path is not a file: {audio_path}"
        )

    try:
        waveform, sample_rate = torchaudio.load(str(audio_path))

        if waveform.numel() == 0:
            raise ValueError("The audio file contains no audio samples.")

        if waveform.ndim != 2 or waveform.shape[0] < 1:
            raise ValueError("The audio has an invalid channel layout.")

        # Combine stereo or multichannel audio into mono.
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # IndicConformer expects 16 kHz audio.
        if sample_rate != TARGET_SAMPLE_RATE:
            resampler = torchaudio.transforms.Resample(
                orig_freq=sample_rate,
                new_freq=TARGET_SAMPLE_RATE,
            )
            waveform = resampler(waveform)

        if waveform.numel() == 0:
            raise ValueError("No samples remain after audio conversion.")

        return waveform.contiguous()

    except Exception as exc:
        raise IndicConformerError(
            f"Unable to load or convert audio file: {audio_path}. "
            "Check the audio format and TorchAudio/TorchCodec dependencies."
        ) from exc


def transcribe_audio(
    audio_path: str | Path,
    language: SupportedLanguage = "ml",
    decoding_method: DecodingMethod = "rnnt",
) -> dict[str, Any]:
    """
    Transcribe an audio file with IndicConformer.

    Args:
        audio_path: Path to the input audio file.
        language: Supported language code: en, ml, or hi.
        decoding_method: Either ctc or rnnt.

    Returns:
        Dictionary containing transcript and processing metadata.
    """

    language = language.strip().lower()
    decoding_method = decoding_method.strip().lower()

    if language not in _SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language '{language}'. "
            f"Supported languages: {sorted(_SUPPORTED_LANGUAGES)}"
        )

    if decoding_method not in _SUPPORTED_DECODERS:
        raise ValueError(
            f"Unsupported decoding method '{decoding_method}'. "
            "Choose 'ctc' or 'rnnt'."
        )

    path = Path(audio_path).expanduser().resolve()

    # Load audio before model initialization to fail early for bad paths.
    audio_start = perf_counter()
    waveform = _load_audio(path)
    audio_seconds = perf_counter() - audio_start
    audio_duration_seconds = waveform.shape[1] / TARGET_SAMPLE_RATE

    model_start = perf_counter()
    model = _load_model()
    model_seconds = perf_counter() - model_start

    logger.info(
        "IndicConformer timing | stage=audio_load_resample | seconds=%.3f",
        audio_seconds,
    )
    logger.info(
        "IndicConformer timing | stage=model_lookup_or_load | seconds=%.3f",
        model_seconds,
    )

    start_time = perf_counter()

    try:
        with torch.inference_mode():
            transcript = model(
                waveform,
                language,
                decoding_method,
            )

        if isinstance(transcript, (tuple, list)):
            transcript = " ".join(str(part) for part in transcript)

        if not isinstance(transcript, str):
            transcript = str(transcript)

        transcript = transcript.strip()


    except IndicConformerError:
        raise
    except Exception as exc:
        raise IndicConformerError(
            "IndicConformer transcription failed. Check the language, "
            "decoding method, audio, and model dependencies."
        ) from exc

    processing_time_seconds = perf_counter() - start_time
    logger.info(
    "IndicConformer timing | stage=inference | seconds=%.3f "
    "| language=%s | decoder=%s | device=cpu",
    processing_time_seconds,
    language,
    decoding_method,
)

    return {
        "transcript": transcript,
        "language": language,
        "model_name": MODEL_NAME,
        "decoding_method": decoding_method,
        "sample_rate": TARGET_SAMPLE_RATE,
        "audio_duration_seconds": round(audio_duration_seconds, 3),
        "processing_time_seconds": round(processing_time_seconds, 3),
        "status": "SUCCESS",
    }


def transcribe_malayalam(
    audio_path: str | Path,
    decoding_method: DecodingMethod = "rnnt",
) -> dict[str, Any]:
    """Convenience wrapper for Malayalam transcription."""
    return transcribe_audio(
        audio_path=audio_path,
        language="ml",
        decoding_method=decoding_method,
    )
