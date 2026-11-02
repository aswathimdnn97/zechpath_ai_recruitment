
"""
transcript_text_cleanup_service.py

Responsibilities
----------------
1. Remove configured filler words conservatively.
2. Normalize punctuation spacing.
3. Apply conservative English sentence-case normalization.
4. Preserve Malayalam and Hindi script conventions.
5. Preserve technical terms, numbers, negation, and meaning.
6. Keep the original transcript unchanged.
7. Return structured cleanup metadata.

This service does not translate, summarize, evaluate, or
factually correct candidate answers.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

SupportedLanguage = Literal["en", "ml", "hi"]

SUPPORTED_LANGUAGES = frozenset({"en", "ml", "hi"})
CLEANUP_VERSION = "1.0"
MAX_TEXT_LENGTH = 50_000

# Only remove fillers when they occur as standalone tokens or
# configured phrases. Keep this list conservative and configurable.
FILLER_PHRASES: dict[str, tuple[str, ...]] = {
    "en": (
        "you know",
        "i mean",
        "um",
        "uh",
        "erm",
        "er",
        "hmm",
    ),
    "ml": (
        "ഉം",
        "ആ",
        "അത്",
    ),
    "hi": (
        "उम्म",
        "अम्म",
        "हम्म",
    ),
}

# These terms are protected during English case normalization.
# Extend this set as your project's technical vocabulary grows.
PROTECTED_TERMS = (
    "FastAPI",
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "Django",
    "Flask",
    "ReactJS",
    "React",
    "Node.js",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "SQL",
    "NoSQL",
    "REST API",
    "HTML",
    "CSS",
    "NumPy",
    "Pandas",
    "GitHub",
    "Git",
    "API",
    "HTTP",
    "HTTPS",
    "JSON",
    "XML",
    "AWS",
    "Azure",
    "Docker",
    "Kubernetes",
    "Linux",
    "Windows",
    "FastAPI",
)

# Protect known spellings while applying English sentence casing.
# Longer phrases are matched first.
_PROTECTED_PATTERN = re.compile(
    r"(?<!\w)("
    + "|".join(
        re.escape(term)
        for term in sorted(set(PROTECTED_TERMS), key=len, reverse=True)
    )
    + r")(?!\w)",
    flags=re.IGNORECASE,
)

_WORD_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


class TranscriptTextCleanupError(ValueError):
    """Raised when transcript cleanup input is invalid."""


@dataclass(frozen=True, slots=True)
class CleanedTranscript:
    """Immutable text cleanup result."""

    original_text: str
    input_text: str
    cleaned_text: str
    language: SupportedLanguage
    cleanup_version: str
    removed_fillers: tuple[str, ...]
    punctuation_changed: bool
    case_changed: bool
    changed: bool


def _validate_text(text: str) -> str:
    if not isinstance(text, str):
        raise TranscriptTextCleanupError(
            "Transcript text must be a string."
        )

    if not text.strip():
        raise TranscriptTextCleanupError(
            "Transcript text cannot be empty or whitespace-only."
        )

    if len(text) > MAX_TEXT_LENGTH:
        raise TranscriptTextCleanupError(
            f"Transcript exceeds the maximum length of {MAX_TEXT_LENGTH} characters."
        )

    if "\x00" in text:
        raise TranscriptTextCleanupError(
            "Transcript contains a forbidden NUL character."
        )

    return text


def _validate_language(language: str) -> SupportedLanguage:
    if not isinstance(language, str):
        raise TranscriptTextCleanupError(
            "Language must be a string."
        )

    if language not in SUPPORTED_LANGUAGES:
        raise TranscriptTextCleanupError(
            f"Unsupported language '{language}'. "
            f"Supported languages: {sorted(SUPPORTED_LANGUAGES)}."
        )

    return language  # type: ignore[return-value]


def _remove_fillers(
    text: str,
    language: SupportedLanguage,
) -> tuple[str, tuple[str, ...]]:
    """
    Remove configured filler phrases as standalone text.

    Matching is case-insensitive for English. Malayalam and Hindi
    matching use their literal configured script forms.
    """
    removed: list[str] = []
    phrases = sorted(
        FILLER_PHRASES[language],
        key=len,
        reverse=True,
    )

    result = text

    for phrase in phrases:
        flags = re.IGNORECASE if language == "en" else 0

        # Require word boundaries for Latin fillers. For phrases in
        # Indic scripts, explicit whitespace/punctuation boundaries
        # prevent matching inside a larger word.
        pattern = re.compile(
            rf"(?<!\w){re.escape(phrase)}(?!\w)",
            flags=flags,
        )

        def replace_match(match: re.Match[str]) -> str:
            removed.append(match.group(0))
            return " "

        result = pattern.sub(replace_match, result)

    # Remove punctuation left at the beginning after a filler is removed.
    result = re.sub(r"^\s*[,;:]\s*", "", result)

    # Clean up separators left between words after filler removal.
    result = re.sub(r",\s*[,;:]+", ",", result)
    result = re.sub(r"[,;:]\s*[,;:]+", ",", result)

    return result, tuple(removed)
    return result, tuple(removed)


def _normalize_punctuation(text: str) -> str:
    """
    Normalize punctuation spacing without rewriting sentence meaning.

    - Remove spaces before punctuation.
    - Ensure one space after common punctuation when followed by text.
    - Collapse repeated identical sentence-ending punctuation.
    - Add terminal punctuation only when the text has none.
    """
    text = re.sub(r"[ \t]+", " ", text).strip()

    # Remove spaces before punctuation.
    text = re.sub(r"\s+([,.;:!?।])", r"\1", text)

    # Add a space after punctuation when directly followed by a word.
    text = re.sub(r"([,;:!?।])(?=\w)", r"\1 ", text)

    # Avoid repeated identical punctuation runs such as "!!!".
    # Do not collapse mixed punctuation such as "?!".
    text = re.sub(r"([!?।])\1{1,}", r"\1", text)
    text = re.sub(r"\.{2,}", ".", text)

    text = text.strip()

    if not text:
        return text

    # Do not append punctuation to a line that already ends with
    # any recognized terminal mark or closing quotation/bracket.
    terminal = re.compile(r"""[.!?।…]["'’”)\]}]*$""")

    if not terminal.search(text):
        text += "।" if any(
            "\u0900" <= char <= "\u097F" for char in text
        ) else "."

    return text




def _normalize_english_case(text: str) -> str:
    """
    Apply conservative English sentence casing.

    Normalize all-uppercase text to sentence case while preserving
    technical terms, names, and the standalone pronoun I.
    """
    protected: list[str] = []

    def save_term(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"ZXPROTECTED{len(protected) - 1}ZX"

    result = _PROTECTED_PATTERN.sub(save_term, text)

    letters = [char for char in result if char.isalpha()]

    # Only normalize text that is entirely uppercase.
    if letters and all(char.isupper() for char in letters):
        result = result.lower()

    # Capitalize the first letter and sentence starts.
    result = re.sub(
        r"^(\s*)([a-z])",
        lambda m: m.group(1) + m.group(2).upper(),
        result,
    )
    result = re.sub(
        r"([.!?]\s+)([a-z])",
        lambda m: m.group(1) + m.group(2).upper(),
        result,
    )

    # Preserve the standalone English pronoun I.
    result = re.sub(r"(?<!\w)i(?!\w)", "I", result)

    # Restore protected terms case-insensitively.
    for index, term in enumerate(protected):
        result = re.sub(
            rf"(?i)zxprotected{index}zx",
            lambda _: term,
            result,
        )

    return result


def cleanup_transcript_text(
    text: str,
    language: SupportedLanguage,
) -> CleanedTranscript:
    """
    Clean an already-transcribed answer.

    Use normalized_text as input when normalization has already run.
    The original transcript remains available and is never overwritten.
    """
    original = _validate_text(text)
    validated_language = _validate_language(language)

    # Canonical Unicode representation and line-ending handling.
    input_text = unicodedata.normalize("NFC", original)
    input_text = input_text.replace("\r\n", "\n").replace("\r", "\n")

    without_fillers, removed_fillers = _remove_fillers(
        input_text,
        validated_language,
    )

    # Normalize horizontal whitespace while preserving line boundaries.
    lines = [
        re.sub(r"[^\S\n]+", " ", line).strip()
        for line in without_fillers.split("\n")
    ]
    cleaned = "\n".join(lines).strip()

    before_punctuation = cleaned
    cleaned = _normalize_punctuation(cleaned)

    before_case = cleaned
    if validated_language == "en":
        cleaned = _normalize_english_case(cleaned)

    result = CleanedTranscript(
        original_text=original,
        input_text=input_text,
        cleaned_text=cleaned,
        language=validated_language,
        cleanup_version=CLEANUP_VERSION,
        removed_fillers=removed_fillers,
        punctuation_changed=before_punctuation != _normalize_punctuation(
            before_punctuation
        ),
        case_changed=before_case != cleaned,
        changed=original != cleaned,
    )

    logger.debug(
        "Transcript cleanup completed | language=%s | changed=%s | "
        "removed_filler_count=%d",
        validated_language,
        result.changed,
        len(result.removed_fillers),
    )

    return result


def cleanup_transcript_payload(payload: dict) -> dict:
    """
    Clean a transcript payload without mutating the input dictionary.

    Uses normalized_text when available; otherwise uses original_text.
    Stores cleaned_text and separate cleanup metadata.
    """
    if not isinstance(payload, dict):
        raise TranscriptTextCleanupError(
            "Transcript payload must be a dictionary."
        )

    if "language" not in payload:
        raise TranscriptTextCleanupError(
            "Transcript payload must contain language."
        )

    source_text = payload.get("normalized_text")

    if source_text is None:
        source_text = payload.get("original_text")

    if source_text is None:
        raise TranscriptTextCleanupError(
            "Transcript payload must contain normalized_text or original_text."
        )

    result = cleanup_transcript_text(
        text=source_text,
        language=payload["language"],
    )

    updated = dict(payload)
    existing_metadata = payload.get("cleanup", {})

    if not isinstance(existing_metadata, dict):
        raise TranscriptTextCleanupError(
            "Cleanup metadata must be a dictionary."
        )

    updated["cleaned_text"] = result.cleaned_text
    updated["cleanup"] = {
        **existing_metadata,
        "version": result.cleanup_version,
        "changed": result.changed,
        "removed_fillers": list(result.removed_fillers),
        "punctuation_changed": result.punctuation_changed,
        "case_changed": result.case_changed,
    }

    return updated
