"""
stack_resolver.py

Responsibilities
----------------
1. Expand validated technology stacks.
2. Add only skills that exist in the master dictionary.
3. Preserve source/evidence metadata from the parent stack.
4. Prevent duplicate skills.
5. Never perform spelling correction.
6. Never perform synonym resolution.
7. Never perform fuzzy matching.

Pipeline position
-----------------
Spelling Resolver
        ↓
Synonym Resolver
        ↓
Master Skill Validator
        ↓
Stack Resolver
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[4]

STACK_DICTIONARY_PATH = (
    BASE_DIR
    / "data"
    / "resume"
    / "skills"
    / "skill_stacks.json"
)

MASTER_SKILL_DICTIONARY_PATH = (
    BASE_DIR
    / "data"
    / "resume"
    / "skills"
    / "master_skill_dictionary.json"
)


# ============================================================
# JSON LOADER
# ============================================================

def _load_json(path: Path) -> Any:

    if not path.exists():
        raise FileNotFoundError(
            f"Required skill file not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


STACK_DICTIONARY = _load_json(
    STACK_DICTIONARY_PATH
)

MASTER_SKILL_DICTIONARY = _load_json(
    MASTER_SKILL_DICTIONARY_PATH
)


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip().lower()


# ============================================================
# MASTER SKILL LOADING
# ============================================================

def _extract_master_skills(
    data: Any,
) -> list[dict[str, Any]]:

    if isinstance(data, list):
        raw_skills = data

    elif isinstance(data, dict):
        raw_skills = data.get("skills", [])

    else:
        raw_skills = []

    result = []

    for item in raw_skills:

        if isinstance(item, str):

            name = item.strip()

            if name:
                result.append(
                    {
                        "name": name,
                        "skill_id": None,
                    }
                )

            continue

        if not isinstance(item, dict):
            continue

        name = (
            item.get("name")
            or item.get("skill")
            or item.get("canonical_name")
        )

        if not name:
            continue

        result.append(
            {
                **item,
                "name": str(name).strip(),
            }
        )

    return result


MASTER_SKILLS = _extract_master_skills(
    MASTER_SKILL_DICTIONARY
)


MASTER_BY_NAME: dict[str, dict[str, Any]] = {
    _normalize(skill["name"]): skill
    for skill in MASTER_SKILLS
}


# ============================================================
# STACK LOADING
# ============================================================

def _extract_stack_mapping(
    data: Any,
) -> dict[str, list[str]]:
    """
    Supports common stack dictionary formats.

    Example:

    {
        "MERN": [
            "MongoDB",
            "Express",
            "React",
            "Node.js"
        ]
    }

    or:

    {
        "stacks": {
            "MERN": [...]
        }
    }
    """

    if isinstance(data, dict):

        if isinstance(data.get("stacks"), dict):
            data = data["stacks"]

        mapping: dict[str, list[str]] = {}

        for stack_name, children in data.items():

            if not isinstance(stack_name, str):
                continue

            if not isinstance(children, list):
                continue

            normalized_children = [
                str(child).strip()
                for child in children
                if str(child).strip()
            ]

            mapping[
                _normalize(stack_name)
            ] = normalized_children

        return mapping

    return {}


STACK_MAP = _extract_stack_mapping(
    STACK_DICTIONARY
)


# ============================================================
# SOURCE HELPERS
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

    merged = []
    seen = set()

    for source in (existing or []) + (incoming or []):

        key = _source_key(source)

        if not key or key in seen:
            continue

        seen.add(key)
        merged.append(source)

    return merged


# ============================================================
# METADATA HELPERS
# ============================================================

def _copy_parent_metadata(
    parent: dict[str, Any],
) -> dict[str, Any]:

    excluded = {
        "skill",
        "name",
        "canonical_name",
        "skill_id",
        "matched_by",
        "match_score",
    }

    metadata = {}

    for key, value in parent.items():

        if key in excluded:
            continue

        metadata[key] = value

    return metadata


# ============================================================
# BUILD EXPANDED SKILL
# ============================================================

def _build_expanded_skill(
    parent: dict[str, Any],
    child_master: dict[str, Any],
) -> dict[str, Any]:

    parent_skill = (
        parent.get("skill")
        or parent.get("name")
        or ""
    )

    result = _copy_parent_metadata(parent)

    result["skill"] = child_master["name"]

    if child_master.get("skill_id") is not None:
        result["skill_id"] = child_master[
            "skill_id"
        ]

    result["matched_by"] = "stack"

    result["source_skill"] = parent_skill

    result["stack_source"] = parent_skill

    # --------------------------------------------------------
    # Preserve source section
    # --------------------------------------------------------

    if not result.get("source_section"):

        source_sections = result.get(
            "source_sections"
        )

        if isinstance(source_sections, list):
            if source_sections:
                result["source_section"] = (
                    source_sections[0]
                )

    # --------------------------------------------------------
    # Preserve source evidence
    # --------------------------------------------------------

    sources = result.get("sources", [])

    if not sources:

        source_section = result.get(
            "source_section"
        )

        source_text = result.get(
            "source_text"
        )

        if source_section or source_text:

            sources = [
                {
                    "source_section": source_section,
                    "source_text": source_text,
                    "source_skill": parent_skill,
                }
            ]

    else:

        copied_sources = []

        for source in sources:

            if isinstance(source, dict):

                copied = dict(source)

                # For stack expansion, explicitly record
                # the parent stack as the source skill.
                if not copied.get("source_skill"):
                    copied["source_skill"] = parent_skill

                copied_sources.append(copied)

            else:

                copied_sources.append(
                    {
                        "source_section": result.get(
                            "source_section"
                        ),
                        "source_text": result.get(
                            "source_text"
                        ),
                        "source_skill": parent_skill,
                    }
                )

        sources = copied_sources

    result["sources"] = sources

    # --------------------------------------------------------
    # Preserve source sections
    # --------------------------------------------------------

    sections = result.get(
        "source_sections",
        [],
    )

    if isinstance(sections, str):
        sections = [sections]

    if not isinstance(sections, list):
        sections = []

    if result.get("source_section"):
        sections.append(
            result["source_section"]
        )

    result["source_sections"] = list(
        dict.fromkeys(
            str(section).strip()
            for section in sections
            if str(section).strip()
        )
    )

    return result


# ============================================================
# MERGE DUPLICATES
# ============================================================

def _merge_metadata(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> None:

    # --------------------------------------------------------
    # Sources
    # --------------------------------------------------------

    existing["sources"] = _merge_sources(
        existing.get("sources"),
        incoming.get("sources"),
    )

    # --------------------------------------------------------
    # Source sections
    # --------------------------------------------------------

    sections = []

    for candidate in (existing, incoming):

        value = candidate.get(
            "source_sections",
            [],
        )

        if isinstance(value, str):
            value = [value]

        if isinstance(value, list):
            sections.extend(value)

        section = candidate.get(
            "source_section"
        )

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
    # Source skills
    # --------------------------------------------------------

    source_skills = []

    for candidate in (existing, incoming):

        value = candidate.get(
            "source_skills",
            [],
        )

        if isinstance(value, str):
            value = [value]

        if isinstance(value, list):
            source_skills.extend(value)

        source_skill = candidate.get(
            "source_skill"
        )

        if source_skill:
            source_skills.append(
                source_skill
            )

    existing["source_skills"] = list(
        dict.fromkeys(
            str(skill).strip()
            for skill in source_skills
            if str(skill).strip()
        )
    )

    if existing["source_skills"]:
        existing["source_skill"] = (
            existing["source_skills"][0]
        )

    # --------------------------------------------------------
    # Preserve source text
    # --------------------------------------------------------

    if not existing.get("source_text"):
        existing["source_text"] = incoming.get(
            "source_text"
        )


# ============================================================
# RESOLVE STACK FOR ONE SKILL
# ============================================================

def _expand_skill(
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:

    skill_name = (
        candidate.get("skill")
        or candidate.get("name")
        or ""
    )

    if not skill_name:
        return []

    children = STACK_MAP.get(
        _normalize(skill_name)
    )

    if not children:
        return []

    expanded = []

    for child_name in children:

        child_master = MASTER_BY_NAME.get(
            _normalize(child_name)
        )

        # Never emit a stack child that does not exist
        # in the master dictionary.
        if child_master is None:
            continue

        expanded.append(
            _build_expanded_skill(
                candidate,
                child_master,
            )
        )

    return expanded


# ============================================================
# RESOLVE ALL STACKS
# ============================================================

def resolve_stacks(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Expand validated technology stacks.

    The original stack remains in the result.
    Expanded child skills are added when valid.
    """

    if not candidates:
        return []

    result: dict[str, dict[str, Any]] = {}

    # --------------------------------------------------------
    # Keep all original validated skills.
    # --------------------------------------------------------

    for candidate in candidates:

        if not isinstance(candidate, dict):
            continue

        skill_name = (
            candidate.get("skill")
            or candidate.get("name")
            or ""
        )

        if not skill_name:
            continue

        key = _normalize(skill_name)

        if key not in result:
            result[key] = dict(candidate)
        else:
            _merge_metadata(
                result[key],
                candidate,
            )

    # --------------------------------------------------------
    # Expand stacks.
    # --------------------------------------------------------

    for candidate in candidates:

        if not isinstance(candidate, dict):
            continue

        expanded_skills = _expand_skill(
            candidate
        )

        for expanded in expanded_skills:

            skill_name = expanded.get(
                "skill"
            )

            if not skill_name:
                continue

            key = _normalize(skill_name)

            if key not in result:
                result[key] = expanded
                continue

            # If skill already exists directly,
            # merge stack evidence into it.
            _merge_metadata(
                result[key],
                expanded,
            )

            # Preserve that the skill was also
            # discovered through a stack.
            matched_by = result[key].get(
                "matched_by"
            )

            if matched_by == "exact":
                result[key]["matched_by"] = (
                    "exact+stack"
                )

            elif matched_by == "fuzzy":
                result[key]["matched_by"] = (
                    "fuzzy+stack"
                )

    return list(result.values())


# ============================================================
# BACKWARD-COMPATIBLE ALIAS
# ============================================================

expand_skill_stacks = resolve_stacks