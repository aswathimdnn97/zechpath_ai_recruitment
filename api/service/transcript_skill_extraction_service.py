
"""
transcript_skill_extraction_service.py

Responsibilities
----------------
1. Extract skills from normalized HR screening transcripts.
2. Reuse existing spelling, synonym, and validation modules.
3. Preserve transcript text without modification.
4. Return canonical skills with source evidence.
5. Keep transcript skill extraction separate from resume parsing.
"""

from __future__ import annotations

from typing import Any

from document_processing.resume.entity_extracter.skill.skill_extractor_from_section import (
    extract_skills_from_section,
)
from document_processing.resume.entity_extracter.skill.spelling_resolver import (
    resolve_spelling,
)
from document_processing.resume.entity_extracter.skill.synonym_resolver import (
    resolve_synonyms,
)
from document_processing.resume.entity_extracter.skill.master_skill_validator import (
    validate_skills,
)


SUPPORTED_LANGUAGES = frozenset({"en", "ml", "hi"})


class TranscriptSkillExtractionError(ValueError):
    """Raised when transcript skill extraction input is invalid."""



def _deduplicate_sources(sources: Any) -> list[Any]:
    """Remove duplicate source records without changing their original values."""

    if not isinstance(sources, list):
        return []

    unique_sources = []
    seen = set()

    for source in sources:
        if not isinstance(source, dict):
            # Preserve unexpected entries rather than silently discarding them.
            unique_sources.append(source)
            continue

        source_section = source.get("source_section")
        source_text = source.get("source_text")
        source_skill = source.get("source_skill")

        # Deduplicate case-insensitively while preserving the first record.
        key = (
            source_section.casefold().strip()
            if isinstance(source_section, str)
            else source_section,
            source_text.casefold().strip()
            if isinstance(source_text, str)
            else source_text,
            source_skill.casefold().strip()
            if isinstance(source_skill, str)
            else source_skill,
        )

        if key in seen:
            continue

        seen.add(key)
        unique_sources.append(source)

    return unique_sources


def extract_transcript_skills(
    transcript: dict[str, Any],
) -> dict[str, Any]:
    """
    Extract and validate skills from a transcript payload.

    Expected input:
        {
            "original_text": "...",
            "normalized_text": "...",
            "language": "en"
        }

    Original and normalized text are returned unchanged.
    """

    if not isinstance(transcript, dict):
        raise TranscriptSkillExtractionError(
            "Transcript must be a dictionary."
        )

    original_text = transcript.get("original_text")
    normalized_text = transcript.get("normalized_text")
    language = transcript.get("language")

    if not isinstance(original_text, str):
        raise TranscriptSkillExtractionError(
            "original_text must be a string."
        )

    if not isinstance(normalized_text, str):
        raise TranscriptSkillExtractionError(
            "normalized_text must be a string."
        )

    if language not in SUPPORTED_LANGUAGES:
        raise TranscriptSkillExtractionError(
            "language must be one of: en, ml, hi."
        )

    if not normalized_text.strip():
        return {
            "original_text": original_text,
            "normalized_text": normalized_text,
            "language": language,
            "recognized_skills": [],
            "skill_count": 0,
        }

    # Stage 1: Extract configured master skills and aliases.
    candidates = extract_skills_from_section(
        "transcript",
        normalized_text,
    )

    # Stage 2: Resolve known spelling variations.
    spelling_resolved = resolve_spelling(candidates)

    # Stage 3: Resolve configured aliases and synonyms.
    synonym_resolved = resolve_synonyms(spelling_resolved)

    # Stage 4: Validate canonical skills against the master list.
    validated = validate_skills(synonym_resolved)

    # Stage 5: Return only validated canonical skills.
    recognized_skills = []

    for candidate in validated:
        if not isinstance(candidate, dict):
            continue

        skill_name = candidate.get("skill")

        if not isinstance(skill_name, str) or not skill_name.strip():
            continue

        recognized_skills.append({
            "skill": skill_name,
            "skill_id": candidate.get("skill_id"),
            "source_text": candidate.get("source_text"),
            "sources": _deduplicate_sources(candidate.get("sources", [])),
            "original_skill": candidate.get("original_skill"),
            "original_skills": candidate.get("original_skills", []),
            "resolution_method": candidate.get("resolution_method"),
            "matched_by": candidate.get("matched_by"),
        })

    return {
        "original_text": original_text,
        "normalized_text": normalized_text,
        "language": language,
        "recognized_skills": recognized_skills,
        "skill_count": len(recognized_skills),
    }
