
from pathlib import Path
from unittest.mock import Mock

import pytest

from api.service.speech_to_text_service import (
    AudioValidationError,
    SpeechToTextService,
    UnsupportedLanguageError,
)


def make_service(result=None):
    model = Mock()
    model.transcribe.return_value = result or {
        "text": "I am a Python developer.",
        "segments": [
            {
                "text": " I am a Python developer. ",
                "start": 0.0,
                "end": 3.5,
                "avg_logprob": -0.1,
            }
        ],
    }

    return SpeechToTextService(
        model=model,
        device="cpu",
    )


def test_transcribes_audio_file(tmp_path: Path):
    audio_path = tmp_path / "answer.wav"
    audio_path.write_bytes(b"fake audio for mocked provider")

    service = make_service()

    result = service.transcribe_file(audio_path, "en")

    assert result["original_text"] == "I am a Python developer."
    assert result["status"] == "transcribed"
    assert result["language"] == "en"
    assert result["provider"] == "local_whisper"
    assert result["segments"][0]["start"] == 0.0
    assert result["duration_seconds"] == 3.5


def test_rejects_unsupported_language(tmp_path: Path):
    audio_path = tmp_path / "answer.wav"
    audio_path.write_bytes(b"fake audio")

    service = make_service()

    with pytest.raises(UnsupportedLanguageError):
        service.transcribe_file(audio_path, "fr")


def test_rejects_empty_file(tmp_path: Path):
    audio_path = tmp_path / "empty.wav"
    audio_path.write_bytes(b"")

    service = make_service()

    with pytest.raises(AudioValidationError):
        service.transcribe_file(audio_path, "en")


def test_flags_interrupted_answer(tmp_path: Path):
    audio_path = tmp_path / "answer.wav"
    audio_path.write_bytes(b"fake audio")

    service = make_service({
        "text": "I started learning Python because",
        "segments": [
            {
                "text": "I started learning Python because",
                "start": 0.0,
                "end": 2.0,
                "avg_logprob": -0.2,
            }
        ],
    })

    result = service.transcribe_file(
        audio_path,
        "en",
        interrupted=True,
    )

    assert result["status"] == "partial"
    assert result["is_partial"] is True
    assert result["original_text"] == (
        "I started learning Python because"
    )


def test_interrupted_answer_preserves_all_recognized_segments(tmp_path: Path):
    audio_path = tmp_path / "interrupted.wav"
    audio_path.write_bytes(b"fake audio")

    service = make_service({
        "text": "I learned Python and",
        "segments": [
            {
                "text": "I learned Python",
                "start": 0.0,
                "end": 1.5,
                "avg_logprob": -0.1,
            },
            {
                "text": "and",
                "start": 1.5,
                "end": 2.0,
                "avg_logprob": -0.2,
            },
        ],
    })

    result = service.transcribe_file(
        audio_path,
        "en",
        interrupted=True,
    )

    assert result["status"] == "partial"
    assert result["is_partial"] is True
    assert result["interruption_reported"] is True
    assert result["original_text"] == "I learned Python and"
    assert len(result["segments"]) == 2
    assert result["segments"][1]["text"] == "and"


def test_interrupted_recording_with_no_recognized_text(tmp_path: Path):
    audio_path = tmp_path / "interrupted_silence.wav"
    audio_path.write_bytes(b"fake audio")

    service = make_service({
        "text": "",
        "segments": [],
    })

    result = service.transcribe_file(
        audio_path,
        "en",
        interrupted=True,
    )

    assert result["status"] == "silence_or_no_speech"
    assert result["original_text"] == ""
    assert result["is_partial"] is False
    assert result["interruption_reported"] is True
    assert result["segments"] == []


def test_completed_recording_with_no_recognized_text(tmp_path: Path):
    audio_path = tmp_path / "silence.wav"
    audio_path.write_bytes(b"fake audio")

    service = make_service({
        "text": "",
        "segments": [],
    })

    result = service.transcribe_file(audio_path, "en")

    assert result["status"] == "silence_or_no_speech"
    assert result["original_text"] == ""
    assert result["is_partial"] is False
    assert result["interruption_reported"] is False
