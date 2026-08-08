"""
school_degree_classifier.py

Classifies school-level education records.

Examples
--------
All India Senior School Certificate Exam
    -> Higher Secondary

All India Secondary School Examination
    -> Secondary
"""

import re


# =========================================================
# HIGHER SECONDARY
# =========================================================

HIGHER_SECONDARY_KEYWORDS = [
    "all india senior school certificate",
    "senior school certificate",
    "senior secondary",
    "higher secondary",
    "higher secondary certificate",
    "class xii",
    "class 12",
    "12th",
    "xii",
]


# =========================================================
# SECONDARY
# =========================================================

SECONDARY_KEYWORDS = [
    "all india secondary school examination",
    "secondary school examination",
    "secondary examination",
    "secondary school",
    "class x",
    "class 10",
    "10th",
]


def _normalize_text(text):
    """Normalize text for matching."""

    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()


def classify_school_degree(block):
    """
    Classify a school education block.

    Parameters
    ----------
    block : list[str]

    Returns
    -------
    str | None

    Returns:
        "Higher Secondary"
        "Secondary"
        None
    """

    if not block:
        return None

    # -----------------------------------------------------
    # Combine all lines because the qualification can
    # appear in the first line while board information
    # appears in another line.
    # -----------------------------------------------------

    text = " ".join(
        _normalize_text(line)
        for line in block
        if line
    )

    # -----------------------------------------------------
    # Higher Secondary
    # -----------------------------------------------------

    if any(
        keyword in text
        for keyword in HIGHER_SECONDARY_KEYWORDS
    ):
        return "Higher Secondary"

    # -----------------------------------------------------
    # Secondary
    # -----------------------------------------------------

    if any(
        keyword in text
        for keyword in SECONDARY_KEYWORDS
    ):
        return "Secondary"

    return None

