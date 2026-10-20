"""
Experience extraction pipeline.

Design:
1. Deterministic extraction first.
2. Validate extracted values before accepting them.
3. Use the shared LLM fallback for missing or invalid fields.
4. Existing title/company validators remain authoritative.
5. Duration calculation remains deterministic.
6. LLM failures never crash resume parsing.
7. Description output is consistently a string or None.
"""

import logging
from time import perf_counter

from document_processing.resume.entity_extracter.experience.experince_block_splitter import (
    split_experience_blocks,
)
from document_processing.resume.entity_extracter.experience.title_extractor import (
    extract_titles,
)
from document_processing.resume.entity_extracter.experience.title_alases_resolver import (
    resolve_title_alias,
)
from document_processing.resume.entity_extracter.experience.title_validator import (
    validate_title,
)
from document_processing.resume.entity_extracter.experience.company_extractor import (
    extract_companies,
)
from document_processing.resume.entity_extracter.experience.company_alias_resolver import (
    resolve_company_aliases,
)
from document_processing.resume.entity_extracter.experience.company_validator import (
    validate_companies,
)
from document_processing.resume.entity_extracter.experience.duration_calculator import (
    extract_duration,
)
from document_processing.resume.entity_extracter.experience.experience_calculator import (
    calculate_experience,
)
from document_processing.resume.entity_extracter.experience.description_extraction import (
    extract_description,
    clean_experience_description,
)
from document_processing.resume.entity_extracter.experience.location_extractor import (
    extract_location,
    validate_location,
)
from document_processing.resume.entity_extracter.experience.employement_type import (
    extract_employment_type,
)
from document_processing.resume.entity_extracter.experience.department_extractor import (
    extract_department,
)
from document_processing.common.llm_fallback_service import (
    llm_fallback_service,
)


logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# LLM SCHEMA
# ------------------------------------------------------------------

EXPERIENCE_LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "company": {"type": "string"},
        "location": {"type": "string"},
        "employment_type": {"type": "string"},
        "department": {"type": "string"},
        "description": {"type": "string"},
    },
    "required": [
        "title",
        "company",
        "location",
        "employment_type",
        "department",
        "description",
    ],
    "additionalProperties": False,
}


# ------------------------------------------------------------------
# CANONICAL VALUES
# ------------------------------------------------------------------

EMPLOYMENT_TYPE_ALIASES = {
    "full time": "Full-time",
    "full-time": "Full-time",
    "fulltime": "Full-time",
    "part time": "Part-time",
    "part-time": "Part-time",
    "parttime": "Part-time",
    "contract": "Contract",
    "contractual": "Contract",
    "intern": "Internship",
    "internship": "Internship",
    "temporary": "Temporary",
    "permanent": "Permanent",
    "freelance": "Freelance",
    "self employed": "Self-employed",
    "self-employed": "Self-employed",
    "remote": "Remote",
    "hybrid": "Hybrid",
}

DEPARTMENT_ALIASES = {
    "engineering": "Engineering",
    "software engineering": "Engineering",
    "software development": "Engineering",
    "development": "Engineering",
    "information technology": "Information Technology",
    "it": "Information Technology",
    "technology": "Technology",
    "human resources": "Human Resources",
    "hr": "Human Resources",
    "sales": "Sales",
    "marketing": "Marketing",
    "finance": "Finance",
    "accounting": "Accounting",
    "operations": "Operations",
    "customer support": "Customer Support",
    "customer service": "Customer Service",
    "quality assurance": "Quality Assurance",
    "qa": "Quality Assurance",
    "research and development": "Research and Development",
    "research": "Research",
    "data science": "Data Science",
    "analytics": "Analytics",
    "product management": "Product Management",
    "design": "Design",
    "administration": "Administration",
}


# ------------------------------------------------------------------
# TEXT HELPERS
# ------------------------------------------------------------------

def _block_to_text(block):
    """Convert an experience block into text for the LLM."""

    if isinstance(block, str):
        return block.strip()

    if isinstance(block, list):
        return "\n".join(
            item.strip()
            for item in block
            if isinstance(item, str) and item.strip()
        )

    if isinstance(block, dict):
        parts = []

        for value in block.values():
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())

            elif isinstance(value, list):
                parts.extend(
                    item.strip()
                    for item in value
                    if isinstance(item, str) and item.strip()
                )

        return "\n".join(parts)

    return ""


def _clean_llm_value(value):
    """Return a non-empty string or None."""

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    if value.casefold() in {
        "unknown",
        "not available",
        "not specified",
        "n/a",
        "null",
        "none",
        "not applicable",
    }:
        return None

    return value


def _is_missing(value):
    """Check whether a value is missing or empty."""

    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0

    return False


def _normalize_description(value):
    """
    Normalize descriptions to one string or None.

    The deterministic description extractor may return a list of lines.
    """

    if value is None:
        return None

    if isinstance(value, list):
        parts = [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]
        value = " ".join(parts)

    if not isinstance(value, str):
        return None

    value = " ".join(value.split())

    return value or None


def _merge_missing_fields(deterministic, fallback):
    """
    Fill missing fields from validated fallback suggestions.

    Existing deterministic values are never overwritten.
    """

    result = dict(deterministic)

    if not isinstance(fallback, dict):
        fallback = {}

    fields = (
        "title",
        "company",
        "location",
        "employment_type",
        "department",
        "description",
    )

    for field in fields:
        current = result.get(field)
        suggested = fallback.get(field)

        if field == "description":
            current = _normalize_description(current)
            suggested = _normalize_description(suggested)

        if _is_missing(current) and not _is_missing(suggested):
            result[field] = suggested
        elif field == "description":
            result[field] = current

    result["description"] = _normalize_description(
        result.get("description")
    )

    return result


# ------------------------------------------------------------------
# DESCRIPTION CLEANUP
# ------------------------------------------------------------------

def _description_lines(value):
    """Convert a description into clean, non-empty lines."""

    if value is None:
        return []

    if isinstance(value, str):
        lines = value.splitlines()

    elif isinstance(value, list):
        lines = []

        for item in value:
            if isinstance(item, str):
                lines.extend(item.splitlines())

    else:
        return []

    return [
        line.strip()
        for line in lines
        if isinstance(line, str) and line.strip()
    ]


def _normalize_for_comparison(value):
    """Normalize text for duplicate detection."""

    if not isinstance(value, str):
        return ""

    value = value.casefold().replace("&", " and ")
    value = "".join(
        char if char.isalnum() else " "
        for char in value
    )

    return " ".join(value.split())


def _remove_header_duplicates(
    description,
    *,
    title=None,
    company=None,
    location=None,
    duration=None,
):
    """
    Remove known metadata from the beginning of a description.

    Returns a list of cleaned description lines.
    """

    lines = _description_lines(description)

    if not lines:
        return []

    combined = " ".join(lines)

    cleaned = clean_experience_description(
        combined,
        title=title,
        company=company,
        location=location,
        duration=duration,
    )

    return [cleaned] if cleaned else []


# ------------------------------------------------------------------
# VALIDATED FALLBACK HELPERS
# ------------------------------------------------------------------

def _validate_fallback_title(value):
    """Resolve and validate an LLM-suggested job title."""

    value = _clean_llm_value(value)

    if not value:
        return None

    try:
        resolved = resolve_title_alias(value)

        if not resolved:
            return None

        return validate_title(resolved)

    except Exception:
        logger.debug(
            "Could not validate fallback job title.",
            exc_info=True,
        )
        return None


def _validate_fallback_company(value):
    """Resolve and validate an LLM-suggested company name."""

    value = _clean_llm_value(value)

    if not value:
        return None

    try:
        resolved = resolve_company_aliases([value])

        if not resolved:
            return None

        validated = validate_companies(resolved)

        return validated[0] if validated else None

    except Exception:
        logger.debug(
            "Could not validate fallback company name.",
            exc_info=True,
        )
        return None


def _validate_employment_type(value):
    """
    Validate and normalize an employment-type suggestion.
    """

    value = _clean_llm_value(value)

    if not value:
        return None

    try:
        validated = extract_employment_type(value)

        if validated:
            return validated

    except Exception:
        logger.debug(
            "Could not validate employment type with the extractor.",
            exc_info=True,
        )

    normalized = " ".join(value.casefold().split())

    return EMPLOYMENT_TYPE_ALIASES.get(normalized)


def _validate_department(value):
    """
    Validate and normalize a department suggestion.
    """

    value = _clean_llm_value(value)

    if not value:
        return None

    try:
        validated = extract_department(value)

        if validated:
            return validated

    except Exception:
        logger.debug(
            "Could not validate department with the extractor.",
            exc_info=True,
        )

    normalized = " ".join(value.casefold().split())

    return DEPARTMENT_ALIASES.get(normalized)


# ------------------------------------------------------------------
# LLM FALLBACK
# ------------------------------------------------------------------

def _llm_experience_fallback(block):
    """
    Recover missing experience fields using the shared LLM service.

    Returns cleaned suggestions or an empty dictionary.
    LLM failures never interrupt deterministic parsing.
    """

    block_text = _block_to_text(block)

    if not block_text:
        return {}

    prompt_text = (
        "Extract employment information from the following resume "
        "experience block. Use only information explicitly supported "
        "by the text. Do not invent a company, job title, location, "
        "employment type, department, or responsibility. A location "
        "must be a place name or an explicitly stated work arrangement "
        "such as Remote or Hybrid. Never use a responsibility sentence "
        "as a location. Do not include the job title, company name, or "
        "location in the description unless it is part of an actual "
        "responsibility. Return an empty string for any missing field."
        "\n\nEXPERIENCE BLOCK:\n"
        f"{block_text}"
    )

    try:
        response = llm_fallback_service.extract_json(
            entity_name="work_experience",
            text=prompt_text,
            output_schema=EXPERIENCE_LLM_SCHEMA,
            document_type="resume",
        )

        if not isinstance(response, dict):
            return {}

        return {
            field: _clean_llm_value(response.get(field))
            for field in EXPERIENCE_LLM_SCHEMA["properties"]
        }

    except Exception:
        logger.warning(
            "LLM experience fallback failed; using deterministic results.",
            exc_info=True,
        )
        return {}


# ------------------------------------------------------------------
# EXPERIENCE PIPELINE
# ------------------------------------------------------------------

def experience_extractor(experience_section, profile=True):
    """
    Extract structured experience records.

    Deterministic extraction runs first. Missing fields may be recovered
    by the LLM, but valid deterministic values are never overwritten.

    Duration and total-experience calculations remain deterministic.
    """

    pipeline_start = perf_counter()

    if not experience_section:
        return []

    timings = {
        "block_splitting": 0.0,
        "title_extraction": 0.0,
        "title_alias_resolution": 0.0,
        "title_validation": 0.0,
        "company_extraction": 0.0,
        "company_alias_resolution": 0.0,
        "company_validation": 0.0,
        "duration_extraction": 0.0,
        "experience_calculation": 0.0,
        "location_extraction": 0.0,
        "description_extraction": 0.0,
        "employment_type_extraction": 0.0,
        "department_extraction": 0.0,
        "llm_fallback": 0.0,
    }

    # --------------------------------------------------------------
    # SPLIT EXPERIENCE SECTION
    # --------------------------------------------------------------

    start = perf_counter()
    experience_blocks = split_experience_blocks(experience_section)
    timings["block_splitting"] += perf_counter() - start

    logger.debug(
        "Experience block splitting: block_count=%d",
        len(experience_blocks),
    )

    if not experience_blocks:
        return []

    experiences = []

    # --------------------------------------------------------------
    # PROCESS EACH EXPERIENCE BLOCK
    # --------------------------------------------------------------

    for block in experience_blocks:
        if not block:
            continue

        # ----------------------------------------------------------
        # TITLE
        # ----------------------------------------------------------

        start = perf_counter()
        titles = extract_titles(block)
        timings["title_extraction"] += perf_counter() - start

        raw_title = titles[0] if titles else None

        start = perf_counter()
        resolved_title = (
            resolve_title_alias(raw_title)
            if raw_title
            else None
        )
        timings["title_alias_resolution"] += perf_counter() - start

        start = perf_counter()
        title = (
            validate_title(resolved_title)
            if resolved_title
            else None
        )
        timings["title_validation"] += perf_counter() - start

        # ----------------------------------------------------------
        # COMPANY
        # ----------------------------------------------------------

        start = perf_counter()
        companies = extract_companies(block)
        timings["company_extraction"] += perf_counter() - start

        start = perf_counter()
        resolved_companies = resolve_company_aliases(companies)
        timings["company_alias_resolution"] += perf_counter() - start

        start = perf_counter()
        validated_companies = validate_companies(resolved_companies)
        timings["company_validation"] += perf_counter() - start

        company = (
            validated_companies[0]
            if validated_companies
            else None
        )

        # ----------------------------------------------------------
        # DURATION
        # Keep duration and total-experience calculations deterministic.
        # ----------------------------------------------------------

        start = perf_counter()
        duration = extract_duration(block)
        timings["duration_extraction"] += perf_counter() - start

        start = perf_counter()
        total_experience = calculate_experience(duration)
        timings["experience_calculation"] += perf_counter() - start

        # ----------------------------------------------------------
        # LOCATION
        # Extract location BEFORE description because the description
        # cleaner needs the extracted location to remove header metadata.
        # ----------------------------------------------------------

        start = perf_counter()
        raw_location = extract_location(block)
        location = validate_location(raw_location)
        timings["location_extraction"] += perf_counter() - start

        # ----------------------------------------------------------
        # DESCRIPTION
        # All known metadata is now available to the description extractor.
        # ----------------------------------------------------------

        start = perf_counter()

        description = extract_description(
            block,
            title=title,
            company=company,
            location=location,
            duration=duration,
        )

        description = _normalize_description(description)

        timings["description_extraction"] += perf_counter() - start

        # ----------------------------------------------------------
        # EMPLOYMENT TYPE
        # ----------------------------------------------------------

        start = perf_counter()
        employment_type = extract_employment_type(block)
        timings["employment_type_extraction"] += perf_counter() - start

        # ----------------------------------------------------------
        # DEPARTMENT
        # ----------------------------------------------------------

        start = perf_counter()
        department = extract_department(block)
        timings["department_extraction"] += perf_counter() - start

        # ----------------------------------------------------------
        # LLM FALLBACK
        # ----------------------------------------------------------

        deterministic = {
            "title": title,
            "company": company,
            "location": location,
            "employment_type": employment_type,
            "department": department,
            "description": description,
        }

        if any(
            _is_missing(value)
            for value in deterministic.values()
        ):
            start = perf_counter()
            suggestions = _llm_experience_fallback(block)
            timings["llm_fallback"] += perf_counter() - start

            if not isinstance(suggestions, dict):
                suggestions = {}

            fallback = {}

            if _is_missing(title):
                fallback["title"] = _validate_fallback_title(
                    suggestions.get("title")
                )

            if _is_missing(company):
                fallback["company"] = _validate_fallback_company(
                    suggestions.get("company")
                )

            if _is_missing(location):
                suggested_location = _clean_llm_value(
                    suggestions.get("location")
                )

                try:
                    fallback["location"] = (
                        validate_location(suggested_location)
                        if suggested_location
                        else None
                    )
                except Exception:
                    logger.debug(
                        "Could not validate fallback location.",
                        exc_info=True,
                    )
                    fallback["location"] = None

            if _is_missing(employment_type):
                fallback["employment_type"] = (
                    _validate_employment_type(
                        suggestions.get("employment_type")
                    )
                )

            if _is_missing(department):
                fallback["department"] = _validate_department(
                    suggestions.get("department")
                )

            if _is_missing(description):
                fallback["description"] = _normalize_description(
                    suggestions.get("description")
                )

            merged = _merge_missing_fields(
                deterministic,
                fallback,
            )

            title = merged["title"]
            company = merged["company"]
            location = merged["location"]
            employment_type = merged["employment_type"]
            department = merged["department"]
            description = merged["description"]

        # ----------------------------------------------------------
        # FINAL DESCRIPTION CLEANUP
        # Pass all extracted metadata, including duration.
        # This also cleans an LLM-provided description if fallback was used.
        # ----------------------------------------------------------

        description_lines = _remove_header_duplicates(
            description,
            title=title,
            company=company,
            location=location,
            duration=duration,
        )

        # Public output contract: description is str | None.
        description = _normalize_description(description_lines)

        # ----------------------------------------------------------
        # FINAL EXPERIENCE RECORD
        # ----------------------------------------------------------

        experiences.append({
            "title": title,
            "company": company,
            "duration": duration,
            "total_experience": total_experience,
            "location": location,
            "employment_type": employment_type,
            "department": department,
            "description": description,
        })

    # --------------------------------------------------------------
    # PROFILING
    # --------------------------------------------------------------

    total_elapsed = perf_counter() - pipeline_start

    if profile:
        print("\n" + "=" * 72)
        print("EXPERIENCE PIPELINE PROFILE")
        print("=" * 72)
        print(f"Experience blocks : {len(experience_blocks)}")
        print(f"Extracted records : {len(experiences)}")
        print(f"Total time        : {total_elapsed:.6f} s")
        print("-" * 72)
        print(f"{'Stage':35s} {'Total (s)':>12s}")
        print("-" * 72)

        for stage, elapsed in timings.items():
            print(f"{stage:35s} {elapsed:12.6f}")

        measured_total = sum(timings.values())

        print("-" * 72)
        print(
            f"{'Sum of measured stages':35s} "
            f"{measured_total:12.6f}"
        )
        print(
            f"{'Other pipeline overhead':35s} "
            f"{max(0.0, total_elapsed - measured_total):12.6f}"
        )
        print("=" * 72 + "\n")

    return experiences
