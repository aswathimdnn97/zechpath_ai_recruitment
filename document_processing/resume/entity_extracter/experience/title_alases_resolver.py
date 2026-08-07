"""
title_alias_resolver.py

Responsibilities
----------------
1. Load title_aliases.json
2. Normalize job title aliases
3. Return canonical job titles
"""

import json
from pathlib import Path

# ----------------------------------------------------
# Project Root
# ----------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

# ----------------------------------------------------
# Alias File
# ----------------------------------------------------

ALIAS_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "job_titles"
    / "job_title_aliases.json"
)
# ----------------------------------------------------
# Load Aliases
# ----------------------------------------------------

def load_title_aliases():
    """
    Returns
    -------
    dict
    """

    with open(ALIAS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ----------------------------------------------------
# Resolve Alias
# ----------------------------------------------------

def resolve_title_alias(title):
    """
    Parameters
    ----------
    title : str

    Returns
    -------
    str
    """

    if not title:
        return None

    aliases = load_title_aliases()

    return aliases.get(
        title.lower().strip(),
        title
    )


# ----------------------------------------------------
# Resolve Multiple Titles
# ----------------------------------------------------

def resolve_title_aliases(titles):
    """
    Parameters
    ----------
    titles : list[str]

    Returns
    -------
    list[str]
    """

    if not titles:
        return []

    resolved = []

    seen = set()

    for title in titles:

        canonical = resolve_title_alias(title)

        if canonical.lower() not in seen:

            seen.add(canonical.lower())

            resolved.append(canonical)

    return resolved