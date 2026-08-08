"""
degree_alias_resolver.py

Responsibilities

1. Convert degree aliases into canonical names.
2. Return normalized degree.
"""

import json
from pathlib import Path

# -------------------------------------------------------
# Project Root
# -------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ALIAS_FILE = (
    PROJECT_ROOT
    / "data"
    /"resume"
    / "education"
    / "degree_aliases.json"
)
# -------------------------------------------------------
# Load Alias Dictionary
# -------------------------------------------------------

def load_degree_aliases():
    """
    Returns
    -------
    dict
    """

    with open(ALIAS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

# -------------------------------------------------------
# Resolve Degree Alias
# -------------------------------------------------------

def resolve_degree_alias(degree):
    """
    Parameters
    ----------
    degree : str

    Returns
    -------
    str | None
    """

    if not degree:
        return None

    aliases = load_degree_aliases()

    lookup = degree.strip().lower()

    return aliases.get(lookup, degree)

# -------------------------------------------------------
# Testing
# -------------------------------------------------------

if __name__ == "__main__":

    print(resolve_degree_alias("B.Tech"))
    print(resolve_degree_alias("MBA"))
    print(resolve_degree_alias("Bachelor of Technology"))