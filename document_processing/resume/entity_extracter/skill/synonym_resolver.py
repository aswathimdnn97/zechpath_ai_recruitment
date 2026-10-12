"""
synonym_resolver.py

Responsibilities
----------------
1. Resolve skill aliases/synonyms.
2. Convert aliases to canonical skill names.
3. Preserve extraction metadata.
4. Merge duplicate canonical skills.
5. Do NOT perform fuzzy matching.
6. Do NOT expand skill stacks.

Pipeline position
-----------------
Spelling Resolver
        ↓
Synonym Resolver
        ↓
Master Skill Validator
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[4]

ALIAS_DICTIONARY_PATH = (
    BASE_DIR
    / "data"
    / "resume"
    / "skills"
    / "skill_aliases.json"
)


# ============================================================
# JSON LOADER
# ============================================================

def _load_json(path: Path) -> dict[str, Any]:
    """
    Load alias dictionary.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Skill alias dictionary not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "skill_aliases.json must contain a JSON object."
        )

    return data


ALIAS_DICTIONARY = _load_json(
    ALIAS_DICTIONARY_PATH
)


# ============================================================
# HELPERS
# ============================================================

def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def _get_skill_name(candidate: dict[str, Any]) -> str:
    return str(
        candidate.get("skill")
        or candidate.get("name")
        or candidate.get("canonical_name")
        or ""
    ).strip()


# ============================================================
# ALIAS LOOKUP
# ============================================================

def _build_normalized_alias_map(
    aliases: dict[str, Any],
) -> dict[str, str]:
    """
    Normalize alias keys once.
    """

    normalized: dict[str, str] = {}

    for alias, canonical in aliases.items():

        if not isinstance(alias, str):
            continue

        if not isinstance(canonical, str):
            continue

        alias_key = _normalize_text(alias)
        canonical_name = canonical.strip()

        if alias_key and canonical_name:
            normalized[alias_key] = canonical_name

    return normalized


ALIAS_MAP = _build_normalized_alias_map(
    ALIAS_DICTIONARY
)


# ============================================================
# SOURCE MERGING
# ============================================================

def _source_key(source: Any) -> str:

    if isinstance(source, dict):
        return "|".join(
            [
                str(source.get("source_section", "")).strip(),
                str(source.get("source_text", "")).strip(),
                str(source.get("source_skill", "")).strip(),
            ]
        ).lower()

    return str(source).strip().lower()


def _merge_sources(
    existing: list[Any] | None,
    incoming: list[Any] | None,
) -> list[Any]:

    merged: list[Any] = []
    seen: set[str] = set()

    for source in (existing or []) + (incoming or []):

        key = _source_key(source)

        if not key or key in seen:
            continue

        seen.add(key)
        merged.append(source)

    return merged


# ============================================================
# METADATA MERGING
# ============================================================

def _merge_metadata(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> None:

    existing["sources"] = _merge_sources(
        existing.get("sources"),
        incoming.get("sources"),
    )

    # --------------------------------------------------------
    # Source sections
    # --------------------------------------------------------

    sections = []

    for candidate in (existing, incoming):

        value = candidate.get("source_sections", [])

        if isinstance(value, str):
            value = [value]

        if isinstance(value, list):
            sections.extend(value)

        section = candidate.get("source_section")

        if section:
            sections.append(section)

    existing["source_sections"] = list(
        dict.fromkeys(
            str(section).strip()
            for section in sections
            if str(section).strip()
        )
    )

    # --------------------------------------------------------
    # Original skills
    # --------------------------------------------------------

    original_skills = []

    for candidate in (existing, incoming):

        value = candidate.get("original_skills", [])

        if isinstance(value, str):
            value = [value]

        if isinstance(value, list):
            original_skills.extend(value)

        original_skill = candidate.get("original_skill")

        if original_skill:
            original_skills.append(original_skill)

        resolved_from = candidate.get("resolved_from")

        if resolved_from:
            original_skills.append(resolved_from)

    existing["original_skills"] = list(
        dict.fromkeys(
            str(skill).strip()
            for skill in original_skills
            if str(skill).strip()
        )
    )

    if existing["original_skills"]:
        existing["original_skill"] = (
            existing["original_skills"][0]
        )

    # --------------------------------------------------------
    # Source text
    # --------------------------------------------------------

    if not existing.get("source_text"):
        existing["source_text"] = incoming.get(
            "source_text"
        )

    # --------------------------------------------------------
    # Extraction method
    # --------------------------------------------------------

    if not existing.get("extraction_method"):
        existing["extraction_method"] = incoming.get(
            "extraction_method"
        )


# ============================================================
# RESOLVE SINGLE SKILL
# ============================================================

def resolve_skill(candidate: dict[str, Any]) -> dict[str, Any]:
    """
    Resolve an alias to its canonical skill.
    """

    if not isinstance(candidate, dict):
        return candidate

    result = dict(candidate)

    skill_name = _get_skill_name(result)

    if not skill_name:
        return result

    normalized = _normalize_text(skill_name)

    canonical = ALIAS_MAP.get(normalized)

    if not canonical:
        return result

    # Already canonical.
    if normalized == _normalize_text(canonical):
        return result

    result["skill"] = canonical

    result["original_skill"] = skill_name
    result["resolved_from"] = skill_name
    result["resolution_method"] = "synonym"

    result["original_skills"] = [skill_name]

    return result


# ============================================================
# RESOLVE ALL
# ============================================================

def resolve_synonyms(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Resolve aliases and merge duplicate canonical skills.
    """

    if not candidates:
        return []

    resolved: dict[str, dict[str, Any]] = {}

    for candidate in candidates:

        if not isinstance(candidate, dict):
            continue

        result = resolve_skill(candidate)

        skill_name = _get_skill_name(result)

        if not skill_name:
            continue

        key = _normalize_text(skill_name)

        if key not in resolved:
            resolved[key] = result
            continue

        # IMPORTANT:
        # Merge transformed candidate.
        _merge_metadata(
            resolved[key],
            result,
        )

    return list(resolved.values())


# ============================================================
# BACKWARD-COMPATIBLE ALIAS
# ============================================================

resolve_skills = resolve_synonyms