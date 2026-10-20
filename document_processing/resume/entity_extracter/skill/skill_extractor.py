"""
Central skill extraction orchestrator with optional Ollama fallback.

Pipeline:
1. Collect skill candidates from relevant resume sections.
2. Deduplicate candidates and merge source evidence.
3. Resolve spelling and synonyms.
4. Validate against the master skill dictionary.
5. Use the LLM only when deterministic extraction yields no usable skills.
6. Expand technology stacks.
7. Deduplicate final skills.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from document_processing.resume.entity_extracter.skill.skill_list_splitter import (
    split_skill_line,
)
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
from document_processing.resume.entity_extracter.skill.stack_resolver import (
    expand_skill_stacks,
)
from document_processing.common.llm_fallback_service import (
    llm_fallback_service,
)

logger = logging.getLogger(__name__)


SKILL_SOURCE_SECTIONS = {
    "skills",
    "summary",
    "experience",
    "projects",
}

IGNORED_SECTIONS = {
    "personal_information",
    "languages",
    "interests",
    "references",
    "declaration",
}

SKILL_FALLBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {"type": "string"},
        }
    },
    "required": ["skills"],
    "additionalProperties": False,
}


def _flatten_section(value: Any) -> list[str]:
    """Recursively flatten strings, dictionaries, and sequences."""

    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []

    if isinstance(value, dict):
        result = []
        for nested_value in value.values():
            result.extend(_flatten_section(nested_value))
        return result

    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            result.extend(_flatten_section(item))
        return result

    return [str(value)]


def _normalize(value: Any) -> str:
    """Normalize a string for case-insensitive comparison."""

    if not isinstance(value, str):
        return ""

    return " ".join(value.strip().lower().split())


def _normalize_section_name(section_name: Any) -> str:
    """Normalize resume section names."""

    if not isinstance(section_name, str):
        return ""

    return " ".join(section_name.strip().lower().split())


def _source_key(source: Any) -> str:
    """Build a stable key for source evidence."""

    if isinstance(source, dict):
        return "|".join(
            str(source.get(field, "")).strip()
            for field in (
                "source_section",
                "source_text",
                "source_skill",
            )
        ).lower()

    return str(source).strip().lower()


def _merge_sources(existing: Any, incoming: Any) -> list[Any]:
    """Merge evidence records without duplicates."""

    if not isinstance(existing, list):
        existing = [existing] if existing else []

    if not isinstance(incoming, list):
        incoming = [incoming] if incoming else []

    merged = []
    seen = set()

    for source in existing + incoming:
        key = _source_key(source)

        if key and key not in seen:
            seen.add(key)
            merged.append(source)

    return merged


def _merge_source_metadata(
    existing: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    """Merge source sections, source text, and structured evidence."""

    if not isinstance(existing, dict) or not isinstance(candidate, dict):
        return

    sections = []

    for item in (existing, candidate):
        values = item.get("source_sections", [])

        if isinstance(values, str):
            values = [values]

        if isinstance(values, list):
            sections.extend(values)

        source_section = item.get("source_section")
        if source_section:
            sections.append(source_section)

    existing["source_sections"] = list(
        dict.fromkeys(
            str(section).strip()
            for section in sections
            if str(section).strip()
        )
    )

    if not existing.get("source_text") and candidate.get("source_text"):
        existing["source_text"] = candidate["source_text"]

    def build_sources(item: dict[str, Any]) -> list[Any]:
        sources = item.get("sources", [])

        if isinstance(sources, list) and sources:
            return sources

        if item.get("source_section") or item.get("source_text"):
            return [
                {
                    "source_section": item.get("source_section"),
                    "source_text": item.get("source_text", ""),
                    "source_skill": item.get("skill"),
                }
            ]

        return []

    existing["sources"] = _merge_sources(
        build_sources(existing),
        build_sources(candidate),
    )


def _collect_candidates(
    sections: dict[str, Any],
    profile: bool = False,
) -> list[dict[str, Any]]:
    """Collect skill candidates from configured resume sections."""

    candidates = []
    collect_start = time.perf_counter() if profile else 0.0

    if not isinstance(sections, dict):
        return candidates

    for raw_section_name, section_block in sections.items():
        section_name = _normalize_section_name(raw_section_name)

        if (
            not section_name
            or section_name in IGNORED_SECTIONS
            or section_name not in SKILL_SOURCE_SECTIONS
        ):
            continue

        section_start = time.perf_counter() if profile else 0.0
        count_before = len(candidates)

        if section_name == "skills":
            lines = _flatten_section(section_block)
            splitter_start = time.perf_counter() if profile else 0.0

            raw_skills = split_skill_line(lines)

            if profile:
                print(
                    f"[SKILL SPLITTER] "
                    f"time={time.perf_counter() - splitter_start:.6f}s "
                    f"lines={len(lines)} "
                    f"skills={len(raw_skills) if isinstance(raw_skills, list) else 0}"
                )

            if isinstance(raw_skills, list):
                for skill in raw_skills:
                    if not isinstance(skill, str) or not skill.strip():
                        continue

                    skill = skill.strip()
                    candidates.append(
                        {
                            "skill": skill,
                            "source_section": "skills",
                            "source_text": skill,
                            "extraction_method": "skills_section",
                            "sources": [
                                {
                                    "source_section": "skills",
                                    "source_text": skill,
                                    "source_skill": skill,
                                }
                            ],
                        }
                    )

        else:
            fragments = _flatten_section(section_block)
            extraction_time = 0.0
            fragment_count = 0

            for source_text in fragments:
                if not isinstance(source_text, str) or not source_text.strip():
                    continue

                source_text = source_text.strip()
                fragment_count += 1
                fragment_start = time.perf_counter() if profile else 0.0

                section_candidates = extract_skills_from_section(
                    section_name=section_name,
                    section_block=source_text,
                )

                if profile:
                    extraction_time += time.perf_counter() - fragment_start

                if not isinstance(section_candidates, list):
                    continue

                for candidate in section_candidates:
                    if not isinstance(candidate, dict):
                        continue

                    skill = candidate.get("skill")
                    if not isinstance(skill, str) or not skill.strip():
                        continue

                    candidate["skill"] = skill.strip()
                    candidate["source_section"] = section_name
                    candidate["source_text"] = (
                        candidate.get("source_text") or source_text
                    )
                    candidate.setdefault("extraction_method", "section_text")

                    if not isinstance(candidate.get("sources"), list):
                        candidate["sources"] = []

                    if not candidate["sources"]:
                        candidate["sources"] = [
                            {
                                "source_section": section_name,
                                "source_text": source_text,
                                "source_skill": candidate["skill"],
                            }
                        ]

                    candidates.append(candidate)

            if profile:
                print(
                    f"[SKILL SECTION] section={section_name:<12} "
                    f"fragments={fragment_count} "
                    f"extract={extraction_time:.6f}s "
                    f"candidates={len(candidates) - count_before}"
                )

        if profile:
            print(
                f"[SKILL SECTION TOTAL] section={section_name:<12} "
                f"time={time.perf_counter() - section_start:.6f}s "
                f"candidates={len(candidates) - count_before}"
            )

    if profile:
        print(
            f"[SKILL COLLECT] total={time.perf_counter() - collect_start:.6f}s "
            f"candidates={len(candidates)}"
        )

    return candidates


def _deduplicate_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate candidates by normalized skill name."""

    unique = []
    seen = {}

    if not isinstance(candidates, list):
        return unique

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        skill = candidate.get("skill")
        if not isinstance(skill, str) or not skill.strip():
            continue

        skill = skill.strip()
        candidate["skill"] = skill
        key = _normalize(skill)

        if not key:
            continue

        if key in seen:
            _merge_source_metadata(seen[key], candidate)
            continue

        if not candidate.get("sources"):
            candidate["sources"] = [
                {
                    "source_section": candidate.get("source_section"),
                    "source_text": candidate.get("source_text", ""),
                    "source_skill": skill,
                }
            ]

        seen[key] = candidate
        unique.append(candidate)

    return unique


def _deduplicate_final_skills(
    skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate final skills by ID and normalized name."""

    final = []
    seen_ids = {}
    seen_names = {}

    if not isinstance(skills, list):
        return final

    for skill in skills:
        if not isinstance(skill, dict):
            continue

        skill_id = skill.get("skill_id")
        name = skill.get("skill")
        normalized_name = _normalize(name) if isinstance(name, str) else ""

        existing = seen_ids.get(skill_id) if skill_id is not None else None

        if existing is None and normalized_name:
            existing = seen_names.get(normalized_name)

        if existing is not None:
            _merge_source_metadata(existing, skill)

            source_skills = []
            for item in (existing, skill):
                values = item.get("source_skills", [])
                if isinstance(values, str):
                    values = [values]
                if isinstance(values, list):
                    source_skills.extend(values)

                if item.get("source_skill"):
                    source_skills.append(item["source_skill"])

            if source_skills:
                existing["source_skills"] = list(
                    dict.fromkeys(
                        str(value).strip()
                        for value in source_skills
                        if str(value).strip()
                    )
                )

            continue

        final.append(skill)

        if skill_id is not None:
            seen_ids[skill_id] = skill

        if normalized_name:
            seen_names[normalized_name] = skill

    return final


def _llm_skill_fallback(sections):
    """
    Extract skills with the LLM only when deterministic extraction fails.

    LLM suggestions are converted into the normal candidate format and
    passed through the master skill validator before being returned.
    """
    relevant_sections = {
        "skills",
        "summary",
        "experience",
        "projects",
    }

    text_parts = []

    for section_name, section_content in sections.items():
        if section_name.lower() not in relevant_sections:
            continue

        if isinstance(section_content, str):
            content = section_content.strip()
            if content:
                text_parts.append(content)

        elif isinstance(section_content, list):
            for item in section_content:
                if isinstance(item, str) and item.strip():
                    text_parts.append(item.strip())

                elif isinstance(item, dict):
                    content = (
                        item.get("text")
                        or item.get("description")
                        or item.get("content")
                    )

                    if isinstance(content, str) and content.strip():
                        text_parts.append(content.strip())

    resume_text = "\n".join(text_parts).strip()

    if not resume_text:
        return []

    schema = {
        "type": "object",
        "properties": {
            "skills": {
                "type": "array",
                "items": {"type": "string"},
            }
        },
        "required": ["skills"],
        "additionalProperties": False,
    }

    try:
        response = llm_fallback_service.extract_json(
            entity_name="skills",
            text=resume_text,
            output_schema=schema,
        )

        if not isinstance(response, dict):
            return []

        suggestions = response.get("skills", [])

        if not isinstance(suggestions, list):
            return []

        # Convert LLM strings into the existing candidate format.
        candidates = []
        seen = set()

        for suggestion in suggestions:
            if not isinstance(suggestion, str):
                continue

            skill_name = suggestion.strip()

            if not skill_name:
                continue

            normalized_name = skill_name.casefold()

            if normalized_name in seen:
                continue

            seen.add(normalized_name)

            candidates.append({
                "skill": skill_name,
                "source_section": "llm_fallback",
                "source_text": resume_text,
                "extraction_method": "llm_fallback",
            })

        if not candidates:
            return []

        # Resolvers must not accidentally erase all candidates.
        resolved = resolve_spelling(candidates)
        if isinstance(resolved, list) and resolved:
            candidates = resolved

        resolved = resolve_synonyms(candidates)
        if isinstance(resolved, list) and resolved:
            candidates = resolved

        # The master validator is authoritative. Do not bypass it.
        validated = validate_skills(candidates)

        if not isinstance(validated, list) or not validated:
            return []

        # Stack expansion should preserve the validated original skills.
        expanded = expand_skill_stacks(validated)

        if not isinstance(expanded, list) or not expanded:
            expanded = validated

        return _deduplicate_final_skills(expanded)

    except Exception:
        # LLM failure must not crash resume parsing.
        return []
    
def extract_skill(
    sections: dict[str, Any],
    profile: bool = False,
) -> list[dict[str, Any]]:
    """
    Extract skills from detected resume sections.

    LLM fallback is used only when the deterministic pipeline
    cannot produce validated skills.
    """

    if not isinstance(sections, dict) or not sections:
        return []

    timings = {}
    total_start = time.perf_counter()

    # Step 1: collect candidates.
    start = time.perf_counter()
    candidates = _collect_candidates(sections, profile=profile)
    timings["collect_candidates"] = time.perf_counter() - start

    logger.debug("Collected %d raw skill candidates", len(candidates))

    # Step 2: raw deduplication.
    start = time.perf_counter()
    candidates = _deduplicate_candidates(candidates)
    timings["raw_deduplication"] = time.perf_counter() - start

    # If no candidates exist, try the LLM fallback.
    if not candidates:
        logger.info("No raw skill candidates; trying LLM fallback")
        fallback_skills = _llm_skill_fallback(sections)

        if profile:
            print(
                f"[SKILL LLM FALLBACK] "
                f"skills={len(fallback_skills)} "
                f"total={time.perf_counter() - total_start:.6f}s"
            )

        return fallback_skills

    # Step 3: spelling resolution.
    start = time.perf_counter()
    candidates = resolve_spelling(candidates)
    timings["spelling_resolution"] = time.perf_counter() - start

    if not candidates:
        logger.info("Spelling resolution returned no candidates")
        return _llm_skill_fallback(sections)

    # Step 4: synonym / alias resolution.
    start = time.perf_counter()
    candidates = resolve_synonyms(candidates)
    timings["synonym_resolution"] = time.perf_counter() - start

    if not candidates:
        logger.info("Synonym resolution returned no candidates")
        return _llm_skill_fallback(sections)

    # Step 5: master skill dictionary validation.
    start = time.perf_counter()
    validated_skills = validate_skills(candidates)
    timings["master_validation"] = time.perf_counter() - start

    if not isinstance(validated_skills, list) or not validated_skills:
        logger.info("No validated skills; trying LLM fallback")
        fallback_skills = _llm_skill_fallback(sections)

        if profile:
            print(
                f"[SKILL LLM FALLBACK] "
                f"skills={len(fallback_skills)} "
                f"total={time.perf_counter() - total_start:.6f}s"
            )

        return fallback_skills

    # Step 6: stack expansion.
    start = time.perf_counter()
    expanded_skills = expand_skill_stacks(validated_skills)
    timings["stack_expansion"] = time.perf_counter() - start

    if not isinstance(expanded_skills, list) or not expanded_skills:
        logger.info("Stack expansion returned no skills")
        return _deduplicate_final_skills(validated_skills)

    # Step 7: final deduplication.
    start = time.perf_counter()
    final_skills = _deduplicate_final_skills(expanded_skills)
    timings["final_deduplication"] = time.perf_counter() - start

    total_time = time.perf_counter() - total_start

    if profile:
        print()
        print("=" * 70)
        print("SKILL EXTRACTION PERFORMANCE")
        print("=" * 70)

        for stage, duration in timings.items():
            print(f"{stage:<30} {duration:.6f} s")

        print("-" * 70)
        print(f"{'TOTAL SKILL EXTRACTION':<30} {total_time:.6f} s")
        print(f"{'RAW CANDIDATES':<30} {len(candidates):>6}")
        print(f"{'VALIDATED SKILLS':<30} {len(validated_skills):>6}")
        print(f"{'EXPANDED SKILLS':<30} {len(expanded_skills):>6}")
        print(f"{'FINAL SKILLS':<30} {len(final_skills):>6}")
        print("=" * 70)

    logger.info(
        "Skill extraction completed: %d final skills",
        len(final_skills),
    )

    return final_skills