"""
spelling_resolver.py

Responsibilities
----------------
1. Correct known skill spelling mistakes.
2. Preserve extraction metadata.
3. Support both:
       - list[str]
       - list[dict]
4. Keep the original skill for traceability.
5. Merge duplicate skills after correction.

This module does NOT:
    - validate skills
    - resolve synonyms
    - perform fuzzy matching
    - expand technology stacks
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]

SPELLING_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "spelling_dictionary.json"
)


# ============================================================
# LOAD SPELLING DICTIONARY
# ============================================================

def load_spelling_dictionary():
    """
    Load the spelling correction dictionary.

    Example:
        {
            "pyhton": "Python",
            "javscript": "JavaScript"
        }
    """

    if not SPELLING_FILE.exists():
        return {}

    with open(SPELLING_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data if isinstance(data, dict) else {}


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(value):
    """
    Normalize text for case-insensitive comparison.
    """

    if not isinstance(value, str):
        return ""

    return " ".join(
        value.strip().lower().split()
    )


# ============================================================
# GET SKILL NAME
# ============================================================

def _get_skill_name(candidate):
    """
    Get the skill name from either:

        "Python"

    or:

        {
            "skill": "Python"
        }
    """

    if isinstance(candidate, str):
        return candidate.strip()

    if isinstance(candidate, dict):
        skill = candidate.get("skill")

        if isinstance(skill, str):
            return skill.strip()

    return ""


# ============================================================
# COPY METADATA
# ============================================================

def _copy_metadata(source, target):
    """
    Preserve extraction/source metadata.
    """

    if not isinstance(source, dict):
        return

    metadata_fields = [
        "source_section",
        "source_sections",
        "source_text",
        "sources",
        "source_skill",
        "extraction_method",
    ]

    for field in metadata_fields:
        if field in source:
            target[field] = source[field]


# ============================================================
# MERGE SOURCE INFORMATION
# ============================================================

def _merge_metadata(existing, candidate):
    """
    Merge source information when two candidates resolve
    to the same skill.
    """

    # --------------------------------------------------------
    # source_sections
    # --------------------------------------------------------

    existing_sections = existing.get(
        "source_sections",
        []
    )

    candidate_sections = candidate.get(
        "source_sections",
        []
    )

    if not isinstance(existing_sections, list):
        existing_sections = [existing_sections]

    if not isinstance(candidate_sections, list):
        candidate_sections = [candidate_sections]

    sections = []

    for section in (
        existing_sections + candidate_sections
    ):
        if section and section not in sections:
            sections.append(section)

    if sections:
        existing["source_sections"] = sections

    # --------------------------------------------------------
    # sources
    # --------------------------------------------------------

    existing_sources = existing.get(
        "sources",
        []
    )

    candidate_sources = candidate.get(
        "sources",
        []
    )

    if not isinstance(existing_sources, list):
        existing_sources = [existing_sources]

    if not isinstance(candidate_sources, list):
        candidate_sources = [candidate_sources]

    sources = existing_sources + candidate_sources

    if sources:
        existing["sources"] = sources

    # --------------------------------------------------------
    # source_text
    # --------------------------------------------------------

    if not existing.get("source_text"):
        existing["source_text"] = candidate.get(
            "source_text",
            ""
        )


# ============================================================
# RESOLVE SPELLING
# ============================================================

def resolve_spelling(candidate_skills):
    """
    Resolve known spelling mistakes.

    Supports:

        list[str]

    and:

        list[dict]

    Example input:

        {
            "skill": "pyhton",
            "source_section": "experience",
            "source_text": "Worked with pyhton and Django"
        }

    Example output:

        {
            "skill": "Python",
            "original_skill": "pyhton",
            "resolution_method": "spelling",
            "source_section": "experience",
            "source_text": "Worked with pyhton and Django"
        }
    """

    if not isinstance(candidate_skills, list):
        return []

    if not candidate_skills:
        return []

    spelling_dictionary = load_spelling_dictionary()

    lookup = {
        _normalize(wrong): correct.strip()
        for wrong, correct in spelling_dictionary.items()
        if isinstance(wrong, str)
        and isinstance(correct, str)
        and wrong.strip()
        and correct.strip()
    }

    resolved = []
    seen = {}

    for candidate in candidate_skills:

        original_skill = _get_skill_name(candidate)

        if not original_skill:
            continue

        normalized_original = _normalize(
            original_skill
        )

        corrected_skill = lookup.get(
            normalized_original,
            original_skill
        )

        corrected_skill = corrected_skill.strip()

        # ----------------------------------------------------
        # STRING INPUT
        # ----------------------------------------------------

        if isinstance(candidate, str):

            result = {
                "skill": corrected_skill
            }

            if normalized_original != _normalize(
                corrected_skill
            ):
                result["original_skill"] = (
                    original_skill
                )
                result["resolution_method"] = (
                    "spelling"
                )

        # ----------------------------------------------------
        # DICT INPUT
        # ----------------------------------------------------

        else:

            result = dict(candidate)

            result["skill"] = corrected_skill

            if normalized_original != _normalize(
                corrected_skill
            ):
                result["original_skill"] = (
                    original_skill
                )
                result["resolution_method"] = (
                    "spelling"
                )

        # ----------------------------------------------------
        # DEDUPLICATION
        # ----------------------------------------------------

        key = _normalize(corrected_skill)

        if key in seen:

            existing = seen[key]

            if isinstance(candidate, dict):
                _merge_metadata(
                    existing,
                    candidate
                )

            continue

        seen[key] = result
        resolved.append(result)

    return resolved