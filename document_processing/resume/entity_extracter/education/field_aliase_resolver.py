"""
field_alias_resolver.py

Responsibilities
----------------
Resolve field-of-study aliases to canonical field names.

Example
-------
CSE
    -> Computer Science

Computer Science and Engineering
    -> Computer Science

Unknown field
    -> Original field value
"""

import json
from pathlib import Path


# =========================================================
# FILE PATH
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ALIAS_FILE = PROJECT_ROOT / "data"/"resume"/"education"/"field_aliases.json"


# =========================================================
# LOAD ALIASES
# =========================================================

def load_field_aliases():
    """
    Load field aliases from JSON.
    """

    if not ALIAS_FILE.exists():
        raise FileNotFoundError(
            f"Field alias file not found: {ALIAS_FILE}"
        )

    with open(
        ALIAS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


FIELD_ALIASES = load_field_aliases()


# =========================================================
# BUILD LOOKUP
# =========================================================

def build_alias_lookup(alias_data):
    """
    Convert:

        {
            "Computer Science": [
                "CSE",
                "Computer Science"
            ]
        }

    into:

        {
            "cse": "Computer Science",
            "computer science": "Computer Science"
        }
    """

    lookup = {}

    for canonical, aliases in alias_data.items():

        # Canonical value itself is also searchable
        lookup[
            canonical.strip().lower()
        ] = canonical

        for alias in aliases:

            if not isinstance(
                alias,
                str
            ):
                continue

            normalized = (
                alias
                .strip()
                .lower()
            )

            if normalized:
                lookup[
                    normalized
                ] = canonical

    return lookup


FIELD_ALIAS_LOOKUP = build_alias_lookup(
    FIELD_ALIASES
)


# =========================================================
# RESOLVE ALIAS
# =========================================================

def resolve_field_alias(field):
    """
    Resolve a field alias to its canonical field name.

    Parameters
    ----------
    field : str | None

    Returns
    -------
    str | None

    Examples
    --------
    >>> resolve_field_alias("CSE")
    'Computer Science'

    >>> resolve_field_alias(
    ...     "Computer Science and Engineering"
    ... )
    'Computer Science'

    >>> resolve_field_alias("Unknown Field")
    'Unknown Field'
    """

    if not field:
        return None

    if not isinstance(
        field,
        str
    ):
        return field

    normalized = (
        field
        .strip()
        .lower()
    )

    if not normalized:
        return None

    return FIELD_ALIAS_LOOKUP.get(
        normalized,
        field.strip()
    )


# =========================================================
# MANUAL TEST
# =========================================================

if __name__ == "__main__":

    test_fields = [
        "CSE",
        "Computer Science and Engineering",
        "Computer Science",
        "ECE",
        "AI/ML",
        "AIML",
        "MBA",
        "Unknown Field"
    ]

    for field in test_fields:

        print(
            f"{field} -> "
            f"{resolve_field_alias(field)}"
        )
