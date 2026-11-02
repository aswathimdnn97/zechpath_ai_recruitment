
from unittest.mock import Mock

import pytest

from api.service import hybrid_speech_to_text_service as hybrid


def test_whisper_segments_are_converted_to_milliseconds():
    result = hybrid._map_whisper_segments(
        [
            {"start": 0.5, "end": 1.25, "text": " Hello "},
            {"start": 1.25, "end": 2.0, "text": "world"},
        ],
        duration_seconds=2.0,
    )

    assert result == [
        {
            "start_ms": 500,
            "end_ms": 1250,
            "text": "Hello",
            "confidence": None,
        },
        {
            "start_ms": 1250,
            "end_ms": 2000,
            "text": "world",
            "confidence": None,
        },
    ]


def test_invalid_whisper_segments_are_skipped():
    result = hybrid._map_whisper_segments(
        [
            {"start": 2.0, "end": 1.0, "text": "invalid"},
            {"start": 0.0, "end": 0.5, "text": ""},
            {"start": 0.5, "end": 1.0, "text": "valid"},
            {"start": 0.8, "end": 1.2, "text": "overlapping"},
        ],
        duration_seconds=2.0,
    )

    assert len(result) == 1
    assert result[0]["text"] == "valid"


def test_english_route_returns_schema_compatible_segments(
    monkeypatch, tmp_path
):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"test")

    service = hybrid.HybridSpeechToTextService()
    service.whisper_service = Mock()
    service.whisper_service.transcribe_file.return_value = {
        "original_text": "Hello world",
        "model": "base",
        "device": "cpu",
        "status": "transcribed",
        "duration_seconds": 2.0,
        "segments": [
            {"start": 0.0, "end": 1.0, "text": "Hello world"}
        ],
    }

    result = service.transcribe_file(audio, "en")

    assert result["status"] == "transcribed"
    assert result["segments"][0]["start_ms"] == 0
    assert result["segments"][0]["end_ms"] == 1000
    assert result["segments"][0]["text"] == "Hello world"
    assert result["segments"][0]["confidence"] is None


def test_indic_route_does_not_invent_segments(monkeypatch, tmp_path):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"test")

    monkeypatch.setattr(
        hybrid,
        "transcribe_audio",
        lambda *args, **kwargs: {
            "transcript": "മലയാളം വാചകം",
            "model_name": "test-model",
            "audio_duration_seconds": 2.0,
        },
    )

    service = hybrid.HybridSpeechToTextService()
    result = service.transcribe_file(audio, "ml")

    assert result["original_text"] == "മലയാളം വാചകം"
    assert result["segments"] == []
    assert result["status"] == "transcribed"


def test_empty_indic_result_is_classified_as_no_speech(
    monkeypatch, tmp_path
):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"test")

    monkeypatch.setattr(
        hybrid,
        "transcribe_audio",
        lambda *args, **kwargs: {
            "transcript": "",
            "audio_duration_seconds": 2.0,
        },
    )

    service = hybrid.HybridSpeechToTextService()
    result = service.transcribe_file(audio, "ml")

    assert result["status"] == "silence_or_no_speech"
    assert result["is_partial"] is False


def test_reported_interruption_marks_nonempty_result_partial(
    monkeypatch, tmp_path
):
    audio = tmp_path / "sample.wav"
    audio.write_bytes(b"test")

    monkeypatch.setattr(
        hybrid,
        "transcribe_audio",
        lambda *args, **kwargs: {
            "transcript": "partial answer",
            "audio_duration_seconds": 2.0,
        },
    )

    service = hybrid.HybridSpeechToTextService()
    result = service.transcribe_file(
        audio, "ml", interrupted=True
    )

    assert result["status"] == "partial"
    assert result["is_partial"] is True
    assert result["interruption_reported"] is True
