from unittest.mock import Mock, patch

from api.service.audio_silence_detection_service import (
    AudioSilenceDetectionService,
)


def test_detects_digital_silence():
    result = Mock(returncode=0, stderr="max_volume: -inf dB")

    with patch(
        "api.service.audio_silence_detection_service.subprocess.run",
        return_value=result,
    ):
        detector = AudioSilenceDetectionService()
        assert detector.is_silent("silent.wav") is True


def test_detects_near_silent_audio():
    result = Mock(returncode=0, stderr="max_volume: -60.0 dB")

    with patch(
        "api.service.audio_silence_detection_service.subprocess.run",
        return_value=result,
    ):
        detector = AudioSilenceDetectionService()
        assert detector.is_silent("quiet.wav") is True


def test_does_not_flag_audible_audio_as_silent():
    result = Mock(returncode=0, stderr="max_volume: -20.0 dB")

    with patch(
        "api.service.audio_silence_detection_service.subprocess.run",
        return_value=result,
    ):
        detector = AudioSilenceDetectionService()
        assert detector.is_silent("speech.wav") is False


def test_analysis_failure_falls_back_safely():
    with patch(
        "api.service.audio_silence_detection_service.subprocess.run",
        side_effect=FileNotFoundError,
    ):
        detector = AudioSilenceDetectionService()
        assert detector.is_silent("speech.wav") is None