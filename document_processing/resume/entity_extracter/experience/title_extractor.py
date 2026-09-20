"""
title_extractor.py

Responsibilities
----------------
1. Extract raw job titles from one experience block
2. Remove dates
3. Ignore company names
4. Ignore description lines
5. Return candidate job titles

No validation is performed here.
"""

import json
import re
from pathlib import Path

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
# Load Companies
# ----------------------------------------------------

def load_companies():

    with open(COMPANY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# ----------------------------------------------------
# Remove Date
# ----------------------------------------------------

def remove_date(text):
    """
    Removes trailing date information.

    Example
    -------
    Software Engineer Jan 2022 - Present

    becomes

    Software Engineer
    """

    pattern = (
        r"\s*"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r".*"
    )

    return re.sub(
        pattern,
        "",
        text,
        flags=re.IGNORECASE
    ).strip()


# ----------------------------------------------------
# Description Detection
# ----------------------------------------------------

def is_description(text):

    keywords = [

        "developed",
        "prepared",
        "worked",
        "responsible",
        "implemented",
        "created",
        "designed",
        "using",
        "maintained",
        "improved",
        "enhanced",
        "built",
        "collaborated",
        "collaborate",
        "collaboration",
        "partnered",
        "communicate",
        "assess",
        "troubleshoot",
        "contributed",
        "explored",
        "presented",
        "wrote",
        "documented",
        "managed",
        "tested",
        "led",
        "leading",
        "delivered",
        "building",
        "designed",
        "performed",
        "completed",
        "handled",
        "supported",
        "executed",
        "updated"

    ]

    text = text.lower()

    if len(text.split()) >= 5 and text.rstrip().endswith((".", ";", ":")):
        return True

    return any(
        word in text
        for word in keywords
    )


def looks_like_title_text(text):
    """Heuristic to classify a text as a likely role/title."""

    lower = text.lower()
    title_tokens = [
        "developer",
        "engineer",
        "analyst",
        "manager",
        "consultant",
        "architect",
        "specialist",
        "scientist",
        "intern",
        "trainee",
        "lead",
        "assistant",
        "designer",
    ]

    return any(token in lower for token in title_tokens)


def split_title_company(line):
    """Strip company names from title-company patterns like 'Backend Trainee - Code Nest Academy'."""

    if not isinstance(line, str):
        return line

    text = line.strip()
    if not text:
        return text

    for separator in [" - ", " – ", " — ", " | "]:
        if separator not in text:
            continue

        left, right = [part.strip() for part in text.split(separator, 1)]
        if not left or not right:
            continue

        if looks_like_title_text(left) and not looks_like_title_text(right):
            return left

    return line


def looks_like_location(text):
    """Recognize simple city/state strings like 'Kochi, Kerala'."""

    if not isinstance(text, str):
        return False

    candidate = text.strip()
    if not candidate:
        return False

    return bool(re.fullmatch(r"[A-Z][a-zA-Z]+\s*,\s*[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*", candidate))


def looks_like_company(text):
    """Heuristic for company names that should not become title candidates."""

    lower = text.lower()

    company_keywords = [
        "pvt",
        "private",
        "limited",
        "ltd",
        "inc",
        "corp",
        "soft",
        "solutions",
        "technology",
        "technologies",
        "systems",
        "services",
        "labs",
        "group",
        "industries",
        "consulting",
        "network",
    ]

    if not any(keyword in lower for keyword in company_keywords):
        return False

    title_keywords = [
        "engineer",
        "developer",
        "manager",
        "analyst",
        "consultant",
        "architect",
        "specialist",
        "scientist",
        "intern",
        "trainee",
        "lead",
        "designer",
    ]

    return not any(keyword in lower for keyword in title_keywords)


# ----------------------------------------------------
# Extract Titles
# ----------------------------------------------------

def extract_titles(experience_block):
    """
    Parameters
    ----------
    experience_block : list[str]

    Returns
    -------
    list[str]
    """

    if not experience_block:
        return []

    # Flatten one level if needed
    if (
        isinstance(experience_block, list)
        and experience_block
        and isinstance(experience_block[0], list)
    ):
        experience_block = experience_block[0]

    company_lookup = {

        company["name"].lower()

        for company in load_companies()

    }

    titles = []

    seen = set()

    for line in experience_block:

        line = line.strip()

        if not line:
            continue

        # Split title-company lines before checking whether the full line looks
        # like a company, since the company portion may contain title-like words.
        line = split_title_company(line)
        if not line:
            continue

        # Skip description lines
        if is_description(line):
            continue

        # Skip company-like lines that should not be job titles
        if looks_like_company(line):
            continue

        # Skip city/state lines that are not roles
        if looks_like_location(line):
            continue

        # Remove dates
        line = remove_date(line)

        if not line:
            continue

        lower = line.lower()

        # Skip if exactly a company
        if lower in company_lookup:
            continue

        # Skip if location-like
        if "," in line and len(line.split()) > 2:
            continue

        if lower not in seen:

            seen.add(lower)

            titles.append(line)

    return titles