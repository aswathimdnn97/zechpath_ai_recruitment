
"""
transcript_normalization_service.py

Responsibilities
----------------
1. Normalize speech-to-text output deterministically.
2. Preserve the original transcript without modification.
3. Support English, Malayalam, and Hindi.
4. Normalize Unicode and whitespace safely.
5. Validate transcript text and language.
6. Preserve technical terms, numbers, and negation.
7. Return structured normalization metadata.

Important
---------
This service does not translate, summarize, evaluate, or
automatically correct candidate answers.
"""

import logging
import unicodedata
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

SupportedLanguage = Literal["en", "ml", "hi"]

SUPPORTED_LANGUAGES = frozenset({"en", "ml", "hi"})
NORMALIZATION_VERSION = "1.0"


class TranscriptNormalizationError(ValueError):
    """Raised when transcript normalization fails validation."""


@dataclass(frozen=True, slots=True)
class NormalizedTranscript:
    """Immutable normalization result."""

    original_text: str
    normalized_text: str
    language: SupportedLanguage
    normalization_version: str
    language_preserved: bool
    changed: bool


def _validate_text(text: str) -> str:
    """
    Validate transcript input without modifying its contents.
    """
    if not isinstance(text, str):
        raise TranscriptNormalizationError(
            "Transcript text must be a string."
        )

    if not text.strip():
        raise TranscriptNormalizationError(
            "Transcript text cannot be empty or whitespace-only."
        )

    if len(text) > 50_000:
        raise TranscriptNormalizationError(
            "Transcript exceeds the maximum length of 50000 characters."
        )

    # NUL characters are not valid transcript content for this service.
    if "\x00" in text:
        raise TranscriptNormalizationError(
            "Transcript contains a forbidden NUL character."
        )

    return text


def _validate_language(language: str) -> SupportedLanguage:
    """
    Validate the supported language code.

    Language codes are intentionally strict so unsupported languages
    cannot silently enter the screening pipeline.
    """
    if not isinstance(language, str):
        raise TranscriptNormalizationError(
            "Language must be a string."
        )

    if language not in SUPPORTED_LANGUAGES:
        raise TranscriptNormalizationError(
            f"Unsupported language '{language}'. "
            f"Supported languages: {sorted(SUPPORTED_LANGUAGES)}."
        )

    return language  # type: ignore[return-value]


def normalize_transcript_text(text: str) -> str:
    """
    Normalize transcript text without translating or interpreting it.

    Rules:
    - Convert Unicode to NFC.
    - Normalize CRLF and CR line endings to LF.
    - Replace tabs and repeated horizontal whitespace with one space.
    - Trim leading and trailing whitespace.
    - Preserve meaningful line breaks.
    - Preserve punctuation, capitalization, numbers, negation,
      technical terms, and the original language.
    - Do not add punctuation or correct spelling automatically.
    """
    original = _validate_text(text)

    # Canonically equivalent Unicode sequences use a consistent form.
    normalized = unicodedata.normalize("NFC", original)

    # Normalize Windows and legacy Mac line endings.
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

    normalized_lines = []

    for line in normalized.split("\n"):
        # Split on whitespace, then rejoin with one ordinary space.
        # This removes tabs and repeated spaces without changing words.
        cleaned_line = " ".join(line.split())
        normalized_lines.append(cleaned_line)

    # Preserve meaningful paragraph boundaries while removing
    # empty lines at the beginning and end.
    normalized = "\n".join(normalized_lines).strip()

    if not normalized:
        raise TranscriptNormalizationError(
            "Transcript is empty after normalization."
        )

    return normalized


def normalize_transcript(
    text: str,
    language: SupportedLanguage,
) -> NormalizedTranscript:
    """
    Normalize a transcript and return structured metadata.

    Args:
        text: Original speech-to-text output.
        language: Validated language code (en, ml, or hi).

    Returns:
        NormalizedTranscript containing original and normalized text.

    Raises:
        TranscriptNormalizationError: If input or language is invalid.
    """
    original = _validate_text(text)
    validated_language = _validate_language(language)

    normalized = normalize_transcript_text(original)

    result = NormalizedTranscript(
        original_text=original,
        normalized_text=normalized,
        language=validated_language,
        normalization_version=NORMALIZATION_VERSION,
        language_preserved=True,
        changed=original != normalized,
    )

    logger.debug(
        "Transcript normalized | language=%s | changed=%s | "
        "original_length=%d | normalized_length=%d",
        validated_language,
        result.changed,
        len(original),
        len(normalized),
    )

    return result


def normalize_transcript_payload(
    payload: dict,
) -> dict:
    """
    Normalize a transcript payload using the schema field names.

    The input dictionary is not mutated. Existing metadata is retained,
    and the normalized text and normalization metadata are updated.

    Expected fields:
        original_text
        language
        optional normalization
    """
    if not isinstance(payload, dict):
        raise TranscriptNormalizationError(
            "Transcript payload must be a dictionary."
        )

    if "original_text" not in payload:
        raise TranscriptNormalizationError(
            "Transcript payload must contain original_text."
        )

    if "language" not in payload:
        raise TranscriptNormalizationError(
            "Transcript payload must contain language."
        )

    result = normalize_transcript(
        text=payload["original_text"],
        language=payload["language"],
    )

    updated = dict(payload)

    existing_metadata = payload.get("normalization", {})

    if not isinstance(existing_metadata, dict):
        raise TranscriptNormalizationError(
            "Normalization metadata must be a dictionary."
        )

    updated["normalized_text"] = result.normalized_text
    updated["normalization"] = {
        **existing_metadata,
        "version": result.normalization_version,
        "language_preserved": result.language_preserved,
    }

    return updated


