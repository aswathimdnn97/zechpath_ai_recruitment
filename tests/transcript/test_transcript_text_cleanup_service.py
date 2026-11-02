
import copy

import pytest

from api.service.transcript_text_cleanup_service import (
    CLEANUP_VERSION,
    TranscriptTextCleanupError,
    cleanup_transcript_payload,
    cleanup_transcript_text,
)


def test_remove_english_filler_words():
    result = cleanup_transcript_text(
        "um, I use Python, uh, and FastAPI",
        "en",
    )

    assert result.cleaned_text == "I use Python, and FastAPI."
    assert len(result.removed_fillers) == 2


def test_remove_english_filler_phrase():
    result = cleanup_transcript_text(
        "I mean, I use Python",
        "en",
    )

    assert result.cleaned_text == "I use Python."


def test_normalize_punctuation_spacing():
    result = cleanup_transcript_text(
        "Hello   ,world   !",
        "en",
    )

    assert result.cleaned_text == "Hello, world!"


def test_normalize_repeated_punctuation():
    result = cleanup_transcript_text(
        "I know Python!!!",
        "en",
    )

    assert result.cleaned_text == "I know Python!"


def test_add_terminal_punctuation():
    result = cleanup_transcript_text(
        "I know Python",
        "en",
    )

    assert result.cleaned_text.endswith(".")


def test_normalize_english_sentence_case():
    result = cleanup_transcript_text(
        "HELLO WORLD",
        "en",
    )

    assert result.cleaned_text == "Hello world."


def test_preserve_technical_terms():
    result = cleanup_transcript_text(
        "I use Python and FastAPI",
        "en",
    )

    assert "Python" in result.cleaned_text
    assert "FastAPI" in result.cleaned_text


@pytest.mark.parametrize(
    ("language", "text", "expected"),
    [
        (
            "ml",
            "ഞാൻ Python ഉപയോഗിക്കുന്നു",
            "ഞാൻ Python ഉപയോഗിക്കുന്നു.",
        ),
        (
            "hi",
            "मैं Python जानता हूँ",
            "मैं Python जानता हूँ।",
        ),
    ],
)
def test_indic_language_punctuation(language, text, expected):
    result = cleanup_transcript_text(text, language)

    assert result.cleaned_text == expected


def test_preserve_negation():
    result = cleanup_transcript_text(
        "I do not know Django",
        "en",
    )

    assert "not" in result.cleaned_text
    assert "Django" in result.cleaned_text


def test_preserve_numbers():
    result = cleanup_transcript_text(
        "I have 2.5 years of experience",
        "en",
    )

    assert "2.5" in result.cleaned_text


def test_original_transcript_is_preserved():
    original = "um, I use Python"

    result = cleanup_transcript_text(original, "en")

    assert result.original_text == original
    assert result.cleaned_text != original


def test_cleanup_returns_metadata():
    result = cleanup_transcript_text(
        "um, I use Python",
        "en",
    )

    assert result.cleanup_version == CLEANUP_VERSION
    assert result.changed is True
    assert result.removed_fillers
    assert isinstance(result.punctuation_changed, bool)
    assert isinstance(result.case_changed, bool)


def test_payload_cleanup_uses_normalized_text():
    payload = {
        "original_text": "um,  I use Python",
        "normalized_text": "um, I use Python",
        "language": "en",
    }

    result = cleanup_transcript_payload(payload)

    assert result["cleaned_text"] == "I use Python."
    assert result["original_text"] == "um,  I use Python"
    assert result["normalized_text"] == "um, I use Python"


def test_payload_cleanup_does_not_mutate_input():
    payload = {
        "original_text": "um, I use Python",
        "language": "en",
    }
    original_payload = copy.deepcopy(payload)

    cleanup_transcript_payload(payload)

    assert payload == original_payload
    assert "cleaned_text" not in payload


@pytest.mark.parametrize(
    "text",
    ["", "   ", None],
)
def test_reject_invalid_text(text):
    with pytest.raises(TranscriptTextCleanupError):
        cleanup_transcript_text(text, "en")


def test_reject_unsupported_language():
    with pytest.raises(TranscriptTextCleanupError):
        cleanup_transcript_text("Hello", "fr")


def test_reject_invalid_payload():
    with pytest.raises(TranscriptTextCleanupError):
        cleanup_transcript_payload([])


def test_payload_requires_language():
    with pytest.raises(TranscriptTextCleanupError):
        cleanup_transcript_payload({
            "original_text": "Hello",
        })


def test_payload_rejects_invalid_cleanup_metadata():
    with pytest.raises(TranscriptTextCleanupError):
        cleanup_transcript_payload({
            "original_text": "Hello",
            "language": "en",
            "cleanup": "invalid",
        })


from api.service.transcript_text_cleanup_service import (
    cleanup_transcript_text,
)


def test_english_cleanup_preserves_names_pronoun_and_technical_terms():
    text = (
        "Hello my name is Anu, I am learning Python SQL and Fast API. "
        "I want to become a Python developer."
    )

    result = cleanup_transcript_text(text, "en")

    assert result.cleaned_text == (
        "Hello my name is Anu, I am learning Python SQL and Fast API. "
        "I want to become a Python developer."
    )

    assert result.case_changed is False
    assert result.punctuation_changed is False
    assert result.changed is False
    assert result.removed_fillers == ()
