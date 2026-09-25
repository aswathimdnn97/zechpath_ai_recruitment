"""
synonym_resolver.py

Responsibilities
----------------
1. Convert skill aliases into canonical skill names.
2. Preserve extraction metadata.
3. Support list[str] and list[dict].
4. Merge duplicate candidates.

This module does NOT:
    - validate skills
    - perform fuzzy matching
    - expand technology stacks
"""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]

ALIAS_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "skill_aliases.json"
)


# ============================================================
# LOAD ALIASES
# ============================================================

def load_skill_aliases():
    """
    Load skill alias dictionary.

    Example:

        {
            "js": "JavaScript",
            "reactjs": "React",
            "nodejs": "Node.js"
        }
    """

    if not ALIAS_FILE.exists():
        return {}

    with open(ALIAS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data if isinstance(data, dict) else {}


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(value):
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
    Extract skill name from supported input formats.

    Supports:

        "Python"

        {
            "skill": "Python"
        }

        {
            "name": "Python"
        }

        {
            "canonical_name": "Python"
        }
    """

    if isinstance(candidate, str):
        return candidate.strip()

    if isinstance(candidate, dict):

        skill = (
            candidate.get("skill")
            or candidate.get("name")
            or candidate.get("canonical_name")
        )

        if isinstance(skill, str):
            return skill.strip()

    return ""

# ============================================================
# MERGE METADATA
# ============================================================

def _merge_metadata(existing, candidate):

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
# RESOLVE SYNONYMS
# ============================================================

def resolve_synonyms(candidate_skills):
    """
    Convert aliases into canonical skill names.

    Example:

        {
            "skill": "reactjs",
            "source_section": "experience"
        }

    becomes:

        {
            "skill": "React",
            "original_skill": "reactjs",
            "resolution_method": "synonym",
            "source_section": "experience"
        }
    """

    if not isinstance(candidate_skills, list):
        return []

    if not candidate_skills:
        return []

    aliases = load_skill_aliases()

    lookup = {
        _normalize(alias): canonical.strip()
        for alias, canonical in aliases.items()
        if isinstance(alias, str)
        and isinstance(canonical, str)
        and alias.strip()
        and canonical.strip()
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

        canonical_skill = lookup.get(
            normalized_original,
            original_skill
        )

        canonical_skill = canonical_skill.strip()

        # ----------------------------------------------------
        # STRING INPUT
        # ----------------------------------------------------

        if isinstance(candidate, str):

            result = {
                "skill": canonical_skill
            }

        # ----------------------------------------------------
        # DICT INPUT
        # ----------------------------------------------------

        else:

            result = dict(candidate)

            result["skill"] = canonical_skill

        # ----------------------------------------------------
        # RECORD SYNONYM TRANSFORMATION
        # ----------------------------------------------------

        if normalized_original != _normalize(
            canonical_skill
        ):

            if "original_skill" not in result:
                result["original_skill"] = (
                    original_skill
                )

            result["resolved_from"] = (
                original_skill
            )

            result["resolution_method"] = (
                "synonym"
            )

        # ----------------------------------------------------
        # DEDUPLICATION
        # ----------------------------------------------------

        key = _normalize(canonical_skill)

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