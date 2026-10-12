"""
spelling_resolver.py

Responsibilities
----------------
1. Correct known skill spelling mistakes.
2. Preserve extraction/source metadata.
3. Support both:
       - list[str]
       - list[dict]
4. Deduplicate skills after spelling resolution.
5. Merge source evidence when the same canonical skill
   appears multiple times.

This module DOES NOT:
    - perform synonym resolution
    - perform fuzzy master validation
    - expand skill stacks

Pipeline position
-----------------
    skill_extractor
          ↓
    spelling_resolver
          ↓
    synonym_resolver
          ↓
    master_skill_validator
          ↓
    stack_resolver
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

SKILL_DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
)

SPELLING_FILE = (
    SKILL_DATA_DIR
    / "spelling_dictionary.json"
)


# ============================================================
# JSON LOADER
# ============================================================

def _load_json(path: Path) -> Any:
    """
    Load JSON data from a file.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Spelling dictionary not found: {path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in spelling dictionary: {path}"
        ) from exc


# ============================================================
# LOAD SPELLING DICTIONARY
# ============================================================

SPELLING_DICTIONARY = _load_json(
    SPELLING_FILE
)


if not isinstance(SPELLING_DICTIONARY, dict):
    raise ValueError(
        "spelling_dictionary.json must contain a JSON object."
    )


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(value: Any) -> str:
    """
    Normalize text for dictionary lookup.

    Examples
    --------
    ' Pyhton ' -> 'pyhton'
    'PYHTON'   -> 'pyhton'
    'Fast  API' -> 'fast api'
    """

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


# ============================================================
# BUILD NORMALIZED SPELLING MAP
# ============================================================

NORMALIZED_SPELLING_MAP = {
    _normalize(wrong): str(correct).strip()
    for wrong, correct in SPELLING_DICTIONARY.items()
    if _normalize(wrong)
    and correct is not None
    and str(correct).strip()
}


# ============================================================
# SKILL NAME EXTRACTION
# ============================================================

def _get_skill_name(candidate: Any) -> str:
    """
    Extract skill name from supported candidate formats.

    Supported:

        "pyhton"

        {
            "skill": "pyhton"
        }

        {
            "name": "pyhton"
        }

        {
            "canonical_name": "pyhton"
        }
    """

    if isinstance(candidate, str):
        return candidate.strip()

    if not isinstance(candidate, dict):
        return ""

    for key in (
        "skill",
        "name",
        "canonical_name",
    ):
        value = candidate.get(key)

        if value is not None:
            value = str(value).strip()

            if value:
                return value

    return ""


# ============================================================
# SOURCE KEY
# ============================================================

def _source_key(source: Any) -> tuple:
    """
    Create a stable key for source deduplication.
    """

    if not isinstance(source, dict):
        return (str(source),)

    return (
        source.get("source_section", ""),
        source.get("source_text", ""),
        source.get("source_skill", ""),
    )


# ============================================================
# MERGE SOURCES
# ============================================================

def _merge_sources(
    existing: list[dict],
    incoming: list[dict],
) -> list[dict]:
    """
    Merge source evidence without duplicates.
    """

    merged = []

    seen = set()

    for source in [
        *existing,
        *incoming,
    ]:

        if not isinstance(source, dict):
            continue

        key = _source_key(source)

        if key in seen:
            continue

        seen.add(key)
        merged.append(source)

    return merged


# ============================================================
# MERGE METADATA
# ============================================================

def _merge_metadata(
    existing: dict,
    incoming: dict,
) -> dict:
    """
    Merge extraction metadata.

    Existing values are preserved while new evidence
    is added.
    """

    result = dict(existing)

    # --------------------------------------------------------
    # SOURCES
    # --------------------------------------------------------

    existing_sources = result.get(
        "sources",
        [],
    )

    incoming_sources = incoming.get(
        "sources",
        [],
    )

    if not isinstance(existing_sources, list):
        existing_sources = []

    if not isinstance(incoming_sources, list):
        incoming_sources = []

    result["sources"] = _merge_sources(
        existing_sources,
        incoming_sources,
    )

    # --------------------------------------------------------
    # SOURCE SECTIONS
    # --------------------------------------------------------

    source_sections = []

    for item in [
        *result.get("source_sections", []),
        *incoming.get("source_sections", []),
    ]:

        if item and item not in source_sections:
            source_sections.append(item)

    # Also derive source sections from sources.
    for source in result["sources"]:

        section = source.get("source_section")

        if section and section not in source_sections:
            source_sections.append(section)

    if source_sections:
        result["source_sections"] = source_sections

    # --------------------------------------------------------
    # ORIGINAL SKILLS
    # --------------------------------------------------------

    original_skills = []

    for item in [
        *result.get("original_skills", []),
        *incoming.get("original_skills", []),
    ]:

        if item and item not in original_skills:
            original_skills.append(item)

    if original_skills:
        result["original_skills"] = original_skills

    # --------------------------------------------------------
    # SOURCE TEXT
    # --------------------------------------------------------

    source_texts = []

    for item in [
        result.get("source_text"),
        incoming.get("source_text"),
    ]:

        if item and item not in source_texts:
            source_texts.append(item)

    if source_texts:
        result["source_text"] = " ".join(
            source_texts
        )

    return result


# ============================================================
# SPELLING RESOLUTION
# ============================================================

def _resolve_spelling(
    skill_name: str,
) -> str:
    """
    Resolve a skill using exact normalized spelling lookup.

    No fuzzy matching is performed here.
    """

    normalized = _normalize(skill_name)

    if not normalized:
        return skill_name

    resolved = NORMALIZED_SPELLING_MAP.get(
        normalized
    )

    if resolved:
        return resolved

    return skill_name


# ============================================================
# RESOLVE SINGLE SKILL
# ============================================================

def resolve_skill(
    candidate: Any,
) -> dict | None:
    """
    Resolve spelling for one candidate.

    Returns
    -------
    dict | None

    Example
    -------
    Input:

        {
            "skill": "pyhton",
            "sources": [...]
        }

    Output:

        {
            "skill": "Python",
            "original_skill": "pyhton",
            "resolved_from": "pyhton",
            "resolution_method": "spelling",
            "original_skills": ["pyhton"],
            "sources": [...]
        }
    """

    # --------------------------------------------------------
    # STRING CANDIDATE
    # --------------------------------------------------------

    if isinstance(candidate, str):

        skill_name = candidate.strip()

        if not skill_name:
            return None

        resolved = _resolve_spelling(
            skill_name
        )

        result = {
            "skill": resolved,
        }

        if _normalize(resolved) != _normalize(skill_name):

            result.update(
                {
                    "original_skill": skill_name,
                    "resolved_from": skill_name,
                    "resolution_method": "spelling",
                    "original_skills": [
                        skill_name
                    ],
                }
            )

        return result

    # --------------------------------------------------------
    # DICT CANDIDATE
    # --------------------------------------------------------

    if not isinstance(candidate, dict):
        return None

    skill_name = _get_skill_name(candidate)

    if not skill_name:
        return None

    result = dict(candidate)

    resolved = _resolve_spelling(
        skill_name
    )

    # --------------------------------------------------------
    # SPELLING CHANGED
    # --------------------------------------------------------

    if _normalize(resolved) != _normalize(skill_name):

        result["skill"] = resolved

        # Preserve first original value.
        if not result.get("original_skill"):
            result["original_skill"] = skill_name

        result["resolved_from"] = skill_name

        result["resolution_method"] = "spelling"

        existing_originals = result.get(
            "original_skills",
            [],
        )

        if not isinstance(existing_originals, list):
            existing_originals = []

        if skill_name not in existing_originals:
            existing_originals.append(
                skill_name
            )

        result["original_skills"] = (
            existing_originals
        )

    else:

        result["skill"] = resolved

        # Keep existing metadata intact.

    return result


# ============================================================
# RESOLVE LIST OF SKILLS
# ============================================================

def resolve_spelling(
    candidates: list[Any],
) -> list[dict]:
    """
    Resolve spelling for all candidates.

    Important:
        Deduplication is performed AFTER spelling resolution.

    This means:

        pyhton
        Python

    become:

        Python

    and their source metadata is merged.
    """

    if not candidates:
        return []

    resolved_skills: dict[str, dict] = {}

    for candidate in candidates:

        result = resolve_skill(
            candidate
        )

        if not result:
            continue

        skill_name = _get_skill_name(
            result
        )

        if not skill_name:
            continue

        canonical_key = _normalize(
            skill_name
        )

        if not canonical_key:
            continue

        # ----------------------------------------------------
        # FIRST OCCURRENCE
        # ----------------------------------------------------

        if canonical_key not in resolved_skills:

            resolved_skills[
                canonical_key
            ] = result

            continue

        # ----------------------------------------------------
        # DUPLICATE AFTER SPELLING
        # ----------------------------------------------------

        existing = resolved_skills[
            canonical_key
        ]

        resolved_skills[
            canonical_key
        ] = _merge_metadata(
            existing,
            result,
        )

    return list(
        resolved_skills.values()
    )


# ============================================================
# BACKWARD-COMPATIBILITY ALIAS
# ============================================================

resolve_skills = resolve_spelling


# ============================================================
# DEBUG / MANUAL TEST
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s",
    )

    test_candidates = [
        {
            "skill": "pyhton",
            "source_section": "skills",
            "source_text": "pyhton, Django",
            "sources": [
                {
                    "source_section": "skills",
                    "source_text": "pyhton, Django",
                    "source_skill": "pyhton",
                }
            ],
        },
        {
            "skill": "Python",
            "source_section": "experience",
            "source_text": (
                "Developed applications using Python"
            ),
            "sources": [
                {
                    "source_section": "experience",
                    "source_text": (
                        "Developed applications using Python"
                    ),
                    "source_skill": "Python",
                }
            ],
        },
    ]

    result = resolve_spelling(
        test_candidates
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )