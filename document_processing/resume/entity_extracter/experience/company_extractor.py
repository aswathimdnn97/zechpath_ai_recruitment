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
    "experience",
    "added",
    "participated",
    "contributed",
    "led",
    "coordinated",
    "facilitated",
    "organized",
    "executed",
    "deployed",
    "configured",
    "supported",
    "monitored",
    "analyzed",
    "researched",
    "reviewed",
    "documented",
    "resolved",
    "performed",
    "conducted",
    "achieved",
    "established",
    "integrated"
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


def strip_dates_from_company(line):
    """Remove date ranges and months from company name.
    
    Examples:
        'Tech Nova Labs Jan 2026 - Apr 2026' -> 'Tech Nova Labs'
        'ABC Corp Jan 2020 - Present' -> 'ABC Corp'
    """
    if not isinstance(line, str):
        return line
    
    # Remove date range patterns like "Jan 2026 - Apr 2026" or "Jan 2020 - Present"
    line = re.sub(r"\s*\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b\s+\d{4}\s*[-–—]\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b\s+\d{4}|present|current)\b", "", line, flags=re.IGNORECASE)
    
    # Remove trailing months with years
    line = re.sub(r"\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b.*$", "", line, flags=re.IGNORECASE)
    
    # Remove trailing year ranges
    line = re.sub(r"\s+\d{4}\s*[-–—]\s*(?:\d{4}|present|current)\b.*$", "", line, flags=re.IGNORECASE)
    
    return line.strip()

# --------------------------------------------------
# Company Extraction
# --------------------------------------------------

def split_title_company(line):
    """Return the company portion from a title-company string."""

    if not isinstance(line, str):
        return None

    text = line.strip()
    if not text:
        return None

    for separator in [" - ", " – ", " — ", " | "]:
        if separator not in text:
            continue

        left, right = [part.strip() for part in text.split(separator, 1)]
        if not left or not right:
            continue

        left_lower = left.lower()
        right_lower = right.lower()

        title_keywords = [
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

        if any(keyword in left_lower for keyword in title_keywords) and not any(keyword in right_lower for keyword in title_keywords):
            return right

    return None


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

        company_from_title = split_title_company(line)
        if company_from_title:
            cleaned = strip_dates_from_company(company_from_title)
            if cleaned:
                companies.append(cleaned)
            continue

        lower = line.lower()

        # Handle "Title | Company | Dates" pattern (with pipe separator)
        if "|" in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            
            if len(parts) >= 2:
                # Pattern: Title Company | Dates
                # Extract the part before the pipe (contains title and company)
                first_part = parts[0]
                
                # Look for separators like " - ", " – ", " — " (with spaces)
                # These typically separate job title from company name
                title_company_sep = re.search(r"\s[\-–—]+\s", first_part)
                
                if title_company_sep:
                    # Split on the separator found
                    sep_start = title_company_sep.start()
                    company_candidate = first_part[sep_start:].strip()
                    # Remove leading separator
                    company_candidate = re.sub(r"^[\-–—\s]+", "", company_candidate).strip()
                    
                    lower_part = company_candidate.lower()
                    
                    if company_candidate and not is_date(company_candidate):
                        if lower_part not in titles and not any(word in lower_part for word in ACTION_WORDS):
                            if sum(1 for word in company_candidate.split() if word and word[0].isupper()) >= 1 or any(suffix.lower() in lower_part for suffix in suffixes):
                                cleaned = strip_dates_from_company(company_candidate)
                                if cleaned:
                                    companies.append(cleaned)
                                continue
                else:
                    # No standard separator found, but line has pipe - check if this looks like a company line
                    # Handle corrupted characters by checking for pattern: word word | word word
                    # Split first_part looking for common separators including non-ASCII
                    import unicodedata
                    # Try splitting by looking for sequences of special characters
                    parts_by_special = re.split(r"[^\w\s\.]+", first_part)
                    parts_by_special = [p.strip() for p in parts_by_special if p.strip()]
                    
                    if len(parts_by_special) >= 2:
                        # Assume the later parts are company (after any special separator)
                        company_candidate = " ".join(parts_by_special[-2:]) if len(parts_by_special) > 1 else parts_by_special[-1]
                        lower_part = company_candidate.lower()
                        
                        if company_candidate and not is_date(company_candidate):
                            if lower_part not in titles and not any(word in lower_part for word in ACTION_WORDS):
                                if sum(1 for word in company_candidate.split() if word and word[0].isupper()) >= 1 or any(suffix.lower() in lower_part for suffix in suffixes):
                                    cleaned = strip_dates_from_company(company_candidate)
                                    if cleaned:
                                        companies.append(cleaned)
                                    continue

        # Split title — company or title - company patterns (dash surrounded by spaces)
        if re.search(r"\s[\-–—]\s", line):
            title_company_sep = re.search(r"\s[\-–—]+\s", line)
            if title_company_sep:
                sep_start = title_company_sep.start()
                # Extract from after the separator to end of line or pipe
                remainder = line[sep_start:].strip()
                # Remove leading separators
                company_candidate = re.sub(r"^[\-–—\s]+", "", remainder).strip()
                
                # If there's a pipe, get only the part before it
                if "|" in company_candidate:
                    company_candidate = company_candidate.split("|")[0].strip()
                
                lower_part = company_candidate.lower()
                
                if not is_date(company_candidate):
                    if lower_part not in titles and not any(word in lower_part for word in ACTION_WORDS):
                        if sum(1 for word in company_candidate.split() if word and word[0].isupper()) >= 1 or any(suffix.lower() in lower_part for suffix in suffixes):
                            cleaned = strip_dates_from_company(company_candidate)
                            if cleaned:
                                companies.append(cleaned)
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
                    cleaned = strip_dates_from_company(part)
                    if cleaned:
                        companies.append(cleaned)
                    continue
                if sum(1 for word in part.split() if word and word[0].isupper()) >= 2:
                    cleaned = strip_dates_from_company(part)
                    if cleaned:
                        companies.append(cleaned)
            continue

        # Company suffix
        if any(suffix.lower() in lower for suffix in suffixes):
            cleaned = strip_dates_from_company(line)
            if cleaned:
                companies.append(cleaned)
            continue

        # Proper noun heuristic
        words = line.split()

        if (
            2 <= len(words) <= 6 and
            sum(1 for word in words if word and word[0].isupper()) >= 2
        ):
            cleaned = strip_dates_from_company(line)
            if cleaned:
                companies.append(cleaned)

    # Remove duplicates
    return list(dict.fromkeys(companies))