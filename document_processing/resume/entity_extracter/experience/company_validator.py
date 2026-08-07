"""
company_validator.py

Responsibilities
----------------
1. Load company_dictionary.json
2. Validate company names
3. Exact matching
4. Fuzzy matching
5. Calculate confidence score
6. Return structured company objects
"""

import json
from pathlib import Path

from rapidfuzz import process, fuzz

# ----------------------------------------------------
# Project Root
# ----------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

# ----------------------------------------------------
# Company Dictionary
# ----------------------------------------------------

COMPANY_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "companies"
    / "company_dictionary.json"
)

# ----------------------------------------------------
# Load Company Dictionary
# ----------------------------------------------------

def load_company_dictionary():
    """
    Load company dictionary.

    Returns
    -------
    list[dict]
    """

    with open(COMPANY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ----------------------------------------------------
# Validate Companies
# ----------------------------------------------------

def validate_companies(candidate_companies, threshold=90):
    """
    Validate company names against the master company dictionary.

    Parameters
    ----------
    candidate_companies : list[str]

    threshold : int
        Minimum fuzzy matching score.

    Returns
    -------
    list[dict]
    """

    if not candidate_companies:
        return []

    # Flatten one level if required
    if (
        isinstance(candidate_companies, list)
        and len(candidate_companies) > 0
        and isinstance(candidate_companies[0], list)
    ):
        candidate_companies = candidate_companies[0]

    company_dictionary = load_company_dictionary()

    # ---------------------------------------
    # Exact lookup
    # ---------------------------------------

    exact_lookup = {}

    for company in company_dictionary:

        exact_lookup[company["name"].lower()] = company

    company_names = list(exact_lookup.keys())

    validated = []

    seen = set()

    # ---------------------------------------
    # Validate each company
    # ---------------------------------------

    for candidate in candidate_companies:

        if not candidate:
            continue

        candidate = candidate.strip()

        if candidate.lower() in seen:
            continue

        seen.add(candidate.lower())

        # -----------------------------------
        # Exact Match
        # -----------------------------------

        if candidate.lower() in exact_lookup:

            company = exact_lookup[candidate.lower()]

            validated.append({

                "company_id": company["company_id"],
                "company": company["name"],
                "industry": company.get("industry", "Unknown"),
                "matched_by": "exact",
                "confidence": 100

            })

            continue

        # -----------------------------------
        # Fuzzy Match
        # -----------------------------------

        result = process.extractOne(

            candidate.lower(),
            company_names,
            scorer=fuzz.WRatio

        )

        if result:

            matched_name = result[0]
            score = result[1]

            if score >= threshold:

                company = exact_lookup[matched_name]

                validated.append({

                    "company_id": company["company_id"],
                    "company": company["name"],
                    "industry": company.get("industry", "Unknown"),
                    "matched_by": "fuzzy",
                    "confidence": round(score)

                })

                continue

        # -----------------------------------
        # Unknown Company
        # -----------------------------------

        validated.append({

            "company_id": None,
            "company": candidate,
            "industry": "Unknown",
            "matched_by": "none",
            "confidence": 0

        })

    return validated


# ----------------------------------------------------
# Testing
# ----------------------------------------------------

if __name__ == "__main__":

    sample = [
        "Acciojob",
        "Infosys",
        "Infosis",
        "Google",
        "Zechpath AI"
    ]

    result = validate_companies(sample)

    from pprint import pprint

    pprint(result)