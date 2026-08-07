"""
company_alias_resolver.py

Responsibilities
----------------
1. Load company_aliases.json
2. Resolve company aliases
3. Keep unknown companies unchanged
4. Remove duplicates
"""

import json
from pathlib import Path

# --------------------------------------------------
# Project Root
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

# --------------------------------------------------
# Alias File
# --------------------------------------------------

ALIAS_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "companies"
    / "company_aliases.json"
)

# --------------------------------------------------
# Load Alias Dictionary
# --------------------------------------------------

def load_company_aliases():
    """
    Returns
    -------
    dict
    """
    with open(ALIAS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

# --------------------------------------------------
# Build Alias Lookup
# --------------------------------------------------

def build_alias_lookup():
    """
    Build alias -> canonical lookup.

    Example
    -------
    {
        "infosys ltd": "Infosys",
        "infosys limited": "Infosys",
        "google india": "Google"
    }
    """

    aliases = load_company_aliases()

    lookup = {}

    for canonical_name, alias_list in aliases.items():

        # Canonical name itself
        lookup[canonical_name.lower()] = canonical_name

        # Every alias
        for alias in alias_list:
            lookup[alias.lower()] = canonical_name

    return lookup

# --------------------------------------------------
# Resolve Company Aliases
# --------------------------------------------------

def resolve_company_aliases(candidate_companies):
    """
    Parameters
    ----------
    candidate_companies : list[str]

    Returns
    -------
    list[str]
    """

    if not candidate_companies:
        return []

    # Flatten one level if required
    if isinstance(candidate_companies[0], list):
        candidate_companies = candidate_companies[0]

    alias_lookup = build_alias_lookup()

    resolved = []

    seen = set()

    for company in candidate_companies:

        company = company.strip()

        canonical = alias_lookup.get(
            company.lower(),
            company          # Unknown company → keep original
        )

        if canonical not in seen:

            seen.add(canonical)

            resolved.append(canonical)

    return resolved