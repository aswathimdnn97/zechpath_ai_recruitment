
import pytest

from api.service.transcript_skill_extraction_service import (
    extract_transcript_skills,
    TranscriptSkillExtractionError,
)


def test_extracts_known_skill_and_preserves_transcript():
    original = "I have experience with Python."
    normalized = "I have experience with Python."

    result = extract_transcript_skills({
        "original_text": original,
        "normalized_text": normalized,
        "language": "en",
    })

    assert result["original_text"] == original
    assert result["normalized_text"] == normalized
    assert result["language"] == "en"
    assert any(
        skill["skill"].casefold() == "python"
        for skill in result["recognized_skills"]
    )


def test_empty_normalized_transcript_returns_no_skills():
    result = extract_transcript_skills({
        "original_text": "",
        "normalized_text": "",
        "language": "en",
    })

    assert result["recognized_skills"] == []
    assert result["skill_count"] == 0


def test_unsupported_language_is_rejected():
    with pytest.raises(TranscriptSkillExtractionError):
        extract_transcript_skills({
            "original_text": "I use Python.",
            "normalized_text": "I use Python.",
            "language": "fr",
        })


def test_invalid_payload_is_rejected():
    with pytest.raises(TranscriptSkillExtractionError):
        extract_transcript_skills("I use Python.")


