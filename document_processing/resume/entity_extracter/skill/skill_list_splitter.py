"""
skill_list_splitter.py

Responsibilities
----------------
1. Split a dedicated Skills section into individual skill candidates.
2. Handle common separators.
3. Remove category labels such as:
       Backend:
       Frontend:
       Database:
       Programming Languages:
4. Preserve multi-word skill names.
5. Preserve technology names such as:
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


import re


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
    r"^[\s•●▪◦‣*-]+"
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
# CLEAN ONE SKILL ITEM
# ============================================================

def _clean_skill_item(skill):
    """
    Clean one extracted skill candidate.

    This function intentionally does not normalize
    spelling or synonyms.
    """

    if not isinstance(skill, str):
        return ""

    skill = skill.strip()

    if not skill:
        return ""

    # Remove bullet characters.
    skill = BULLET_PATTERN.sub("", skill).strip()

    # Remove category prefix if still present.
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
# SPLIT ONE LINE
# ============================================================

def _split_line(line):
    """
    Split one Skills-section line.

    Examples
    --------
    "Backend: Django, FastAPI, Flask"

        ->
        ["Django", "FastAPI", "Flask"]

    "Frontend: React | JavaScript | HTML | CSS"

        ->
        ["React", "JavaScript", "HTML", "CSS"]

    "Database: PostgreSQL; MongoDB"

        ->
        ["PostgreSQL", "MongoDB"]
    """

    if not isinstance(line, str):
        return []

    line = line.strip()

    if not line:
        return []

    # Remove bullet.
    line = BULLET_PATTERN.sub(
        "",
        line,
    ).strip()

    # Remove category prefix.
    line = CATEGORY_PREFIX_PATTERN.sub(
        "",
        line,
    ).strip()

    if not line:
        return []

    # --------------------------------------------------------
    # Split only on explicit separators.
    #
    # IMPORTANT:
    # Do NOT split on whitespace.
    #
    # This preserves:
    #     Machine Learning
    #     Object Oriented Programming
    #     Microsoft SQL Server
    # --------------------------------------------------------

    parts = SEPARATOR_PATTERN.split(line)

    cleaned = []

    for part in parts:

        skill = _clean_skill_item(part)

        if skill:
            cleaned.append(skill)

    return cleaned


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

    IMPORTANT
    ---------
    This function returns RAW candidates.

    It does not perform:

        spelling correction
        synonym resolution
        validation
        fuzzy matching
        stack expansion
    """

    if not lines:
        return []

    # --------------------------------------------------------
    # Accept a single string.
    # --------------------------------------------------------

    if isinstance(lines, str):
        lines = lines.splitlines()

    # --------------------------------------------------------
    # Make sure input is a list.
    # --------------------------------------------------------

    if not isinstance(lines, list):
        return []

    skills = []

    # --------------------------------------------------------
    # Flatten nested lists.
    # --------------------------------------------------------

    def flatten(items):

        for item in items:

            if isinstance(item, list):

                yield from flatten(item)

            elif isinstance(item, str):

                if item.strip():
                    yield item

    # --------------------------------------------------------
    # Process every line.
    # --------------------------------------------------------

    for line in flatten(lines):

        extracted = _split_line(line)

        skills.extend(extracted)

    # --------------------------------------------------------
    # Remove duplicates while preserving order.
    # --------------------------------------------------------

    unique_skills = []

    seen = set()

    for skill in skills:

        key = skill.lower().strip()

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)

        unique_skills.append(skill)

    return unique_skills