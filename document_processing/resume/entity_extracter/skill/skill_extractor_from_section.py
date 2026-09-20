"""
skill_extractor_from_section.py

Extract skill candidates from normal resume sections.

Used for sections such as:

    summary
    experience
    projects
    certifications
    education
    achievements
    publications
    activities

This module DOES NOT:
    - perform fuzzy validation
    - resolve synonyms
    - expand stacks

It only discovers candidate skill mentions.

The actual normalization pipeline is handled by:

    spelling_resolver.py
    synonym_resolver.py
    master_skill_validator.py
    stack_resolver.py
"""

import json
import re
from pathlib import Path


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


SPELLING_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "spelling_dictionary.json"
)


# ============================================================
# LOAD MASTER SKILLS
# ============================================================

def load_master_skills():
    """
    Load active skills from master dictionary.
    """

    if not MASTER_SKILL_FILE.exists():
        return []

    with open(
        MASTER_SKILL_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(data, list):
        return []

    return [
        skill
        for skill in data
        if (
            isinstance(skill, dict)
            and skill.get("status") == "active"
            and skill.get("name")
        )
    ]


# ============================================================
# LOAD ALIASES
# ============================================================

def load_aliases():
    """
    Load skill aliases.

    Example:

        Fast API -> FastAPI
        React JS -> React.js
    """

    if not ALIAS_FILE.exists():
        return {}

    with open(
        ALIAS_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    return data if isinstance(data, dict) else {}


# ============================================================
# LOAD SPELLING DICTIONARY
# ============================================================

def load_spelling_dictionary():
    """
    Load known spelling corrections.

    Example:

        javasript -> JavaScript
    """

    if not SPELLING_FILE.exists():
        return {}

    with open(
        SPELLING_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    return data if isinstance(data, dict) else {}


# ============================================================
# NORMALIZE FOR LOOKUP
# ============================================================

def _normalize(value):
    if not isinstance(value, str):
        return ""

    return " ".join(
        value.strip().lower().split()
    )


# ============================================================
# REGEX ESCAPE
# ============================================================

def _build_pattern(skill_name):
    """
    Build a safe regex for a skill name.

    re.escape() is important for:

        C++
        C#
        .NET
        Node.js
        React.js
    """

    escaped = re.escape(
        skill_name.strip()
    )

    return re.compile(
        rf"(?<!\w){escaped}(?!\w)",
        flags=re.IGNORECASE,
    )


# ============================================================
# FIND SKILL IN TEXT
# ============================================================

def _find_skill_mentions(text, candidate):
    """
    Find a candidate skill in text.

    Returns True/False.
    """

    if not text or not candidate:
        return False

    pattern = _build_pattern(candidate)

    return bool(
        pattern.search(text)
    )


# ============================================================
# EXTRACT FROM ONE SECTION
# ============================================================

def extract_skills_from_section(
    section_name,
    section_block,
):
    """
    Extract candidate skill mentions from one resume section.

    Returns structured candidate objects so that the caller
    knows where the skill came from.
    """

    if not section_block:
        return []

    # --------------------------------------------------------
    # Flatten nested section detector output.
    #
    # Example:
    #
    # [
    #     [
    #         "Worked with Python.",
    #         "Developed APIs using FastAPI."
    #     ]
    # ]
    # --------------------------------------------------------

    text_parts = []

    def flatten(value):

        if isinstance(value, list):

            for item in value:
                flatten(item)

        elif isinstance(value, str):

            cleaned = value.strip()

            if cleaned:
                text_parts.append(cleaned)

    flatten(section_block)

    if not text_parts:
        return []

    text = " ".join(text_parts)

    candidates = []

    seen = set()

    # ========================================================
    # MASTER SKILL NAMES
    # ========================================================

    master_skills = load_master_skills()

    for skill in master_skills:

        skill_name = skill.get("name")

        if not skill_name:
            continue

        if not _find_skill_mentions(
            text,
            skill_name,
        ):
            continue

        key = _normalize(skill_name)

        if key in seen:
            continue

        seen.add(key)

        candidates.append(
            {
                "skill": skill_name,
                "source_section": section_name,
                "source_text": text,
                "extraction_method": "master_dictionary",
            }
        )

    # ========================================================
    # ALIASES
    # ========================================================

    aliases = load_aliases()

    for alias, canonical in aliases.items():

        if not alias or not canonical:
            continue

        if not _find_skill_mentions(
            text,
            alias,
        ):
            continue

        # Keep the ALIAS as the candidate.
        #
        # This allows synonym_resolver.py to perform
        # canonicalization later.

        key = _normalize(alias)

        if key in seen:
            continue

        seen.add(key)

        candidates.append(
            {
                "skill": alias,
                "source_section": section_name,
                "source_text": text,
                "extraction_method": "alias",
            }
        )

    # ========================================================
    # SPELLING VARIANTS
    # ========================================================

    spelling_dictionary = load_spelling_dictionary()

    for wrong, correct in spelling_dictionary.items():

        if not wrong:
            continue

        if not _find_skill_mentions(
            text,
            wrong,
        ):
            continue

        key = _normalize(wrong)

        if key in seen:
            continue

        seen.add(key)

        candidates.append(
            {
                "skill": wrong,
                "source_section": section_name,
                "source_text": text,
               "extraction_method": "spelling_dictionary",
            }
        )

    return candidates