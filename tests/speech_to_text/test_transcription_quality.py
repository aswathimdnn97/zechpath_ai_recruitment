"""
Speech-to-text quality evaluation for ZechPath.

Evaluates HybridSpeechToTextService against human-verified
reference transcripts.

Metrics:
    WER - Word Error Rate
    CER - Character Error Rate
    RTF - Real-Time Factor

Run from the project root:
    python -m tests.speech_to_text.test_transcription_quality
"""

import json
import logging
import time
import unicodedata

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.service.hybrid_speech_to_text_service import (
    HybridSpeechToTextService,
)


# ============================================================
# PATHS AND CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REFERENCE_FILE = (
    PROJECT_ROOT
    / "tests"
    / "speech_to_text"
    / "test_data"
    / "reference_transcripts.json"
)

REPORT_FILE = (
    PROJECT_ROOT
    / "reports"
    / "speech_to_text"
    / "quality_report.json"
)

SUPPORTED_LANGUAGES = {"en", "ml", "hi"}

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# TEXT NORMALIZATION FOR FAIR COMPARISON
# ============================================================

def normalize_for_scoring(text: str) -> str:
    """
    Normalize text consistently before calculating WER/CER.

    - Apply Unicode NFC normalization.
    - Normalize whitespace.
    - Apply case folding.
    - Preserve punctuation and technical terms.
    - Do not translate or correct the transcript.
    """

    if not isinstance(text, str):
        return ""

    text = unicodedata.normalize("NFC", text)
    text = " ".join(text.split())

    return text.casefold()


# ============================================================
# EDIT DISTANCE
# ============================================================

def edit_distance(reference: list, hypothesis: list) -> int:
    """
    Calculate Levenshtein edit distance.

    Counts insertions, deletions, and substitutions.
    Uses O(min(n, m)) additional memory.
    """

    if len(reference) < len(hypothesis):
        reference, hypothesis = hypothesis, reference

    previous_row = list(range(len(hypothesis) + 1))

    for i, ref_item in enumerate(reference, start=1):
        current_row = [i]

        for j, hyp_item in enumerate(hypothesis, start=1):
            insertion = current_row[j - 1] + 1
            deletion = previous_row[j] + 1
            substitution = (
                previous_row[j - 1]
                + (ref_item != hyp_item)
            )

            current_row.append(
                min(insertion, deletion, substitution)
            )

        previous_row = current_row

    return previous_row[-1]


# ============================================================
# WER AND CER
# ============================================================

def calculate_wer(
    reference_text: str,
    hypothesis_text: str,
) -> dict[str, Any]:
    """
    Calculate word-level error rate.

    WER = (substitutions + deletions + insertions)
          / number of reference words
    """

    reference = normalize_for_scoring(reference_text).split()
    hypothesis = normalize_for_scoring(hypothesis_text).split()

    if not reference:
        raise ValueError(
            "WER cannot be calculated with an empty reference."
        )

    errors = edit_distance(reference, hypothesis)

    return {
        "wer": errors / len(reference),
        "reference_words": len(reference),
        "hypothesis_words": len(hypothesis),
        "edit_errors": errors,
    }


def calculate_cer(
    reference_text: str,
    hypothesis_text: str,
) -> dict[str, Any]:
    """
    Calculate character-level error rate.

    CER = character edit distance / reference character count.

    Whitespace is normalized before scoring. Remaining spaces
    and punctuation are included in the character sequence.
    """

    reference = list(normalize_for_scoring(reference_text))
    hypothesis = list(normalize_for_scoring(hypothesis_text))

    if not reference:
        raise ValueError(
            "CER cannot be calculated with an empty reference."
        )

    errors = edit_distance(reference, hypothesis)

    return {
        "cer": errors / len(reference),
        "reference_characters": len(reference),
        "hypothesis_characters": len(hypothesis),
        "edit_errors": errors,
    }


# ============================================================
# INPUT VALIDATION AND PATH RESOLUTION
# ============================================================

def load_test_cases() -> list[dict[str, Any]]:
    """Load and validate the reference-transcript dataset."""

    if not REFERENCE_FILE.is_file():
        raise FileNotFoundError(
            f"Reference file not found: {REFERENCE_FILE}"
        )

    with REFERENCE_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    test_cases = data.get("test_cases")

    if not isinstance(test_cases, list):
        raise ValueError(
            "'test_cases' must be a list in reference_transcripts.json."
        )

    return test_cases


def resolve_audio_path(audio_path: str) -> Path:
    """
    Resolve an audio path.

    Absolute paths are accepted. Relative paths are first checked
    against the project root, then against the test-data directory.
    """

    path = Path(audio_path)

    if path.is_absolute():
        return path

    project_path = PROJECT_ROOT / path

    if project_path.is_file():
        return project_path

    test_data_path = REFERENCE_FILE.parent / path

    if test_data_path.is_file():
        return test_data_path

    # Return the expected project-relative path so the caller
    # can report a useful missing-file error.
    return project_path


# ============================================================
# HYBRID TRANSCRIPTION
# ============================================================

def transcribe_audio(
    service: HybridSpeechToTextService,
    audio_path: Path,
    language: str,
) -> dict[str, Any]:
    """
    Run the existing hybrid service.

    The hybrid service selects the transcription provider
    according to the configured language routing.
    """

    result = service.transcribe_file(
        audio_path=str(audio_path),
        language=language,
    )

    if not isinstance(result, dict):
        raise TypeError(
            "HybridSpeechToTextService.transcribe_audio() "
            "must return a dictionary."
        )

    return result


def get_transcript(result: dict[str, Any]) -> str:
    """Read the transcript from the standardized hybrid response."""

    transcript = result.get(
        "original_text",
        result.get("transcript", ""),
    )

    if not isinstance(transcript, str):
        raise TypeError(
            "The transcription service returned a non-string transcript."
        )

    return transcript


# ============================================================
# EVALUATE ONE TEST CASE
# ============================================================

def evaluate_test_case(
    service: HybridSpeechToTextService,
    case: dict[str, Any],
) -> dict[str, Any]:
    """Transcribe one audio file and evaluate it against its reference."""

    test_id = case.get("test_id", "UNKNOWN")
    language = case.get("language", "")
    reference_text = case.get("reference_text", "")

    result: dict[str, Any] = {
        "test_id": test_id,
        "language": language,
        "condition": case.get("condition"),
        "audio_path": case.get("audio_path"),
    }

    if language not in SUPPORTED_LANGUAGES:
        result.update({
            "status": "invalid_language",
            "error": f"Unsupported language: {language!r}",
        })
        return result

    if not isinstance(reference_text, str) or not reference_text.strip():
        result.update({
            "status": "skipped_missing_reference",
            "message": (
                "Add a human-verified reference transcript "
                "before evaluating accuracy."
            ),
        })
        return result

    raw_audio_path = case.get("audio_path")

    if not isinstance(raw_audio_path, str) or not raw_audio_path.strip():
        result.update({
            "status": "invalid_audio_path",
            "error": "audio_path must be a non-empty string.",
        })
        return result

    audio_path = resolve_audio_path(raw_audio_path)

    if not audio_path.is_file():
        result.update({
            "status": "missing_audio",
            "error": f"Audio file not found: {audio_path}",
        })
        return result

    started = time.perf_counter()

    try:
        transcription_result = transcribe_audio(
            service=service,
            audio_path=audio_path,
            language=language,
        )

        elapsed_seconds = time.perf_counter() - started

        hypothesis_text = get_transcript(transcription_result)

        if not hypothesis_text.strip():
            result.update({
                "status": "empty_transcription",
                "processing_time_seconds": round(
                    elapsed_seconds, 3
                ),
                "provider": transcription_result.get("provider"),
                "model": transcription_result.get("model"),
                "service_status": transcription_result.get("status"),
            })
            return result

        wer_result = calculate_wer(
            reference_text,
            hypothesis_text,
        )

        cer_result = calculate_cer(
            reference_text,
            hypothesis_text,
        )

        duration = transcription_result.get(
            "duration_seconds",
            transcription_result.get("audio_duration_seconds"),
        )

        rtf = (
            elapsed_seconds / duration
            if isinstance(duration, (int, float)) and duration > 0
            else None
        )

        result.update({
            "status": "evaluated",
            "reference_text": reference_text,
            "hypothesis_text": hypothesis_text,
            "provider": transcription_result.get("provider"),
            "model": transcription_result.get("model"),
            "device": transcription_result.get("device"),
            "service_status": transcription_result.get("status"),
            "is_partial": transcription_result.get(
                "is_partial", False
            ),
            "audio_duration_seconds": duration,
            "processing_time_seconds": round(
                elapsed_seconds, 3
            ),
            "real_time_factor": (
                round(rtf, 4) if rtf is not None else None
            ),
            "wer": round(wer_result["wer"], 6),
            "wer_percent": round(
                wer_result["wer"] * 100, 2
            ),
            "cer": round(cer_result["cer"], 6),
            "cer_percent": round(
                cer_result["cer"] * 100, 2
            ),
            "reference_words": wer_result["reference_words"],
            "hypothesis_words": wer_result["hypothesis_words"],
            "word_edit_errors": wer_result["edit_errors"],
            "reference_characters": (
                cer_result["reference_characters"]
            ),
            "hypothesis_characters": (
                cer_result["hypothesis_characters"]
            ),
            "character_edit_errors": cer_result["edit_errors"],
        })

    except Exception as exc:
        logger.exception(
            "Failed to evaluate test case %s",
            test_id,
        )

        result.update({
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "processing_time_seconds": round(
                time.perf_counter() - started, 3
            ),
        })

    return result


# ============================================================
# AGGREGATE METRICS
# ============================================================

def build_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate corpus-level WER and CER.

    Aggregate edit errors and reference lengths rather than
    taking a simple average of per-file percentages.
    """

    evaluated = [
        item for item in results
        if item.get("status") == "evaluated"
    ]

    total_word_errors = sum(
        item["word_edit_errors"] for item in evaluated
    )
    total_reference_words = sum(
        item["reference_words"] for item in evaluated
    )

    total_character_errors = sum(
        item["character_edit_errors"] for item in evaluated
    )
    total_reference_characters = sum(
        item["reference_characters"] for item in evaluated
    )

    corpus_wer = (
        total_word_errors / total_reference_words
        if total_reference_words else None
    )

    corpus_cer = (
        total_character_errors / total_reference_characters
        if total_reference_characters else None
    )

    processing_times = [
        item["processing_time_seconds"]
        for item in evaluated
        if isinstance(
            item.get("processing_time_seconds"),
            (int, float),
        )
    ]

    return {
        "total_cases": len(results),
        "evaluated_cases": len(evaluated),
        "skipped_cases": sum(
            item.get("status", "").startswith("skipped")
            for item in results
        ),
        "error_cases": sum(
            item.get("status") == "error"
            for item in results
        ),
        "missing_audio_cases": sum(
            item.get("status") == "missing_audio"
            for item in results
        ),
        "corpus_wer": (
            round(corpus_wer, 6)
            if corpus_wer is not None else None
        ),
        "corpus_wer_percent": (
            round(corpus_wer * 100, 2)
            if corpus_wer is not None else None
        ),
        "corpus_cer": (
            round(corpus_cer, 6)
            if corpus_cer is not None else None
        ),
        "corpus_cer_percent": (
            round(corpus_cer * 100, 2)
            if corpus_cer is not None else None
        ),
        "average_processing_time_seconds": (
            round(
                sum(processing_times) / len(processing_times),
                3,
            )
            if processing_times else None
        ),
    }

def build_condition_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate WER and CER by audio test condition."""

    groups: dict[str, list[dict[str, Any]]] = {}

    for item in results:
        if item.get("status") != "evaluated":
            continue

        condition = item.get("condition") or "unspecified"
        groups.setdefault(condition, []).append(item)

    summary = {}

    for condition, cases in sorted(groups.items()):
        word_errors = sum(
            item["word_edit_errors"] for item in cases
        )
        reference_words = sum(
            item["reference_words"] for item in cases
        )

        character_errors = sum(
            item["character_edit_errors"] for item in cases
        )
        reference_characters = sum(
            item["reference_characters"] for item in cases
        )

        wer = (
            word_errors / reference_words
            if reference_words else None
        )
        cer = (
            character_errors / reference_characters
            if reference_characters else None
        )

        summary[condition] = {
            "evaluated_cases": len(cases),
            "corpus_wer": (
                round(wer, 6) if wer is not None else None
            ),
            "corpus_wer_percent": (
                round(wer * 100, 2) if wer is not None else None
            ),
            "corpus_cer": (
                round(cer, 6) if cer is not None else None
            ),
            "corpus_cer_percent": (
                round(cer * 100, 2) if cer is not None else None
            ),
        }

    return summary


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """Run the quality evaluation and save the report."""

    test_cases = load_test_cases()

    # Construct once so model loading/caching can be reused.
    service = HybridSpeechToTextService()

    results = []

    for index, case in enumerate(test_cases, start=1):
        test_id = case.get("test_id", f"CASE_{index}")

        logger.info(
            "[%s/%s] Evaluating %s",
            index,
            len(test_cases),
            test_id,
        )

        result = evaluate_test_case(service, case)
        results.append(result)

        status = result.get("status", "unknown")

        if status == "evaluated":
            logger.info(
                "PASS | %s | provider=%s | WER=%s%% | CER=%s%%",
                test_id,
                result.get("provider"),
                result.get("wer_percent"),
                result.get("cer_percent"),
            )
        else:
            logger.warning(
                "%s | %s | %s",
                status.upper(),
                test_id,
                result.get("error", result.get("message", "")),
            )

    report = {
        "report_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_method": {
            "transcription_service": "HybridSpeechToTextService",
            "wer": "Word edit distance / reference word count",
            "cer": "Character edit distance / reference character count",
            "text_normalization": (
                "Unicode NFC, whitespace collapse, casefold; "
                "punctuation preserved"
            ),
            "references": "Human-verified reference transcripts",
        },
        "summary": build_summary(results),
        "condition_summary": build_condition_summary(results),
        "results": results,
    }

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    summary = report["summary"]

    print("\n========== SPEECH-TO-TEXT QUALITY REPORT ==========")
    print(f"Total cases:       {summary['total_cases']}")
    print(f"Evaluated:         {summary['evaluated_cases']}")
    print(f"Skipped:           {summary['skipped_cases']}")
    print(f"Errors:            {summary['error_cases']}")
    print(f"Corpus WER:        {summary['corpus_wer_percent']}%")
    print(f"Corpus CER:        {summary['corpus_cer_percent']}%")
    print(f"Report saved to:   {REPORT_FILE}")


if __name__ == "__main__":
    main()