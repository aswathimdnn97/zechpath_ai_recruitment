import pytest

from api.service.partial_answer_detection_service import (
    PartialAnswerDetectionService,
)


@pytest.fixture
def detector():
    return PartialAnswerDetectionService()


@pytest.mark.parametrize(
    "text,language",
    [
        ("I started learning Python because", "en"),
        ("I started learning Python because...", "en"),
        ("The reason is", "en"),
        ("നിങ്ങൾ കാരണം", "ml"),
        ("क्योंकि", "hi"),
    ],
)
def test_detects_partial_answers(detector, text, language):
    result = detector.detect(text, language)

    assert result.is_partial is True
    assert result.reason in {
        "unfinished_punctuation",
        "trailing_incomplete_phrase",
    }


@pytest.mark.parametrize(
    "text,language",
    [
        ("I am a Python developer.", "en"),
        ("I use Python and FastAPI.", "en"),
        ("Python.", "en"),
        ("നമസ്കാരം.", "ml"),
        ("मैं Python सीखता हूँ।", "hi"),
        ("", "en"),
        ("   ", "en"),
    ],
)
def test_does_not_flag_normal_or_empty_text(detector, text, language):
    result = detector.detect(text, language)

    assert result.is_partial is False
    assert result.reason is None


def test_preserves_original_text(detector):
    text = "  I started learning Python because...  "

    detector.detect(text, "en")

    assert text == "  I started learning Python because...  "


def test_rejects_unsupported_language(detector):
    with pytest.raises(ValueError, match="Unsupported language"):
        detector.detect("Bonjour", "fr")


def test_rejects_non_string_input(detector):
    with pytest.raises(TypeError, match="text must be a string"):
        detector.detect(None, "en")