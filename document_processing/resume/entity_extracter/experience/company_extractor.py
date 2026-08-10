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
    "collaborated",
    "collaborate",
    "collaboration",
    "partnered",
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
    pattern = r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b|\bpresent\b|\b\d{4}\b"

    return bool(re.search(pattern, line.lower()))

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

    title_keywords = {
        word
        for title in titles
        for word in title.split()
        if word
    }
    title_keywords.update(
        {
            "senior",
            "junior",
            "lead",
            "principal",
            "staff",
            "associate",
            "intern",
            "director",
            "vice",
            "vp",
            "head",
            "assistant",
        }
    )

    companies = []

    for line in experience_section:

        line = line.strip()

        if not line:
            continue

        lower = line.lower()

        # Split title — company or title - company patterns (dash surrounded by spaces)
        if re.search(r"\s[—–-]\s", line):
            parts = [p.strip() for p in re.split(r"\s[—–-]\s+", line) if p.strip()]

            if len(parts) >= 2:
                company_candidate = parts[-1]

                lower_part = company_candidate.lower()

                if not is_date(company_candidate):
                    if lower_part not in titles and not any(word in lower_part for word in ACTION_WORDS):
                        if sum(1 for word in company_candidate.split() if word and word[0].isupper()) >= 1 or any(suffix.lower() in lower_part for suffix in suffixes):
                            companies.append(company_candidate)
                            # continue to next line
                            continue
        # Skip dates
        if is_date(line):
            continue

        # Skip job titles
        if lower in titles:
            continue

        words = line.split()
        if (
            1 <= len(words) <= 6 and
            any(word in title_keywords for word in lower.split())
        ):
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

        # Multi-company line separated by commas or slashes
        if "," in line or "/" in line:
            candidate_parts = [
                part.strip()
                for part in re.split(r"[,/]+", line)
                if part.strip()
            ]

            for part in candidate_parts:
                lower_part = part.lower()
                tech_count_part = sum(
                    word in lower_part
                    for word in TECH_WORDS
                )

                if is_date(part):
                    continue
                if lower_part in titles:
                    continue
                if any(word in lower_part for word in ACTION_WORDS):
                    continue
                if tech_count_part >= 2:
                    continue
                if any(suffix.lower() in lower_part for suffix in suffixes):
                    companies.append(part)
                    continue
                if sum(1 for word in part.split() if word and word[0].isupper()) >= 2:
                    companies.append(part)
            continue

        # Company suffix
        if any(suffix.lower() in lower for suffix in suffixes):
            companies.append(line)
            continue

        # Proper noun heuristic
        words = line.split()

        if (
            2 <= len(words) <= 6 and
            sum(1 for word in words if word and word[0].isupper()) >= 2
        ):
            companies.append(line)

    # Remove duplicates
    return list(dict.fromkeys(companies))