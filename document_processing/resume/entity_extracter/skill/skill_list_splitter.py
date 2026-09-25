"""
skill_list_splitter.py

Responsibilities
----------------
1. Split a dedicated Skills section into individual skill candidates.
2. Handle common separators.
3. Handle space-separated skills using the master skill dictionary
   and skill aliases.
4. Remove category labels such as:
       Backend:
       Frontend:
       Database:
       Programming Languages:
5. Preserve multi-word skill names.
6. Preserve technology names such as:
       C++
       C#
       .NET
       Node.js
       React.js

This module does NOT:
    - resolve spelling
    - resolve synonyms
    - validate skills
    - perform fuzzy matching
    - expand technology stacks

Those responsibilities belong to:
    spelling_resolver.py
    synonym_resolver.py
    master_skill_validator.py
    stack_resolver.py
"""

import json
import re
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[4]

MASTER_SKILL_DICTIONARY = (
    BASE_DIR / "data" / "resume" / "skills" / "master_skill_dictionary.json"
)

SKILL_ALIASES = (
    BASE_DIR / "data" / "resume" / "skills" / "skill_aliases.json"
)


# ============================================================
# CATEGORY PREFIXES
# ============================================================

CATEGORY_PREFIX_PATTERN = re.compile(
    r"""
    ^\s*
    (?:
        backend
        |frontend
        |full[-\s]?stack
        |database
        |databases
        |programming\s+languages?
        |technical\s+skills?
        |technologies
        |technology
        |frameworks?
        |libraries
        |tools
        |devops
        |cloud
        |testing
        |testing\s+tools
        |web\s+technologies
        |soft\s+skills
        |skills
    )
    \s*:\s*
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# BULLET PREFIX
# ============================================================

BULLET_PATTERN = re.compile(
    r"^[\s•●▪◦‣\*-]+"
)


# ============================================================
# EXPLICIT SKILL SEPARATORS
# ============================================================

SEPARATOR_PATTERN = re.compile(
    r"""
    \s*
    (?:
        \|
        |,
        |;
        |\u2022
        |\u00b7
    )
    \s*
    """,
    flags=re.VERBOSE,
)


# ============================================================
# LOAD MASTER SKILLS
# ============================================================

def _load_master_skills():
    """
    Load canonical skill names from the master dictionary.

    Expected structure:

    [
        {
            "skill_id": "TECH001",
            "name": "Python",
            ...
        }
    ]
    """

    try:
        if not MASTER_SKILL_DICTIONARY.exists():
            return []

        with open(
            MASTER_SKILL_DICTIONARY,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return []

    if not isinstance(data, list):
        return []

    skills = []

    for item in data:

        if not isinstance(item, dict):
            continue

        name = item.get("name")

        if not isinstance(name, str):
            continue

        name = name.strip()

        if not name:
            continue

        status = item.get(
            "status",
            "active",
        )

        if isinstance(status, str):
            if status.lower() != "active":
                continue

        skills.append(name)

    return skills


# ============================================================
# LOAD ALIASES
# ============================================================

def _load_aliases():
    """
    Load aliases from skill_aliases.json.

    Example:

        {
            "aws": "AWS",
            "amazon web services": "AWS",
            "docker": "Docker",
            "docker container": "Docker",
            "fast api": "FastAPI"
        }
    """

    try:
        if not SKILL_ALIASES.exists():
            return {}

        with open(
            SKILL_ALIASES,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}

    if not isinstance(data, dict):
        return {}

    aliases = {}

    for alias, canonical in data.items():

        if not isinstance(
            alias,
            str,
        ):
            continue

        if not isinstance(
            canonical,
            str,
        ):
            continue

        alias = alias.strip()
        canonical = canonical.strip()

        if not alias or not canonical:
            continue

        aliases[
            alias.lower()
        ] = canonical

    return aliases


# ============================================================
# NORMALIZE MATCH TEXT
# ============================================================

def _normalize_match_text(value):
    """
    Normalize text only for matching.

    Examples:

        "Fast API" -> "fast api"
        "REST APIs" -> "rest apis"
        "AWS" -> "aws"
    """

    if not isinstance(
        value,
        str,
    ):
        return ""

    value = value.strip().lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


# ============================================================
# CLEAN ONE SKILL ITEM
# ============================================================

def _clean_skill_item(skill):
    """
    Clean one extracted skill candidate.

    This function intentionally does not perform
    spelling correction or synonym resolution.
    """

    if not isinstance(
        skill,
        str,
    ):
        return ""

    skill = skill.strip()

    if not skill:
        return ""

    # Remove bullet characters.
    skill = BULLET_PATTERN.sub(
        "",
        skill,
    ).strip()

    # Remove category prefix.
    skill = CATEGORY_PREFIX_PATTERN.sub(
        "",
        skill,
    ).strip()

    # Normalize repeated whitespace.
    skill = re.sub(
        r"\s+",
        " ",
        skill,
    )

    return skill.strip()


# ============================================================
# DICTIONARY-AWARE SPACE SEPARATED SPLITTER
# ============================================================

def _split_using_known_skills(line):
    """
    Extract known skills from a space-separated Skills line.

    Example:

        Python Django Fast API REST API PostgreSQL Git Docker AWS API Testing

    becomes:

        Python
        Django
        Fast API
        REST API
        PostgreSQL
        Git
        Docker
        AWS
        API Testing

    The longest matching skill phrases are checked first so
    multi-word skills are preserved.

    IMPORTANT
    ---------
    This function does not perform fuzzy matching.

    It only uses exact normalized matching against:

        1. master skill dictionary
        2. skill aliases
    """

    if not isinstance(
        line,
        str,
    ):
        return []

    line = _clean_skill_item(line)

    if not line:
        return []

    master_skills = _load_master_skills()
    aliases = _load_aliases()
    
    print("\n========== SPLITTER DEBUG ==========")

    print("MASTER DICTIONARY PATH:")
    print(MASTER_SKILL_DICTIONARY)
    print("EXISTS:", MASTER_SKILL_DICTIONARY.exists())
    print("MASTER SKILLS COUNT:", len(master_skills))

    print("\nALIASES PATH:")
    print(SKILL_ALIASES)
    print("EXISTS:", SKILL_ALIASES.exists())
    print("ALIASES COUNT:", len(aliases))

    print("\nCHECKING REQUIRED SKILLS:")

    for value in [
        "Python",
        "Django",
        "FastAPI",
        "PostgreSQL",
        "Git",
        "Docker",
        "AWS",
        "API Testing",
    ]:
        print(
            value,
            "=>",
            value.lower() in [
                str(skill).lower()
                for skill in master_skills
            ]
        )

    print("====================================\n")

    # --------------------------------------------------------
    # Build known phrases.
    # --------------------------------------------------------

    known_phrases = {}

    # Canonical master skills.
    for skill in master_skills:

        normalized = _normalize_match_text(
            skill
        )

        if normalized:
            known_phrases[
                normalized
            ] = skill

    # Aliases.
    for alias, canonical in aliases.items():

        normalized_alias = _normalize_match_text(
            alias
        )

        if normalized_alias:
            known_phrases[
                normalized_alias
            ] = alias

    if not known_phrases:
        return [line]

    # --------------------------------------------------------
    # Sort longest phrases first.
    #
    # This is important.
    #
    # Example:
    #
    # API
    # API Testing
    #
    # We must match API Testing first.
    # --------------------------------------------------------

    phrases = sorted(
        known_phrases.keys(),
        key=lambda value: (
            len(value.split()),
            len(value),
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # Tokenize input while preserving original tokens.
    # --------------------------------------------------------

    tokens = line.split()

    if not tokens:
        return []

    results = []

    index = 0

    while index < len(tokens):

        matched = False

        # ----------------------------------------------------
        # Try longest phrase first.
        # ----------------------------------------------------

        for phrase in phrases:

            phrase_tokens = phrase.split()

            phrase_length = len(
                phrase_tokens
            )

            if (
                index + phrase_length
                > len(tokens)
            ):
                continue

            candidate_tokens = tokens[
                index:
                index + phrase_length
            ]

            candidate = " ".join(
                candidate_tokens
            )

            normalized_candidate = (
                _normalize_match_text(
                    candidate
                )
            )

            if normalized_candidate != phrase:
                continue

            # ------------------------------------------------
            # Preserve original text from resume.
            # ------------------------------------------------

            original_candidate = " ".join(
                candidate_tokens
            )

            results.append(
                original_candidate
            )

            index += phrase_length

            matched = True

            break

        # ----------------------------------------------------
        # No known skill matched.
        # ----------------------------------------------------

        if not matched:

            # Move one token forward.
            #
            # Do NOT add unknown tokens as skills.
            #
            # They will be ignored by this dictionary-aware
            # splitter.
            index += 1

    return results


# ============================================================
# SPLIT ONE LINE
# ============================================================

def _split_line(line):
    """
    Split one Skills-section line.

    Supports:

        Backend: Django, FastAPI, Flask

        Frontend: React | JavaScript | HTML | CSS

        Database: PostgreSQL; MongoDB

        Python Django Fast API REST API PostgreSQL Git Docker AWS

    The final example is handled using dictionary-aware
    matching rather than whitespace splitting.
    """

    if not isinstance(
        line,
        str,
    ):
        return []

    line = line.strip()

    if not line:
        return []

    # --------------------------------------------------------
    # Remove bullet.
    # --------------------------------------------------------

    line = BULLET_PATTERN.sub(
        "",
        line,
    ).strip()

    # --------------------------------------------------------
    # Remove category prefix.
    # --------------------------------------------------------

    line = CATEGORY_PREFIX_PATTERN.sub(
        "",
        line,
    ).strip()

    if not line:
        return []

    # --------------------------------------------------------
    # First try explicit separators.
    # --------------------------------------------------------

    if SEPARATOR_PATTERN.search(line):

        parts = SEPARATOR_PATTERN.split(
            line
        )

        cleaned = []

        for part in parts:

            skill = _clean_skill_item(
                part
            )

            if skill:
                cleaned.append(
                    skill
                )

        return cleaned

    # --------------------------------------------------------
    # No explicit separators.
    #
    # Use dictionary-aware matching.
    # --------------------------------------------------------

    dictionary_skills = (
        _split_using_known_skills(
            line
        )
    )

    if dictionary_skills:
        return dictionary_skills

    # --------------------------------------------------------
    # Fallback:
    #
    # Preserve the complete item rather than incorrectly
    # splitting multi-word skills.
    # --------------------------------------------------------

    cleaned = _clean_skill_item(
        line
    )

    return [cleaned] if cleaned else []


# ============================================================
# MAIN FUNCTION
# ============================================================

def split_skill_line(lines):
    """
    Split a dedicated Skills section into raw skill candidates.

    Input
    -----
    Can be:

        - string
        - list[str]
        - nested list

    Examples
    --------

        Input:

            [
                "Backend: Django, FastAPI, Flask",
                "Frontend: React, JavaScript, HTML, CSS",
                "Database: PostgreSQL, MongoDB"
            ]

        Output:

            [
                "Django",
                "FastAPI",
                "Flask",
                "React",
                "JavaScript",
                "HTML",
                "CSS",
                "PostgreSQL",
                "MongoDB"
            ]

    Space-separated input:

        "Python Django Fast API REST API PostgreSQL Git Docker AWS API Testing"

    becomes:

        [
            "Python",
            "Django",
            "Fast API",
            "REST API",
            "PostgreSQL",
            "Git",
            "Docker",
            "AWS",
            "API Testing"
        ]

    IMPORTANT
    ---------

    This function returns RAW candidates.

    It does not perform:

        spelling correction
        synonym resolution
        fuzzy matching
        validation
        stack expansion
    """

    if not lines:
        return []

    # --------------------------------------------------------
    # Accept a single string.
    # --------------------------------------------------------

    if isinstance(
        lines,
        str,
    ):
        lines = lines.splitlines()

    # --------------------------------------------------------
    # Make sure input is a list.
    # --------------------------------------------------------

    if not isinstance(
        lines,
        list,
    ):
        return []

    skills = []

    # --------------------------------------------------------
    # Flatten nested lists.
    # --------------------------------------------------------

    def flatten(items):

        for item in items:

            if isinstance(
                item,
                list,
            ):

                yield from flatten(
                    item
                )

            elif isinstance(
                item,
                str,
            ):

                if item.strip():
                    yield item

    # --------------------------------------------------------
    # Process every line.
    # --------------------------------------------------------

    for line in flatten(lines):

        extracted = _split_line(
            line
        )

        skills.extend(
            extracted
        )

    # --------------------------------------------------------
    # Remove duplicates while preserving order.
    # --------------------------------------------------------

    unique_skills = []

    seen = set()

    for skill in skills:

        key = _normalize_match_text(
            skill
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)

        unique_skills.append(
            skill
        )

    return unique_skills