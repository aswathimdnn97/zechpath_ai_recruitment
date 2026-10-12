"""
Skill Extraction From Section

Responsibilities
----------------
- Load master skill dictionary
- Load skill aliases
- Compile skill regex patterns once
- Build prefix indexes once
- Extract skill candidates from resume sections
- Preserve existing extraction semantics
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
import time

# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

MASTER_SKILL_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "master_skill_dictionary.json"
)

ALIAS_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "skill_aliases.json"
)


# ============================================================
# JSON LOADER
# ============================================================

def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return default


# ============================================================
# MASTER SKILLS
# ============================================================

def load_master_skills() -> list[dict[str, Any]]:
    data = _load_json(MASTER_SKILL_FILE, [])

    if isinstance(data, list):
        return [
            skill
            for skill in data
            if (
                isinstance(skill, dict)
                and skill.get("status") == "active"
                and skill.get("name")
            )
        ]

    if isinstance(data, dict):
        skills = data.get("skills", [])

        if isinstance(skills, list):
            return [
                skill
                for skill in skills
                if (
                    isinstance(skill, dict)
                    and skill.get("status", "active") == "active"
                    and skill.get("name")
                )
            ]

    return []


# ============================================================
# ALIASES
# ============================================================

def load_aliases() -> dict[str, str]:
    data = _load_json(ALIAS_FILE, {})

    if not isinstance(data, dict):
        return {}

    aliases: dict[str, str] = {}

    for alias, canonical in data.items():

        if not isinstance(alias, str):
            continue

        if not isinstance(canonical, str):
            continue

        alias = alias.strip()
        canonical = canonical.strip()

        if not alias or not canonical:
            continue

        aliases[alias] = canonical

    return aliases


# ============================================================
# LOAD ONCE
# ============================================================

MASTER_SKILLS = load_master_skills()
ALIASES = load_aliases()


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    return " ".join(
        value.strip().lower().split()
    )


# ============================================================
# REGEX BUILDER
# ============================================================

def _build_pattern(skill_name: str) -> re.Pattern[str]:
    escaped = re.escape(skill_name.strip())

    return re.compile(
        rf"(?<!\w){escaped}(?!\w)",
        flags=re.IGNORECASE,
    )


# ============================================================
# PREFIX BUILDER
# ============================================================

def _build_prefix(skill_name: str) -> str:
    """
    Creates a safe literal prefix used only to narrow
    the candidate regex patterns.

    Examples
    --------
    Python       -> py
    Java         -> ja
    JavaScript   -> ja
    React        -> re
    Django       -> dj
    Spring Boot  -> sp
    Node.js      -> no
    C++          -> c+
    C#           -> c#
    C Sharp      -> c

    The original regex is ALWAYS executed after this
    filter, so this cannot change the final matching rule.
    """

    if not isinstance(skill_name, str):
        return ""

    skill_name = skill_name.strip()

    if not skill_name:
        return ""

    first_token = skill_name.split()[0]

    if not first_token:
        return ""

    if len(first_token) >= 2:
        return first_token[:2].lower()

    return first_token.lower()


# ============================================================
# MASTER PATTERNS
# ============================================================

MASTER_SKILL_PATTERNS: list[
    tuple[dict[str, Any], re.Pattern[str], str]
] = []

for master_skill in MASTER_SKILLS:

    skill_name = master_skill.get("name")

    if not isinstance(skill_name, str):
        continue

    skill_name = skill_name.strip()

    if not skill_name:
        continue

    MASTER_SKILL_PATTERNS.append(
        (
            master_skill,
            _build_pattern(skill_name),
            _build_prefix(skill_name),
        )
    )


# ============================================================
# ALIAS PATTERNS
# ============================================================

ALIAS_PATTERNS: list[
    tuple[str, str, re.Pattern[str], str]
] = []

for alias, canonical in ALIASES.items():

    if not isinstance(alias, str):
        continue

    if not isinstance(canonical, str):
        continue

    alias = alias.strip()
    canonical = canonical.strip()

    if not alias or not canonical:
        continue

    ALIAS_PATTERNS.append(
        (
            alias,
            canonical,
            _build_pattern(alias),
            _build_prefix(alias),
        )
    )


# ============================================================
# PREFIX INDEXES
# ============================================================

MASTER_PATTERN_INDEX: dict[
    str,
    list[
        tuple[dict[str, Any], re.Pattern[str]]
    ]
] = {}

for master_skill, pattern, prefix in MASTER_SKILL_PATTERNS:

    MASTER_PATTERN_INDEX.setdefault(
        prefix,
        [],
    ).append(
        (
            master_skill,
            pattern,
        )
    )


ALIAS_PATTERN_INDEX: dict[
    str,
    list[
        tuple[str, str, re.Pattern[str]]
    ]
] = {}

for alias, canonical, pattern, prefix in ALIAS_PATTERNS:

    ALIAS_PATTERN_INDEX.setdefault(
        prefix,
        [],
    ).append(
        (
            alias,
            canonical,
            pattern,
        )
    )


# ============================================================
# DIAGNOSTIC
# ============================================================

print(
    f"[SKILL PATTERNS] "
    f"master={len(MASTER_SKILL_PATTERNS)} "
    f"aliases={len(ALIAS_PATTERNS)} "
    f"master_prefixes={len(MASTER_PATTERN_INDEX)} "
    f"alias_prefixes={len(ALIAS_PATTERN_INDEX)}"
)


# ============================================================
# MATCHER
# ============================================================

def _find_skill_mentions(
    text: str,
    pattern: re.Pattern[str],
) -> bool:

    if not text:
        return False

    return bool(pattern.search(text))


# ============================================================
# SOURCE BUILDER
# ============================================================

def _build_source(
    section_name: str,
    source_text: str,
    skill: str,
) -> dict[str, str]:

    return {
        "source_section": section_name,
        "source_text": source_text,
        "source_skill": skill,
    }


def extract_skills_from_section(
    section_name: str,
    section_block: Any,
) -> list[dict[str, Any]]:
    """
    Extract skills from a single section text/fragment.

    Performance goals
    ------------------
    - Avoid unnecessary recursive flattening when section_block
      is already a string.
    - Normalize and prepare the text only once.
    - Use prefix indexes to skip irrelevant patterns.
    - Preserve existing candidate structure.
    - Preserve source_section/source_text/source_skill.
    - Preserve master-dictionary and alias extraction behavior.

    Expected input from _collect_candidates()
    ------------------------------------------
        section_block = source_text

    where source_text is already a single flattened string.

    Returns
    -------
    list[dict[str, Any]]
        Extracted skill candidates.
    """

    # ---------------------------------------------------------
    # 1. Validate section
    # ---------------------------------------------------------

    if not section_block:
        return []

    if not isinstance(section_name, str):
        return []

    section_name = _normalize(section_name)

    if not section_name:
        return []

    # ---------------------------------------------------------
    # 2. Convert section_block into text
    #
    # IMPORTANT:
    # _collect_candidates() normally passes a string here.
    # Avoid recursive flattening in that common case.
    # ---------------------------------------------------------

    if isinstance(section_block, str):

        text = section_block.strip()

        if not text:
            return []

    else:

        text_parts: list[str] = []

        def flatten(value: Any) -> None:

            if isinstance(value, list):

                for item in value:
                    flatten(item)

            elif isinstance(value, tuple):

                for item in value:
                    flatten(item)

            elif isinstance(value, dict):

                for item in value.values():
                    flatten(item)

            elif isinstance(value, str):

                cleaned = value.strip()

                if cleaned:
                    text_parts.append(cleaned)

        flatten(section_block)

        if not text_parts:
            return []

        text = " ".join(text_parts)

    # ---------------------------------------------------------
    # 3. Lowercase once
    # ---------------------------------------------------------

    text_lower = text.lower()

    candidates: list[dict[str, Any]] = []

    # ---------------------------------------------------------
    # 4. Determine which prefixes are actually present
    #
    # Instead of creating two sets containing every prefix,
    # create only boolean lookup information needed by the
    # pattern loops.
    # ---------------------------------------------------------

    master_prefixes_present = {
        prefix
        for prefix in MASTER_PATTERN_INDEX
        if prefix and prefix in text_lower
    }

    alias_prefixes_present = {
        prefix
        for prefix in ALIAS_PATTERN_INDEX
        if prefix and prefix in text_lower
    }

    # ---------------------------------------------------------
    # 5. MASTER DICTIONARY
    # ---------------------------------------------------------

    for master_skill, pattern, prefix in MASTER_SKILL_PATTERNS:

        # Fast rejection.
        if prefix and prefix not in master_prefixes_present:
            continue

        skill_name = master_skill.get("name")

        if not isinstance(skill_name, str):
            continue

        skill_name = skill_name.strip()

        if not skill_name:
            continue

        if skill_name.lower() not in text_lower:
            continue

        # Exact/regex skill validation.
        if not _find_skill_mentions(
            text,
            pattern,
        ):
            continue

        candidates.append(
            {
                "skill": skill_name,
                "source_section": section_name,
                "source_text": text,
                "extraction_method": "master_dictionary",
                "sources": [
                    _build_source(
                        section_name,
                        text,
                        skill_name,
                    )
                ],
            }
        )

    # ---------------------------------------------------------
    # 6. ALIAS DICTIONARY
    # ---------------------------------------------------------

    for alias, canonical, pattern, prefix in ALIAS_PATTERNS:

        # Fast rejection.
        if prefix and prefix not in alias_prefixes_present:
            continue

        if alias.lower() not in text_lower:
            continue

        if not _find_skill_mentions(
            text,
            pattern,
        ):
            continue

        candidates.append(
            {
                "skill": alias,
                "source_section": section_name,
                "source_text": text,
                "extraction_method": "alias",
                "sources": [
                    _build_source(
                        section_name,
                        text,
                        alias,
                    )
                ],
            }
        )

    return candidates