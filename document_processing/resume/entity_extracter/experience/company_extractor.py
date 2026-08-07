"""
company_extractor.py

Responsibilities
----------------
1. Extract raw company candidates.
2. Ignore dates.
3. Ignore responsibility lines.
4. Ignore technical skill lines.
5. Ignore job titles.
6. Return raw company candidates.
"""

import json
import re
from pathlib import Path

# --------------------------------------------------
# Project Root
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]

# --------------------------------------------------
# Files
# --------------------------------------------------

SUFFIX_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "companies"
    / "company_suffix.json"
)

TITLE_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "job_titles"
    / "master_job_titles.json"
)

# --------------------------------------------------
# Load JSON
# --------------------------------------------------

def load_suffixes():
    with open(SUFFIX_FILE, encoding="utf-8") as file:
        return json.load(file)


def load_job_titles():
    with open(TITLE_FILE, encoding="utf-8") as file:
        return json.load(file)


# --------------------------------------------------
# Action Words
# --------------------------------------------------

ACTION_WORDS = {
    "developed",
    "designed",
    "implemented",
    "created",
    "built",
    "worked",
    "responsible",
    "improved",
    "enhanced",
    "maintained",
    "managed",
    "optimized",
    "tested",
    "using",
    "knowledge",
    "experience"
}

# --------------------------------------------------
# Technical Words
# --------------------------------------------------

TECH_WORDS = {
    "python",
    "java",
    "javascript",
    "html",
    "css",
    "mysql",
    "mongodb",
    "react",
    "node",
    "php",
    "api",
    "rest",
    "git",
    "github"
}

# --------------------------------------------------
# Date Detection
# --------------------------------------------------

def is_date(line):

    return bool(
        re.search(
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
            r"|present"
            r"|\d{4}",
            line.lower()
        )
    )

# --------------------------------------------------
# Company Extraction
# --------------------------------------------------

def extract_companies(experience_section):

    if not experience_section:
        return []

    # Flatten one level
    if isinstance(experience_section[0], list):
        experience_section = experience_section[0]

    suffixes = load_suffixes()

    titles = {
        item["name"].lower()
        for item in load_job_titles()
    }

    companies = []

    for line in experience_section:

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        # Skip dates
        if is_date(line):
            continue

        # Skip job titles
        if lower in titles:
            continue

        # Skip responsibility lines
        if any(word in lower for word in ACTION_WORDS):
            continue

        # Skip technical lines
        tech_count = sum(
            word in lower
            for word in TECH_WORDS
        )

        if tech_count >= 2:
            continue

        # Company suffix
        if any(suffix.lower() in lower for suffix in suffixes):
            companies.append(line)
            continue

        # Proper noun heuristic
        words = line.split()

        if (
            2 <= len(words) <= 5 and
            sum(
                word[0].isupper()
                for word in words
                if word and word[0].isalpha()
            ) >= 2
        ):
            companies.append(line)

    # Remove duplicates
    return list(dict.fromkeys(companies))