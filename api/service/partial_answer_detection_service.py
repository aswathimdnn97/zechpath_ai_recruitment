"""
partial_answer_detection_service.py

Responsibilities
----------------
1. Detect explicit textual signs of an unfinished answer.
2. Support English, Malayalam, and Hindi.
3. Avoid classifying answers as partial based only on their length.
4. Preserve the original recognized text.
5. Keep detection separate from audio interruption and silence detection.
"""

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True)
class PartialAnswerDetection:
    is_partial: bool
    reason: str | None = None


class PartialAnswerDetectionService:
    """Conservative rule-based detection of unfinished spoken answers."""

    SUPPORTED_LANGUAGES = {"en", "ml", "hi"}

    # Strong signs that the recognized answer ended before the thought
    # was completed. These are intentionally not general conjunctions.
    TRAILING_CUES = {
        "en": (
            "because",
            "although",
            "though",
            "if",
            "when",
            "which",
            "that",
            "such as",
            "for example",
            "in order to",
            "depends on",
            "based on",
            "one of the",
            "the reason is",
        ),
        "ml": (
            "കാരണം",
            "എങ്കിൽ",
            "എന്നാൽ",
            "ഉദാഹരണത്തിന്",
        ),
        "hi": (
            "क्योंकि",
            "अगर",
            "यदि",
            "जबकि",
            "उदाहरण के लिए",
        ),
    }

    # Punctuation that strongly suggests the speaker or recognizer
    # stopped mid-thought. A normal final full stop is not a cue.
    TRAILING_INTERRUPTION_MARKERS = ("...", "…", "—", "--")

    def detect(
        self,
        text: str,
        language: str = "en",
    ) -> PartialAnswerDetection:
        """
        Return whether the text contains a strong unfinished-answer cue.

        This method does not modify or correct the supplied text.
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        language = language.lower().strip()
        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")

        normalized = unicodedata.normalize("NFC", text).strip()

        if not normalized:
            return PartialAnswerDetection(
                is_partial=False,
                reason=None,
            )

        # Explicit ellipsis or interruption-style ending.
        if normalized.endswith(self.TRAILING_INTERRUPTION_MARKERS):
            return PartialAnswerDetection(
                is_partial=True,
                reason="unfinished_punctuation",
            )

        # Remove ordinary sentence-final punctuation for cue matching.
        match_text = re.sub(r"[.!?।]+$", "", normalized).strip()
        match_text = re.sub(r"\s+", " ", match_text).casefold()

        for cue in self.TRAILING_CUES[language]:
            cue_normalized = re.sub(r"\s+", " ", cue).casefold()

            if (
                match_text == cue_normalized
                or match_text.endswith(" " + cue_normalized)
            ):
                return PartialAnswerDetection(
                    is_partial=True,
                    reason="trailing_incomplete_phrase",
                )

        return PartialAnswerDetection(
            is_partial=False,
            reason=None,
        )