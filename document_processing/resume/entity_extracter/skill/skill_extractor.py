"""
skill_extractor.py

Central skill extraction orchestrator.

Responsibilities
----------------
1. Collect skill candidates from multiple resume sections.
2. Use skill_list_splitter.py for dedicated Skills sections.
3. Use skill_extractor_from_section.py for prose sections.
4. Preserve source/evidence metadata.
5. Resolve spelling.
6. Resolve synonyms / aliases.
7. Validate against the master skill dictionary.
8. Expand technology stacks.
9. Deduplicate final skills.

Pipeline
--------
Resume sections
        ↓
Collect candidates
        ↓
Raw candidate deduplication
        ↓
Spelling resolver
        ↓
Synonym resolver
        ↓
Master skill validator
        ↓
Stack resolver
        ↓
Final deduplication
        ↓
Final validated skills
"""

from __future__ import annotations

import logging
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

import time


# ============================================================
# LOGGER
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# SECTIONS FROM WHICH TECHNICAL SKILLS CAN BE EXTRACTED
# ============================================================

SKILL_SOURCE_SECTIONS = {
    "skills",
    "summary",
    "experience",
    "projects",
}


# ============================================================
# SECTIONS THAT SHOULD NOT BE USED FOR TECHNICAL SKILLS
# ============================================================

IGNORED_SECTIONS = {
    "personal_information",
    "languages",
    "interests",
    "references",
    "declaration",
}


# ============================================================
# FLATTEN SECTION DATA
# ============================================================

def _flatten_section(value):
    """
    Recursively flatten nested resume section data.

    Supports:
        str
        dict
        list
        tuple
        nested combinations
    """

    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()

        return [value] if value else []

    if isinstance(value, dict):
        result = []

        for nested_value in value.values():
            result.extend(
                _flatten_section(nested_value)
            )

        return result

    if isinstance(value, (list, tuple)):
        result = []

        for item in value:
            result.extend(
                _flatten_section(item)
            )

        return result

    return [str(value)]


# ============================================================
# NORMALIZE TEXT
# ============================================================

def _normalize(value: Any) -> str:
    """
    Normalize a value for case-insensitive comparison.
    """

    if not isinstance(value, str):
        return ""

    return " ".join(
        value.strip().lower().split()
    )


# ============================================================
# NORMALIZE SECTION NAME
# ============================================================

def _normalize_section_name(
    section_name: Any,
) -> str:
    """
    Normalize resume section names.
    """

    if not isinstance(section_name, str):
        return ""

    return " ".join(
        section_name.strip().lower().split()
    )


# ============================================================
# SOURCE HELPERS
# ============================================================

def _source_key(source: Any) -> str:
    """
    Create a stable key for source deduplication.

    Preferred source format:

        {
            "source_section": "experience",
            "source_text": "...",
            "source_skill": "Python"
        }
    """

    if isinstance(source, dict):

        return "|".join(
            [
                str(
                    source.get(
                        "source_section",
                        "",
                    )
                ).strip(),

                str(
                    source.get(
                        "source_text",
                        "",
                    )
                ).strip(),

                str(
                    source.get(
                        "source_skill",
                        "",
                    )
                ).strip(),
            ]
        ).lower()

    return str(source).strip().lower()


def _merge_sources(
    existing: Any,
    incoming: Any,
) -> list[Any]:
    """
    Merge source evidence without duplicates.

    Supports both the new structured source format
    and legacy string sources.
    """

    if not isinstance(existing, list):
        existing = (
            [existing]
            if existing
            else []
        )

    if not isinstance(incoming, list):
        incoming = (
            [incoming]
            if incoming
            else []
        )

    merged: list[Any] = []
    seen: set[str] = set()

    for source in (
        existing + incoming
    ):

        key = _source_key(source)

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        merged.append(source)

    return merged


# ============================================================
# MERGE SOURCE METADATA
# ============================================================

def _merge_source_metadata(
    existing: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    """
    Merge source/evidence metadata.

    This function is mainly used by the orchestrator's
    initial/final deduplication.

    The canonical source format is:

        sources: [
            {
                "source_section": "...",
                "source_text": "...",
                "source_skill": "..."
            }
        ]
    """

    if not isinstance(existing, dict):
        return

    if not isinstance(candidate, dict):
        return

    # --------------------------------------------------------
    # SOURCE SECTION
    # --------------------------------------------------------

    sections: list[str] = []

    for item in (
        existing,
        candidate,
    ):

        value = item.get(
            "source_sections",
            [],
        )

        if isinstance(value, str):
            value = [value]

        if isinstance(value, list):
            sections.extend(value)

        source_section = item.get(
            "source_section"
        )

        if source_section:
            sections.append(
                source_section
            )

    # Preserve order while removing duplicates.
    existing["source_sections"] = list(
        dict.fromkeys(
            str(section).strip()
            for section in sections
            if str(section).strip()
        )
    )

    # --------------------------------------------------------
    # SOURCE TEXT
    # --------------------------------------------------------

    existing_text = existing.get(
        "source_text"
    )

    candidate_text = candidate.get(
        "source_text"
    )

    if not existing_text and candidate_text:
        existing["source_text"] = (
            candidate_text
        )

    # --------------------------------------------------------
    # SOURCES
    # --------------------------------------------------------

    existing_sources = existing.get(
        "sources",
        [],
    )

    candidate_sources = candidate.get(
        "sources",
        [],
    )

    # If sources don't exist yet, construct structured
    # evidence from the candidate metadata.

    if not existing_sources:

        existing_sources = []

        if existing.get(
            "source_section"
        ) or existing.get(
            "source_text"
        ):

            existing_sources.append(
                {
                    "source_section": existing.get(
                        "source_section"
                    ),
                    "source_text": existing.get(
                        "source_text"
                    ),
                    "source_skill": existing.get(
                        "skill"
                    ),
                }
            )

    if not candidate_sources:

        candidate_sources = []

        if candidate.get(
            "source_section"
        ) or candidate.get(
            "source_text"
        ):

            candidate_sources.append(
                {
                    "source_section": candidate.get(
                        "source_section"
                    ),
                    "source_text": candidate.get(
                        "source_text"
                    ),
                    "source_skill": candidate.get(
                        "skill"
                    ),
                }
            )

    existing["sources"] = _merge_sources(
        existing_sources,
        candidate_sources,
    )


# ============================================================
# COLLECT SKILL CANDIDATES
# ============================================================

def _collect_candidates(
    sections: dict[str, Any],
    profile: bool = False,
) -> list[dict[str, Any]]:
    """
    Collect raw skill candidates from all relevant sections.

    Performance profiling:
        - Section-level timing
        - Fragment-level timing
        - Skills splitter timing

    Important:
        Each text fragment is passed individually to
        extract_skills_from_section() to avoid repeatedly
        processing the entire section.
    """

    candidates: list[dict[str, Any]] = []

    if not isinstance(sections, dict):
        return candidates

    # ========================================================
    # TOTAL COLLECT CANDIDATES TIMER
    # ========================================================

    collect_start = time.perf_counter() if profile else 0.0

    # ========================================================
    # PROCESS EACH SECTION
    # ========================================================

    for raw_section_name, section_block in sections.items():

        # ----------------------------------------------------
        # Normalize section name
        # ----------------------------------------------------

        section_name = _normalize_section_name(
            raw_section_name
        )

        if not section_name:
            continue

        # ----------------------------------------------------
        # Ignore excluded sections
        # ----------------------------------------------------

        if section_name in IGNORED_SECTIONS:
            continue

        # ----------------------------------------------------
        # Only configured skill source sections
        # ----------------------------------------------------

        if section_name not in SKILL_SOURCE_SECTIONS:
            continue

        # ====================================================
        # SECTION TIMER
        # ====================================================

        section_start = time.perf_counter() if profile else 0.0
        section_candidate_count_before = (
            len(candidates)
            if profile
            else 0
        )

        # ====================================================
        # DEDICATED SKILLS SECTION
        # ====================================================

        if section_name == "skills":

            flatten_start = (
                time.perf_counter()
                if profile
                else 0.0
            )

            lines = _flatten_section(
                section_block
            )

            flatten_duration = (
                time.perf_counter() - flatten_start
                if profile
                else 0.0
            )

            # ------------------------------------------------
            # Skill splitter timing
            # ------------------------------------------------

            splitter_start = (
                time.perf_counter()
                if profile
                else 0.0
            )

            raw_skills = split_skill_line(lines)

            splitter_duration = (
                time.perf_counter() - splitter_start
                if profile
                else 0.0
            )

            if profile:
                print(
                    f"[SKILL SPLITTER] "
                    f"time={splitter_duration:.6f}s "
                    f"lines={len(lines)} "
                    f"skills={len(raw_skills) if isinstance(raw_skills, list) else 0}"
                )

            if not isinstance(raw_skills, list):
                if profile:
                    print(
                        f"[SKILL SECTION] "
                        f"section={section_name:<12} "
                        f"time={time.perf_counter() - section_start:.6f}s "
                        f"fragments={len(lines)} "
                        f"candidates=0"
                    )
                continue

            for skill in raw_skills:

                if not isinstance(skill, str):
                    continue

                skill = skill.strip()

                if not skill:
                    continue

                candidates.append(
                    {
                        "skill": skill,
                        "source_section": "skills",
                        "source_text": skill,
                        "extraction_method": (
                            "skills_section"
                        ),
                        "sources": [
                            {
                                "source_section": "skills",
                                "source_text": skill,
                                "source_skill": skill,
                            }
                        ],
                    }
                )

            if profile:
                section_duration = (
                    time.perf_counter()
                    - section_start
                )

                section_candidate_count = (
                    len(candidates)
                    - section_candidate_count_before
                )

                print(
                    f"[SKILL SECTION] "
                    f"section={section_name:<12} "
                    f"time={section_duration:.6f}s "
                    f"flatten={flatten_duration:.6f}s "
                    f"splitter={splitter_duration:.6f}s "
                    f"fragments={len(lines)} "
                    f"candidates={section_candidate_count}"
                )

            continue

        # ====================================================
        # PROSE / STRUCTURED SECTIONS
        # ====================================================

        flatten_start = time.perf_counter() if profile else 0.0

        text_fragments = _flatten_section(
            section_block
        )

        flatten_duration = (
            time.perf_counter() - flatten_start
            if profile
            else 0.0
        )

        if not text_fragments:
            if profile:
                print(
                    f"[SKILL SECTION] "
                    f"section={section_name:<12} "
                    f"time={time.perf_counter() - section_start:.6f}s "
                    f"flatten={flatten_duration:.6f}s "
                    f"fragments=0 "
                    f"candidates=0"
                )
            continue

        # ----------------------------------------------------
        # Fragment counters
        # ----------------------------------------------------

        fragment_count = 0
        extraction_time_total = 0.0

        # ====================================================
        # PROCESS EACH FRAGMENT
        # ====================================================

        for source_text in text_fragments:

            if not isinstance(
                source_text,
                str,
            ):
                continue

            source_text = source_text.strip()

            if not source_text:
                continue

            fragment_count += 1

            # ------------------------------------------------
            # Extract skills from THIS fragment only
            # ------------------------------------------------

            fragment_start = (
                time.perf_counter()
                if profile
                else 0.0
            )

            section_candidates = extract_skills_from_section(
                section_name=section_name,
                section_block=source_text,
            )

            if profile:
                extraction_time_total += (
                    time.perf_counter()
                    - fragment_start
                )

            if not isinstance(
                section_candidates,
                list,
            ):
                continue

            # ------------------------------------------------
            # Normalize each candidate
            # ------------------------------------------------

            for candidate in section_candidates:

                if not isinstance(
                    candidate,
                    dict,
                ):
                    continue

                skill = candidate.get(
                    "skill"
                )

                if not isinstance(
                    skill,
                    str,
                ):
                    continue

                skill = skill.strip()

                if not skill:
                    continue

                candidate["skill"] = skill

                # --------------------------------------------
                # Preserve parent section
                # --------------------------------------------

                candidate["source_section"] = (
                    section_name
                )

                # --------------------------------------------
                # Preserve source text
                # --------------------------------------------

                candidate["source_text"] = (
                    candidate.get("source_text")
                    or source_text
                )

                candidate.setdefault(
                    "extraction_method",
                    "section_text",
                )

                # --------------------------------------------
                # Structured source evidence
                # --------------------------------------------

                existing_sources = candidate.get(
                    "sources"
                )

                if not isinstance(
                    existing_sources,
                    list,
                ):
                    existing_sources = []

                if not existing_sources:

                    existing_sources = [
                        {
                            "source_section": (
                                section_name
                            ),
                            "source_text": (
                                source_text
                            ),
                            "source_skill": skill,
                        }
                    ]

                candidate["sources"] = (
                    existing_sources
                )

                candidates.append(
                    candidate
                )

        # ====================================================
        # SECTION PROFILING
        # ====================================================

        if profile:
            section_duration = (
                time.perf_counter()
                - section_start
            )

            section_candidate_count = (
                len(candidates)
                - section_candidate_count_before
            )

            print(
                f"[SKILL SECTION] "
                f"section={section_name:<12} "
                f"time={section_duration:.6f}s "
                f"flatten={flatten_duration:.6f}s "
                f"extract={extraction_time_total:.6f}s "
                f"fragments={fragment_count} "
                f"candidates={section_candidate_count}"
            )

    # ========================================================
    # TOTAL PROFILING
    # ========================================================

    if profile:
        collect_duration = (
            time.perf_counter()
            - collect_start
        )

        print(
            f"[SKILL COLLECT] "
            f"total={collect_duration:.6f}s "
            f"candidates={len(candidates)}"
        )

    return candidates

# ============================================================
# DEDUPLICATE CANDIDATES
# ============================================================

def _deduplicate_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Deduplicate raw candidates by normalized skill name.

    Source/evidence metadata is merged.

    Example:

        Python
        python
        PYTHON

    becomes one candidate while retaining evidence from
    all occurrences.
    """

    if not isinstance(
        candidates,
        list,
    ):
        return []

    unique: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}

    for candidate in candidates:

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        skill = candidate.get(
            "skill"
        )

        if not isinstance(
            skill,
            str,
        ):
            continue

        skill = skill.strip()

        if not skill:
            continue

        candidate["skill"] = skill

        key = _normalize(skill)

        if not key:
            continue

        # ----------------------------------------------------
        # Existing candidate
        # ----------------------------------------------------

        if key in seen:

            _merge_source_metadata(
                seen[key],
                candidate,
            )

            continue

        # ----------------------------------------------------
        # First occurrence
        # ----------------------------------------------------

        # Make sure the first candidate also has
        # structured source evidence.

        if not candidate.get(
            "sources"
        ):

            candidate["sources"] = [
                {
                    "source_section": (
                        candidate.get(
                            "source_section"
                        )
                    ),
                    "source_text": (
                        candidate.get(
                            "source_text",
                            "",
                        )
                    ),
                    "source_skill": skill,
                }
            ]

        seen[key] = candidate
        unique.append(candidate)

    return unique


# ============================================================
# FINAL SKILL DEDUPLICATION
# ============================================================

def _deduplicate_final_skills(
    skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Deduplicate final validated/expanded skills.

    A skill can be identified by:

        1. skill_id
        2. normalized skill name

    Both indexes are checked independently.

    This is important because stack expansion may produce
    a skill that already exists as a directly extracted skill.
    """

    if not isinstance(
        skills,
        list,
    ):
        return []

    final: list[dict[str, Any]] = []

    seen_ids: dict[Any, dict[str, Any]] = {}
    seen_names: dict[str, dict[str, Any]] = {}

    for skill in skills:

        if not isinstance(
            skill,
            dict,
        ):
            continue

        skill_id = skill.get(
            "skill_id"
        )

        skill_name = skill.get(
            "skill"
        )

        normalized_name = (
            _normalize(skill_name)
            if skill_name
            else ""
        )

        # ----------------------------------------------------
        # Find existing skill
        # ----------------------------------------------------

        existing = None

        if skill_id is not None:
            existing = seen_ids.get(
                skill_id
            )

        if existing is None and normalized_name:
            existing = seen_names.get(
                normalized_name
            )

        # ----------------------------------------------------
        # Duplicate
        # ----------------------------------------------------

        if existing is not None:

            _merge_source_metadata(
                existing,
                skill,
            )

            # ------------------------------------------------
            # Preserve stack source information
            # ------------------------------------------------

            source_skills = []

            for item in (
                existing,
                skill,
            ):

                value = item.get(
                    "source_skills",
                    [],
                )

                if isinstance(
                    value,
                    str,
                ):
                    value = [value]

                if isinstance(
                    value,
                    list,
                ):
                    source_skills.extend(
                        value
                    )

                source_skill = item.get(
                    "source_skill"
                )

                if source_skill:
                    source_skills.append(
                        source_skill
                    )

            if source_skills:

                existing["source_skills"] = list(
                    dict.fromkeys(
                        str(value).strip()
                        for value in source_skills
                        if str(value).strip()
                    )
                )

            continue

        # ----------------------------------------------------
        # New skill
        # ----------------------------------------------------

        final.append(
            skill
        )

        if skill_id is not None:
            seen_ids[skill_id] = skill

        if normalized_name:
            seen_names[
                normalized_name
            ] = skill

    return final


# ============================================================
# MAIN SKILL EXTRACTION FUNCTION
# ============================================================

def extract_skill(
    sections: dict[str, Any],
    profile: bool = False,
) -> list[dict[str, Any]]:
    """
    Extract and normalize skills from the complete
    section-detected resume.

    profile=True prints timing information for each
    internal skill-extraction stage.
    """

    if not isinstance(sections, dict):
        return []

    if not sections:
        return []

    timings = {}
    total_start = time.perf_counter()

    # ========================================================
    # STEP 1 — COLLECT CANDIDATES
    # ========================================================

    start = time.perf_counter()

    candidates = _collect_candidates(
        sections,
        profile=profile,
    )

    timings["collect_candidates"] = time.perf_counter() - start

    logger.debug(
        "Skill extraction: collected %d raw candidates",
        len(candidates),
    )

    if not candidates:
        return []

    # ========================================================
    # STEP 2 — RAW CANDIDATE DEDUPLICATION
    # ========================================================

    start = time.perf_counter()

    candidates = _deduplicate_candidates(candidates)

    timings["raw_deduplication"] = time.perf_counter() - start

    logger.debug(
        "Skill extraction: %d candidates after raw deduplication",
        len(candidates),
    )

    if not candidates:
        return []

    # ========================================================
    # STEP 3 — SPELLING RESOLUTION
    # ========================================================

    start = time.perf_counter()

    candidates = resolve_spelling(candidates)

    timings["spelling_resolution"] = time.perf_counter() - start

    logger.debug(
        "Skill extraction: %d candidates after spelling resolution",
        len(candidates),
    )

    if not candidates:
        return []

    # ========================================================
    # STEP 4 — SYNONYM / ALIAS RESOLUTION
    # ========================================================

    start = time.perf_counter()

    candidates = resolve_synonyms(candidates)

    timings["synonym_resolution"] = time.perf_counter() - start

    logger.debug(
        "Skill extraction: %d candidates after synonym resolution",
        len(candidates),
    )

    if not candidates:
        return []

    # ========================================================
    # STEP 5 — MASTER SKILL VALIDATION
    # ========================================================

    start = time.perf_counter()

    validated_skills = validate_skills(candidates)

    timings["master_validation"] = time.perf_counter() - start

    logger.debug(
        "Skill extraction: %d skills after master validation",
        len(validated_skills),
    )

    if not validated_skills:
        return []

    # ========================================================
    # STEP 6 — STACK EXPANSION
    # ========================================================

    start = time.perf_counter()

    expanded_skills = expand_skill_stacks(validated_skills)

    timings["stack_expansion"] = time.perf_counter() - start

    logger.debug(
        "Skill extraction: %d skills after stack expansion",
        len(expanded_skills),
    )

    if not expanded_skills:
        return []

    # ========================================================
    # STEP 7 — FINAL DEDUPLICATION
    # ========================================================

    start = time.perf_counter()

    final_skills = _deduplicate_final_skills(expanded_skills)

    timings["final_deduplication"] = time.perf_counter() - start

    total_time = time.perf_counter() - total_start

    # ========================================================
    # PROFILING OUTPUT
    # ========================================================

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