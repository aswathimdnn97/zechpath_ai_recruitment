
"""
tests/test_transcript_normalization.py

Tests for:
    api/service/transcript_normalization_service.py

Run:
    python -m pytest tests/test_transcript_normalization.py -v
"""

import copy

import pytest

from api.service.transcript_normalization_service import (
    NORMALIZATION_VERSION,
    SUPPORTED_LANGUAGES,
    NormalizedTranscript,
    TranscriptNormalizationError,
    normalize_transcript,
    normalize_transcript_payload,
    normalize_transcript_text,
)


# ---------------------------------------------------------
# 1. Basic normalization
# ---------------------------------------------------------


def test_normalize_repeated_spaces():
    result = normalize_transcript_text(
        "  I know   Python, Django   and FastAPI  "
    )

    assert result == "I know Python, Django and FastAPI"


def test_normalize_tabs_and_spaces():
    result = normalize_transcript_text(
        "Python\t\tDjango     FastAPI"
    )

    assert result == "Python Django FastAPI"


def test_trim_leading_and_trailing_whitespace():
    result = normalize_transcript_text(
        "   Hello candidate!   "
    )

    assert result == "Hello candidate!"


def test_normalize_windows_line_endings():
    result = normalize_transcript_text(
        "First line\r\nSecond line\r\nThird line"
    )

    assert result == "First line\nSecond line\nThird line"


def test_normalize_old_mac_line_endings():
    result = normalize_transcript_text(
        "First line\rSecond line"
    )

    assert result == "First line\nSecond line"


def test_preserve_meaningful_line_breaks():
    result = normalize_transcript_text(
        "  Python   developer  \n"
        "  Three years   experience  \n"
        "FastAPI"
    )

    assert result == (
        "Python developer\n"
        "Three years experience\n"
        "FastAPI"
    )


def test_remove_empty_lines_at_boundaries():
    result = normalize_transcript_text(
        "\n\nPython developer\nFastAPI\n\n"
    )

    assert result == "Python developer\nFastAPI"


def test_empty_lines_inside_text_are_preserved():
    result = normalize_transcript_text(
        "Introduction\n\nExperience"
    )

    assert result == "Introduction\n\nExperience"


# ---------------------------------------------------------
# 2. Unicode normalization
# ---------------------------------------------------------


def test_unicode_is_normalized_to_nfc():
    # "é" represented as e + combining acute accent.
    original = "Cafe\u0301 developer"
    result = normalize_transcript_text(original)

    assert result == "Café developer"


def test_unicode_normalization_does_not_change_original():
    original = "Cafe\u0301 developer"

    result = normalize_transcript(
        text=original,
        language="en",
    )

    assert result.original_text == original
    assert result.normalized_text == "Café developer"


# ---------------------------------------------------------
# 3. Preserve technical content and meaning
# ---------------------------------------------------------


def test_preserve_technical_terms():
    original = (
        "I use Python, Django, FastAPI, ReactJS, "
        "PostgreSQL, MySQL and REST API."
    )

    result = normalize_transcript_text(original)

    assert result == original
    assert "FastAPI" in result
    assert "ReactJS" in result
    assert "PostgreSQL" in result
    assert "REST API" in result


def test_preserve_numbers_and_experience():
    original = "I have 2.5 years of Python experience."

    result = normalize_transcript_text(original)

    assert result == original
    assert "2.5" in result


def test_preserve_negation():
    original = "I do not have experience with Django."

    result = normalize_transcript_text(original)

    assert result == original
    assert "not" in result


def test_preserve_punctuation_and_capitalization():
    original = "Python? YES! I use FastAPI, not Flask."

    result = normalize_transcript_text(original)

    assert result == original


def test_normalization_does_not_correct_spelling():
    original = "I know Pythn and Djagno."

    result = normalize_transcript_text(original)

    assert result == original


# ---------------------------------------------------------
# 4. Multilingual support
# ---------------------------------------------------------


@pytest.mark.parametrize(
    ("language", "text"),
    [
        ("en", "I am a Python developer."),
        ("ml", "ഞാൻ ഒരു Python ഡെവലപ്പറാണ്."),
        ("hi", "मैं एक Python डेवलपर हूँ।"),
    ],
)
def test_supported_languages(language, text):
    result = normalize_transcript(
        text=f"  {text}   ",
        language=language,
    )

    assert isinstance(result, NormalizedTranscript)
    assert result.language == language
    assert result.normalized_text == text
    assert result.language_preserved is True


def test_supported_language_set():
    assert SUPPORTED_LANGUAGES == {"en", "ml", "hi"}


def test_malayalam_text_is_not_translated():
    original = "എനിക്ക് Python അറിയാം."

    result = normalize_transcript(
        text=original,
        language="ml",
    )

    assert result.original_text == original
    assert result.normalized_text == original
    assert result.language == "ml"


def test_hindi_text_is_not_translated():
    original = "मुझे Python आता है।"

    result = normalize_transcript(
        text=original,
        language="hi",
    )

    assert result.original_text == original
    assert result.normalized_text == original
    assert result.language == "hi"


# ---------------------------------------------------------
# 5. Normalization metadata
# ---------------------------------------------------------


def test_normalize_returns_expected_metadata():
    result = normalize_transcript(
        text="  Python developer  ",
        language="en",
    )

    assert result.original_text == "  Python developer  "
    assert result.normalized_text == "Python developer"
    assert result.language == "en"
    assert result.normalization_version == NORMALIZATION_VERSION
    assert result.language_preserved is True
    assert result.changed is True


def test_changed_is_false_when_text_is_already_normalized():
    result = normalize_transcript(
        text="Python developer",
        language="en",
    )

    assert result.changed is False


def test_original_text_is_not_modified():
    original = "  Python   developer  "

    result = normalize_transcript(
        text=original,
        language="en",
    )

    assert result.original_text == original


# ---------------------------------------------------------
# 6. Invalid text
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "\t",
        "\n\n",
    ],
)
def test_reject_empty_or_whitespace_text(text):
    with pytest.raises(
        TranscriptNormalizationError,
        match="cannot be empty",
    ):
        normalize_transcript_text(text)


def test_reject_non_string_text():
    with pytest.raises(
        TranscriptNormalizationError,
        match="must be a string",
    ):
        normalize_transcript_text(None)  # type: ignore[arg-type]


def test_reject_text_exceeding_maximum_length():
    text = "a" * 50_001

    with pytest.raises(
        TranscriptNormalizationError,
        match="maximum length",
    ):
        normalize_transcript_text(text)


def test_accept_text_at_maximum_length():
    text = "a" * 50_000

    result = normalize_transcript_text(text)

    assert len(result) == 50_000


def test_reject_nul_character():
    with pytest.raises(
        TranscriptNormalizationError,
        match="NUL character",
    ):
        normalize_transcript_text("Python\x00developer")


# ---------------------------------------------------------
# 7. Invalid language
# ---------------------------------------------------------


@pytest.mark.parametrize(
    "language",
    [
        "fr",
        "ta",
        "EN",
        "en-IN",
        "",
    ],
)
def test_reject_unsupported_language(language):
    with pytest.raises(
        TranscriptNormalizationError,
        match="Unsupported language",
    ):
        normalize_transcript(
            text="Python developer",
            language=language,  # type: ignore[arg-type]
        )


def test_reject_non_string_language():
    with pytest.raises(
        TranscriptNormalizationError,
        match="Language must be a string",
    ):
        normalize_transcript(
            text="Python developer",
            language=None,  # type: ignore[arg-type]
        )


# ---------------------------------------------------------
# 8. Normalize transcript payload
# ---------------------------------------------------------


def test_payload_normalization_adds_normalized_text():
    payload = {
        "original_text": "  Python   developer  ",
        "language": "en",
    }

    result = normalize_transcript_payload(payload)

    assert result["original_text"] == "  Python   developer  "
    assert result["normalized_text"] == "Python developer"
    assert result["normalization"]["version"] == NORMALIZATION_VERSION
    assert result["normalization"]["language_preserved"] is True


def test_payload_normalization_preserves_existing_metadata():
    payload = {
        "original_text": "  Python developer  ",
        "language": "en",
        "normalization": {
            "pii_redacted": True,
            "custom_metadata": "preserve-me",
        },
        "transcription": {
            "provider": "test-provider",
        },
    }

    result = normalize_transcript_payload(payload)

    assert result["normalization"]["pii_redacted"] is True
    assert (
        result["normalization"]["custom_metadata"]
        == "preserve-me"
    )
    assert result["transcription"]["provider"] == "test-provider"


def test_payload_normalization_does_not_mutate_input():
    payload = {
        "original_text": "  Python   developer  ",
        "language": "en",
        "normalization": {
            "pii_redacted": False,
        },
    }
    original_payload = copy.deepcopy(payload)

    normalize_transcript_payload(payload)

    assert payload == original_payload
    assert "normalized_text" not in payload


def test_payload_normalization_does_not_mutate_nested_metadata():
    payload = {
        "original_text": "  Python developer  ",
        "language": "en",
        "normalization": {
            "pii_redacted": False,
        },
    }

    result = normalize_transcript_payload(payload)

    assert result["normalization"] is not payload["normalization"]
    assert payload["normalization"] == {"pii_redacted": False}


def test_payload_rejects_non_dictionary():
    with pytest.raises(
        TranscriptNormalizationError,
        match="must be a dictionary",
    ):
        normalize_transcript_payload([])  # type: ignore[arg-type]


def test_payload_requires_original_text():
    with pytest.raises(
        TranscriptNormalizationError,
        match="original_text",
    ):
        normalize_transcript_payload({
            "language": "en",
        })


def test_payload_requires_language():
    with pytest.raises(
        TranscriptNormalizationError,
        match="language",
    ):
        normalize_transcript_payload({
            "original_text": "Python developer",
        })


def test_payload_rejects_invalid_normalization_metadata():
    with pytest.raises(
        TranscriptNormalizationError,
        match="Normalization metadata must be a dictionary",
    ):
        normalize_transcript_payload({
            "original_text": "Python developer",
            "language": "en",
            "normalization": "invalid",
        })


def test_payload_rejects_unsupported_language():
    with pytest.raises(TranscriptNormalizationError):
        normalize_transcript_payload({
            "original_text": "Python developer",
            "language": "fr",
        })

def test_normalize_transcript_payload():
    payload = {
        "session_id": "SCREEN_0B4F4DA9183D",
        "candidate_id": "CAN_C0CC88823474",
        "job_id": "JOB_BF2FEFE4A4A3",
        "question_id": "PYF_EXP_001",
        "language": "en",
        "original_text": "  I know   Python and Django  ",
        "transcription": {
            "provider": "test-provider",
            "confidence": 0.95,
        },
    }

    result = normalize_transcript_payload(payload)

    assert result["normalized_text"] == (
        "I know Python and Django"
    )
    assert result["original_text"] == (
        "  I know   Python and Django  "
    )
    assert payload["original_text"] == (
        "  I know   Python and Django  "
    )