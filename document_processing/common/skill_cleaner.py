"""
skill_cleaner.py

Responsibilities
----------------
1. Remove common filler phrases.
2. Normalize whitespace and punctuation.
3. Split explicit separators.
4. Split standalone connector words.
5. Split adjacent skill names using the master skill dictionary.
6. Preserve multi-word skills when they exist in the master dictionary.
7. Remove duplicates.

IMPORTANT
---------
This module does NOT contain a hard-coded technology list.

Technology names and multi-word skills are obtained from:

    data/resume/skills/master_skill_dictionary.json

This allows the cleaner to work with new technologies without
changing Python code.
"""

import json
import re
from pathlib import Path


# ============================================================
# MASTER SKILL DICTIONARY
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MASTER_SKILL_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "master_skill_dictionary.json"
)


# ============================================================
# FILLER PATTERNS
# ============================================================

FILLER_PATTERNS = [

    r"\bhands[- ]on\s+experience\s+with\s+",

    r"\bhands[- ]on\s+experience\s+in\s+",

    r"\bstrong\s+experience\s+with\s+",

    r"\bstrong\s+knowledge\s+of\s+",

    r"\bexperience\s+with\s+",

    r"\bexperience\s+in\s+",

    r"\bknowledge\s+of\s+",

    r"\bknowledge\s+in\s+",

    r"\bfamiliar\s+with\s+",

    r"\bexpertise\s+in\s+",

    r"\bexpertise\s+with\s+",

    r"\bgood\s+understanding\s+of\s+",

    r"\bunderstanding\s+of\s+",

    r"\bproficiency\s+in\s+",

    r"\bproficiency\s+with\s+",

    r"\bunit\s+testing\s+using\s+",

    r"\btesting\s+using\s+",
]


# ============================================================
# CONNECTOR WORDS
# ============================================================

CONNECTOR_PATTERN = re.compile(
    r"\s+\b(?:and|or)\b\s+",
    flags=re.IGNORECASE,
)


# ============================================================
# LOAD MASTER SKILLS
# ============================================================

def _load_master_skills() -> list[str]:
    """
    Load active skill names from the master skill dictionary.

    Expected JSON structure:

    [
        {
            "name": "Python",
            "status": "active"
        },
        {
            "name": "Django REST Framework",
            "status": "active"
        }
    ]

    Returns
    -------
    list[str]
        Active skill names.
    """

    if not MASTER_SKILL_FILE.exists():
        return []

    try:
        with open(
            MASTER_SKILL_FILE,
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

        if item.get("status") != "active":
            continue

        name = item.get("name")

        if not isinstance(name, str):
            continue

        name = name.strip()

        if not name:
            continue

        skills.append(name)

    return skills


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(value: str) -> str:
    """
    Normalize text for comparison.
    """

    if not isinstance(value, str):
        return ""

    value = value.strip()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.casefold()


# ============================================================
# CLEAN SINGLE SKILL
# ============================================================

def _clean_skill(skill: str) -> str:
    """
    Clean one skill entry without identifying specific
    technologies.

    Examples
    --------
    "Experience with Python"
        -> "Python"

    "Proficiency in REST APIs"
        -> "REST APIs"

    "Object-Oriented Programming"
        -> "Object-Oriented Programming"
    """

    if not isinstance(skill, str):
        return ""

    skill = skill.strip()

    if not skill:
        return ""

    # --------------------------------------------------------
    # Remove filler phrases
    # --------------------------------------------------------

    for pattern in FILLER_PATTERNS:

        skill = re.sub(
            pattern,
            "",
            skill,
            flags=re.IGNORECASE,
        )

    # --------------------------------------------------------
    # Normalize whitespace
    # --------------------------------------------------------

    skill = skill.replace(
        "\t",
        " ",
    )

    skill = re.sub(
        r"\s+",
        " ",
        skill,
    ).strip()

    # --------------------------------------------------------
    # Remove surrounding punctuation
    # --------------------------------------------------------

    skill = re.sub(
        r"^[\s,;|/:\\\-–—]+",
        "",
        skill,
    )

    skill = re.sub(
        r"[\s,;|/:\\\-–—]+$",
        "",
        skill,
    )

    return skill.strip()


# ============================================================
# SPLIT EXPLICIT SEPARATORS
# ============================================================

def _split_explicit_separators(
    text: str,
) -> list[str]:
    """
    Split skill expressions using strong separators.

    Examples
    --------
    "Python, FastAPI, Django"
        ->
        ["Python", "FastAPI", "Django"]

    "Python; FastAPI; Django"
        ->
        ["Python", "FastAPI", "Django"]

    "Python | FastAPI | Django"
        ->
        ["Python", "FastAPI", "Django"]

    "PostgreSQL / MySQL"
        ->
        ["PostgreSQL", "MySQL"]
    """

    if not isinstance(text, str):
        return []

    text = text.strip()

    if not text:
        return []

    parts = re.split(
        r"\s*[,;|/]\s*",
        text,
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


# ============================================================
# SPLIT CONNECTORS
# ============================================================

def _split_connectors(
    text: str,
) -> list[str]:
    """
    Split expressions joined using standalone
    'and' or 'or'.

    Examples
    --------
    "Python and Git"
        ->
        ["Python", "Git"]

    "PostgreSQL or MySQL"
        ->
        ["PostgreSQL", "MySQL"]

    "Python, Django and PostgreSQL"
        ->
        ["Python, Django", "PostgreSQL"]
    """

    if not isinstance(text, str):
        return []

    text = text.strip()

    if not text:
        return []

    parts = CONNECTOR_PATTERN.split(
        text
    )

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


# ============================================================
# MASTER SKILL TOKENIZATION
# ============================================================

def _build_master_skill_index():
    """
    Build a normalized master-skill index.

    Multi-word skills are sorted before shorter skills.

    Example:

        Django REST Framework
        Django

    becomes:

        Django REST Framework
        Django

    This is important because the longest valid skill should
    be selected first.
    """

    master_skills = _load_master_skills()

    indexed_skills = []

    for skill in master_skills:

        normalized = _normalize(skill)

        if not normalized:
            continue

        indexed_skills.append(
            (
                normalized,
                skill.strip(),
            )
        )

    # --------------------------------------------------------
    # Longest skills first
    # --------------------------------------------------------

    indexed_skills.sort(
        key=lambda item: (
            len(item[0].split()),
            len(item[0]),
        ),
        reverse=True,
    )

    return indexed_skills


# ============================================================
# MATCH MASTER SKILLS
# ============================================================

def _match_master_skill(
    tokens: list[str],
    start_index: int,
    master_skills,
):
    """
    Find the longest master skill beginning at start_index.

    Example
    -------
    Tokens:

        ["django", "rest", "framework", "postgresql"]

    If the master dictionary contains:

        Django REST Framework

    the function returns:

        ("Django REST Framework", 3)

    Meaning:
        matched skill = Django REST Framework
        consumed tokens = 3
    """

    remaining_tokens = tokens[
        start_index:
    ]

    if not remaining_tokens:
        return None

    remaining_text = " ".join(
        remaining_tokens
    )

    normalized_remaining = _normalize(
        remaining_text
    )

    for normalized_skill, original_skill in master_skills:

        skill_tokens = normalized_skill.split()

        token_count = len(skill_tokens)

        if (
            start_index + token_count
            > len(tokens)
        ):
            continue

        candidate_tokens = tokens[
            start_index:
            start_index + token_count
        ]

        candidate = _normalize(
            " ".join(candidate_tokens)
        )

        if candidate == normalized_skill:

            return (
                original_skill,
                token_count,
            )

    return None


# ============================================================
# SPLIT ADJACENT SKILLS USING MASTER DICTIONARY
# ============================================================

def _split_using_master_dictionary(
    text: str,
) -> list[str]:
    """
    Split adjacent skills using the master dictionary.

    Examples
    --------
    If master dictionary contains:

        Python
        SQL
        MySQL
        Django

    then:

        "Python SQL MySQL Django"

    becomes:

        [
            "Python",
            "SQL",
            "MySQL",
            "Django"
        ]

    Multi-word skills are preserved.

    Example:

        "Django REST Framework PostgreSQL"

    becomes:

        [
            "Django REST Framework",
            "PostgreSQL"
        ]

    IMPORTANT
    ---------
    This function does not contain any technology names.
    """

    if not isinstance(text, str):
        return []

    text = text.strip()

    if not text:
        return []

    master_skills = _build_master_skill_index()

    if not master_skills:
        return [text]

    tokens = text.split()

    if not tokens:
        return []

    result = []

    index = 0

    while index < len(tokens):

        match = _match_master_skill(
            tokens,
            index,
            master_skills,
        )

        if match:

            skill_name, consumed = match

            result.append(
                skill_name
            )

            index += consumed

        else:

            # ------------------------------------------------
            # Unknown token.
            #
            # We do not invent a skill name.
            # We simply keep the token as a candidate.
            # ------------------------------------------------

            result.append(
                tokens[index]
            )

            index += 1

    return result


# ============================================================
# SPLIT SKILL EXPRESSION
# ============================================================

def _split_skill_expression(
    text: str,
) -> list[str]:
    """
    Split a skill expression into individual candidates.

    Processing order
    ----------------
    1. Explicit separators
    2. Connector words
    3. Master-dictionary segmentation

    Examples
    --------
    "Python, FastAPI, Django"
        ->
        [
            "Python",
            "FastAPI",
            "Django"
        ]

    "Python and Git"
        ->
        [
            "Python",
            "Git"
        ]

    "Python SQL MySQL Django"
        ->
        [
            "Python",
            "SQL",
            "MySQL",
            "Django"
        ]

    "Django REST Framework PostgreSQL"
        ->
        [
            "Django REST Framework",
            "PostgreSQL"
        ]

    "Object Oriented Programming Python"
        ->
        [
            "Object Oriented Programming",
            "Python"
        ]

    The exact result depends on the contents of the
    master skill dictionary.
    """

    if not isinstance(text, str):
        return []

    text = text.strip()

    if not text:
        return []

    result = []

    # --------------------------------------------------------
    # Step 1: Explicit separators
    # --------------------------------------------------------

    first_level = _split_explicit_separators(
        text
    )

    for part in first_level:

        # ----------------------------------------------------
        # Step 2: Connectors
        # ----------------------------------------------------

        second_level = _split_connectors(
            part
        )

        for sub_part in second_level:

            # ------------------------------------------------
            # Step 3: Master dictionary
            # ------------------------------------------------

            third_level = (
                _split_using_master_dictionary(
                    sub_part
                )
            )

            result.extend(
                third_level
            )

    return result


# ============================================================
# DEDUPLICATION
# ============================================================

def _append_unique(
    skills: list[str],
    skill: str,
) -> None:
    """
    Add a skill while preventing
    case-insensitive duplicates.
    """

    if not skill:
        return

    normalized = _normalize(
        skill
    )

    for existing in skills:

        if _normalize(existing) == normalized:
            return

    skills.append(skill)


# ============================================================
# PUBLIC SKILL CLEANER
# ============================================================

def clean_skills(skills):
    """
    Clean and structurally split skill entries.

    Responsibilities
    ----------------
    1. Validate input.
    2. Remove filler phrases.
    3. Normalize whitespace.
    4. Remove surrounding punctuation.
    5. Split explicit separators.
    6. Split standalone 'and' / 'or'.
    7. Segment adjacent skills using the master dictionary.
    8. Preserve multi-word skills from the master dictionary.
    9. Remove duplicates.

    IMPORTANT
    ---------
    This function intentionally does NOT maintain a hard-coded
    technology list.

    Technology recognition is driven by:

        master_skill_dictionary.json
    """

    if not skills:
        return []

    if isinstance(skills, str):
        skills = [skills]

    if not isinstance(skills, list):
        return []

    cleaned_skills = []

    for skill_entry in skills:

        if not isinstance(
            skill_entry,
            str,
        ):
            continue

        skill_entry = skill_entry.strip()

        if not skill_entry:
            continue

        # ----------------------------------------------------
        # Remove filler phrases.
        # ----------------------------------------------------

        cleaned_entry = _clean_skill(
            skill_entry
        )

        if not cleaned_entry:
            continue

        # ----------------------------------------------------
        # Split compound expressions.
        # ----------------------------------------------------

        skill_parts = _split_skill_expression(
            cleaned_entry
        )

        # ----------------------------------------------------
        # Clean every resulting candidate.
        # ----------------------------------------------------

        for part in skill_parts:

            cleaned_skill = _clean_skill(
                part
            )

            if not cleaned_skill:
                continue

            _append_unique(
                cleaned_skills,
                cleaned_skill,
            )

    return cleaned_skills