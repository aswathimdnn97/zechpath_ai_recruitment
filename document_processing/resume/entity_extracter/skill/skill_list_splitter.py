import re

from document_processing.resume.entity_extracter.skill.synonym_resolver import (
    resolve_synonyms,
)


def split_skill_line(lines):
    """
    Split skill lines into individual skill items.

    Input can be:
        - list of strings
        - single string

    Example:
        [
            "Backend: Django, FastAPI, Flask",
            "Frontend: React, JavaScript, HTML, CSS",
            "Database: PostgreSQL, MongoDB"
        ]

    Returns:
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
    """

    if not lines:
        return []

    # -------------------------------------------------------
    # Accept a single string.
    # -------------------------------------------------------

    if isinstance(lines, str):
        lines = [lines]

    # -------------------------------------------------------
    # Make sure we have a list.
    # -------------------------------------------------------

    if not isinstance(lines, list):
        return []

    skills = []

    for line in lines:

        if isinstance(line, list):
            skills.extend(
                split_skill_line(line)
            )
            continue

        if not isinstance(line, str):
            continue

        line = line.strip()

        if not line:
            continue

        # ---------------------------------------------------
        # Remove category prefix.
        #
        # Backend: Django, FastAPI
        # Frontend: React, JavaScript
        # Database: PostgreSQL
        # ---------------------------------------------------

        line = re.sub(
            r"^[^:]+:\s*",
            "",
            line,
        )

        # ---------------------------------------------------
        # Split comma-separated skills.
        # ---------------------------------------------------

        parts = re.split(
            r",",
            line,
        )

        for part in parts:

            skill = part.strip()

            if not skill:
                continue

            skills.append(skill)

    # Resolve aliases to canonical names (e.g., "Fast API" -> "FastAPI").
    skills_raw = list(skills)

    try:
        resolved = resolve_synonyms(skills_raw)
    except Exception:
        return skills_raw

    # Preserve plural originals when alias canonical form is singular
    final = []

    for original, canonical in zip(skills_raw, resolved):

        o = original.strip()

        # check if original appears plural (simple heuristic)
        is_plural = o.endswith("s") or o.lower().endswith("apis")

        if is_plural and not canonical.lower().endswith("s"):
            final.append(o)
        else:
            final.append(canonical)

    return final
