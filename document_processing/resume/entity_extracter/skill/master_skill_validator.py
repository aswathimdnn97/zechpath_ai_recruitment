"""
master_skill_validator.py

Responsibilities
----------------
1. Validate extracted/resolved skills against the master dictionary.
2. Perform exact matching first.
3. Perform conservative fuzzy matching when required.
4. Reject unknown skills.
5. Preserve all source/evidence metadata.
6. Normalize canonical master skill names.
7. Never perform synonym resolution or stack expansion.

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

from rapidfuzz import fuzz, process


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[4]

MASTER_SKILL_DICTIONARY_PATH = (
    BASE_DIR
    / "data"
    / "resume"
    / "skills"
    / "master_skill_dictionary.json"
)

FUZZY_MATCH_THRESHOLD = 90.0

SKILL_ALIASES_PATH = (
    BASE_DIR
    / "data"
    / "resume"
    / "skills"
    / "skill_aliases.json"
)


# ============================================================
# JSON LOADER
# ============================================================

def _load_json(path: Path) -> Any:

    if not path.exists():
        raise FileNotFoundError(
            f"Master skill dictionary not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


MASTER_SKILL_DICTIONARY = _load_json(
    MASTER_SKILL_DICTIONARY_PATH
)


# ============================================================
# MASTER SKILL NORMALIZATION
# ============================================================

def _extract_master_skills(
    data: Any,
) -> list[dict[str, Any]]:
    """
    Normalize supported master dictionary structures.

    Supported examples:

    [
        {"name": "Python", "skill_id": "SK001"}
    ]

    or

    {
        "skills": [
            {"name": "Python", "skill_id": "SK001"}
        ]
    }
    """

    if isinstance(data, list):
        raw_skills = data

    elif isinstance(data, dict):
        raw_skills = data.get("skills", [])

    else:
        raw_skills = []

    normalized: list[dict[str, Any]] = []

    for item in raw_skills:

        if isinstance(item, str):

            name = item.strip()

            if name:
                normalized.append(
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

        normalized.append(
            {
                **item,
                "name": str(name).strip(),
                "skill_id": item.get("skill_id"),
            }
        )

    return normalized


MASTER_SKILLS = _extract_master_skills(
    MASTER_SKILL_DICTIONARY
)

# ============================================================
# SKILL ALIAS LOADING
# ============================================================

def _load_skill_aliases() -> dict[str, str]:
    """
    Load skill aliases such as:

        "rest apis" -> "REST API"
        "fast api"  -> "FastAPI"
        "drf"      -> "Django REST Framework"

    Aliases are used only to map extracted skill names to
    canonical master skill names.
    """

    if not SKILL_ALIASES_PATH.exists():
        return {}

    data = _load_json(SKILL_ALIASES_PATH)

    if not isinstance(data, dict):
        return {}

    return {
        str(alias).strip().lower(): str(canonical).strip()
        for alias, canonical in data.items()
        if str(alias).strip() and str(canonical).strip()
    }


SKILL_ALIASES = _load_skill_aliases()


# ============================================================
# MASTER LOOKUP MAPS
# ============================================================

def _normalize(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip().lower()


MASTER_BY_NAME: dict[str, dict[str, Any]] = {}

MASTER_NAMES: list[str] = []

for master_skill in MASTER_SKILLS:

    name = master_skill["name"]

    key = _normalize(name)

    if not key:
        continue

    MASTER_BY_NAME[key] = master_skill
    MASTER_NAMES.append(name)


# ============================================================
# CANDIDATE HELPERS
# ============================================================

def _get_skill_name(candidate: dict[str, Any]) -> str:

    return str(
        candidate.get("skill")
        or candidate.get("name")
        or candidate.get("canonical_name")
        or ""
    ).strip()


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
# METADATA COPY
# ============================================================

def _copy_metadata(
    candidate: dict[str, Any],
) -> dict[str, Any]:

    metadata: dict[str, Any] = {}

    excluded = {
        "skill",
        "name",
        "canonical_name",
        "matched_by",
        "skill_id",
    }

    for key, value in candidate.items():

        if key in excluded:
            continue

        metadata[key] = value

    return metadata


# ============================================================
# VALIDATE EXACT
# ============================================================

def _exact_match(
    skill_name: str,
) -> dict[str, Any] | None:
    """
    Perform exact matching against the master dictionary.

    Alias resolution is applied before the master lookup.

    Examples:

        REST APIs
            -> REST API
            -> TECH025

        Fast API
            -> FastAPI
            -> TECH014

        DRF
            -> Django REST Framework
            -> TECH041
    """

    normalized_name = _normalize(skill_name)

    if not normalized_name:
        return None

    # Direct canonical master match first.
    master_skill = MASTER_BY_NAME.get(normalized_name)

    if master_skill is not None:
        return master_skill

    # Alias -> canonical name.
    canonical_name = SKILL_ALIASES.get(normalized_name)

    if canonical_name:
        return MASTER_BY_NAME.get(
            _normalize(canonical_name)
        )

    return None


# ============================================================
# VALIDATE FUZZY
# ============================================================

def _fuzzy_match(
    skill_name: str,
) -> tuple[dict[str, Any] | None, float]:

    if not MASTER_NAMES:
        return None, 0.0

    normalized_name = "".join(
        character
        for character in skill_name.casefold()
        if character.isalnum()
    )
    if len(normalized_name) < 3:
        return None, 0.0

    result = process.extractOne(
        skill_name,
        MASTER_NAMES,
        scorer=fuzz.WRatio,
    )

    if not result:
        return None, 0.0

    matched_name, score, _ = result

    if score < FUZZY_MATCH_THRESHOLD:
        return None, score

    master_skill = MASTER_BY_NAME.get(
        _normalize(matched_name)
    )

    return master_skill, float(score)


# ============================================================
# MERGE METADATA
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

        value = candidate.get(
            "original_skills",
            [],
        )

        if isinstance(value, str):
            value = [value]

        if isinstance(value, list):
            original_skills.extend(value)

        for key in (
            "original_skill",
            "resolved_from",
        ):
            value = candidate.get(key)

            if value:
                original_skills.append(value)

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
    # Preserve source text
    # --------------------------------------------------------

    if not existing.get("source_text"):
        existing["source_text"] = incoming.get(
            "source_text"
        )

    # --------------------------------------------------------
    # Preserve extraction method
    # --------------------------------------------------------

    if not existing.get("extraction_method"):
        existing["extraction_method"] = incoming.get(
            "extraction_method"
        )


# ============================================================
# VALIDATE SINGLE CANDIDATE
# ============================================================

def validate_skill(
    candidate: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Validate one candidate.

    Returns
    -------
    dict | None
        Validated canonical skill or None when rejected.
    """

    if not isinstance(candidate, dict):
        return None

    skill_name = _get_skill_name(candidate)

    if not skill_name:
        return None

    # --------------------------------------------------------
    # Exact match
    # --------------------------------------------------------

    master_skill = _exact_match(skill_name)

    matched_by = "exact"
    fuzzy_score = None

    # --------------------------------------------------------
    # Fuzzy fallback
    # --------------------------------------------------------

    if master_skill is None:

        master_skill, fuzzy_score = _fuzzy_match(
            skill_name
        )

        if master_skill is None:
            return None

        matched_by = "fuzzy"

    # --------------------------------------------------------
    # Build canonical result
    # --------------------------------------------------------

    result = _copy_metadata(candidate)

    result["skill"] = master_skill["name"]

    if master_skill.get("skill_id") is not None:
        result["skill_id"] = master_skill["skill_id"]

    result["matched_by"] = matched_by

    if fuzzy_score is not None:
        result["match_score"] = round(
            fuzzy_score,
            2,
        )

    # --------------------------------------------------------
    # Preserve original candidate if changed
    # --------------------------------------------------------

    if _normalize(skill_name) != _normalize(
        master_skill["name"]
    ):

        result.setdefault(
            "original_skill",
            skill_name,
        )

        result.setdefault(
            "original_skills",
            [],
        )

        if skill_name not in result["original_skills"]:
            result["original_skills"].append(
                skill_name
            )

    return result


# ============================================================
# VALIDATE ALL
# ============================================================

def validate_skills(
    candidates: list[dict[str, Any] | str],
) -> list[dict[str, Any]]:
    """
    Validate all candidates against the master dictionary.

    Unknown skills are rejected.
    Duplicate canonical skills are merged.
    """

    if not candidates:
        return []

    validated: dict[str, dict[str, Any]] = {}

    for candidate in candidates:

        # split_skill_line() returns strings.
        # Other pipeline stages may return dictionaries.
        # Support both formats.

        if isinstance(candidate, str):
            candidate = {
                "skill": candidate,
            }

        result = validate_skill(candidate)

        if result is None:
            continue

        skill_name = _get_skill_name(result)

        if not skill_name:
            continue

        key = _normalize(skill_name)

        if key not in validated:
            validated[key] = result
            continue

        _merge_metadata(
            validated[key],
            result,
        )

    return list(validated.values())


# ============================================================
# BACKWARD-COMPATIBLE ALIAS
# ============================================================

validate_master_skills = validate_skills