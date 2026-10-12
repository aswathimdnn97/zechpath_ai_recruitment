
"""
experience_pipeline.py

Combines experience extraction modules and creates structured experience data.

Optional profiling measures the time spent in each extraction stage.
"""

import logging
from time import perf_counter

# ============================================================
# EXPERIENCE BLOCK SPLITTER
# ============================================================

from document_processing.resume.entity_extracter.experience.experince_block_splitter import (
    split_experience_blocks,
)

# ============================================================
# TITLE
# ============================================================

from document_processing.resume.entity_extracter.experience.title_extractor import (
    extract_titles,
)
from document_processing.resume.entity_extracter.experience.title_alases_resolver import (
    resolve_title_alias,
)
from document_processing.resume.entity_extracter.experience.title_validator import (
    validate_title,
)

# ============================================================
# COMPANY
# ============================================================

from document_processing.resume.entity_extracter.experience.company_extractor import (
    extract_companies,
)
from document_processing.resume.entity_extracter.experience.company_alias_resolver import (
    resolve_company_aliases,
)
from document_processing.resume.entity_extracter.experience.company_validator import (
    validate_companies,
)

# ============================================================
# DURATION
# ============================================================

from document_processing.resume.entity_extracter.experience.duration_calculator import (
    extract_duration,
)
from document_processing.resume.entity_extracter.experience.experience_calculator import (
    calculate_experience,
)

# ============================================================
# DESCRIPTION
# ============================================================

from document_processing.resume.entity_extracter.experience.description_extraction import (
    extract_description,
)

# ============================================================
# LOCATION
# ============================================================

from document_processing.resume.entity_extracter.experience.location_extractor import (
    extract_location,
)

# ============================================================
# EMPLOYMENT TYPE
# ============================================================

from document_processing.resume.entity_extracter.experience.employement_type import (
    extract_employment_type,
)

# ============================================================
# DEPARTMENT
# ============================================================

from document_processing.resume.entity_extracter.experience.department_extractor import (
    extract_department,
)

logger = logging.getLogger(__name__)


# ============================================================
# EXPERIENCE EXTRACTOR
# ============================================================

def experience_extractor(experience_section, profile=True):
    """
    Extract structured experience information.

    Args:
        experience_section:
            Experience section detected from the resume.

        profile:
            If True, print one aggregate timing summary after extraction.

    Returns:
        List of structured experience dictionaries.
    """

    pipeline_start = perf_counter()

    if not experience_section:
        return []

    # --------------------------------------------------------
    # Initialize profiling counters
    # --------------------------------------------------------

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
        "description_extraction": 0.0,
        "location_extraction": 0.0,
        "employment_type_extraction": 0.0,
        "department_extraction": 0.0,
    }

    # --------------------------------------------------------
    # Split experience section into blocks
    # --------------------------------------------------------

    start = perf_counter()
    experience_blocks = split_experience_blocks(experience_section)
    timings["block_splitting"] += perf_counter() - start

    logger.debug(
        "Experience block splitting: block_count=%d blocks=%r",
        len(experience_blocks),
        experience_blocks,
    )

    if not experience_blocks:
        return []

    experiences = []

    # ========================================================
    # PROCESS EACH EXPERIENCE BLOCK
    # ========================================================

    for block in experience_blocks:
        if not block:
            continue

        # ----------------------------------------------------
        # TITLE EXTRACTION
        # ----------------------------------------------------

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

        logger.debug(
            "Experience title extraction: raw_candidates=%r selected=%r",
            titles,
            raw_title,
        )

        # ----------------------------------------------------
        # COMPANY EXTRACTION
        # ----------------------------------------------------

        start = perf_counter()
        companies = extract_companies(block)
        timings["company_extraction"] += perf_counter() - start

        start = perf_counter()
        resolved_companies = resolve_company_aliases(companies)
        timings["company_alias_resolution"] += perf_counter() - start

        start = perf_counter()
        validated_companies = validate_companies(resolved_companies)
        timings["company_validation"] += perf_counter() - start

        company = validated_companies[0] if validated_companies else None

        logger.debug(
            "Experience company extraction: candidates=%r "
            "resolved=%r validated=%r selected=%r",
            companies,
            resolved_companies,
            validated_companies,
            company,
        )

        # ----------------------------------------------------
        # DURATION
        # ----------------------------------------------------

        start = perf_counter()
        duration = extract_duration(block)
        timings["duration_extraction"] += perf_counter() - start

        start = perf_counter()
        total_experience = calculate_experience(duration)
        timings["experience_calculation"] += perf_counter() - start

        # ----------------------------------------------------
        # DESCRIPTION
        # ----------------------------------------------------

        start = perf_counter()
        description = extract_description(block)
        timings["description_extraction"] += perf_counter() - start

        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        start = perf_counter()
        location = extract_location(block)
        timings["location_extraction"] += perf_counter() - start

        # ----------------------------------------------------
        # EMPLOYMENT TYPE
        # ----------------------------------------------------

        start = perf_counter()
        employment_type = extract_employment_type(block)
        timings["employment_type_extraction"] += perf_counter() - start

        # ----------------------------------------------------
        # DEPARTMENT
        # ----------------------------------------------------

        start = perf_counter()
        department = extract_department(block)
        timings["department_extraction"] += perf_counter() - start

        # ----------------------------------------------------
        # FINAL EXPERIENCE OBJECT
        # ----------------------------------------------------

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

    # ========================================================
    # PROFILING SUMMARY
    # ========================================================

    total_elapsed = perf_counter() - pipeline_start

    if profile:
        print("\n" + "=" * 72)
        print("EXPERIENCE PIPELINE PROFILE")
        print("=" * 72)
        print(f"Experience blocks : {len(experience_blocks)}")
        print(f"Extracted records : {len(experiences)}")
        print(f"Total time        : {total_elapsed:.6f} s")
        print("-" * 72)
        print(f"{'Stage':35s} {'Total (s)':>12s} {'Calls':>8s}")
        print("-" * 72)

        calls_per_block = {
            "block_splitting": 1,
        }

        for stage in timings:
            calls = (
                calls_per_block.get(stage, len(experiences))
            )
            print(
                f"{stage:35s} "
                f"{timings[stage]:12.6f} "
                f"{calls:8d}"
            )

        measured_total = sum(timings.values())

        print("-" * 72)
        print(f"{'Sum of measured stages':35s} {measured_total:12.6f}")
        print(
            f"{'Other pipeline overhead':35s} "
            f"{max(0.0, total_elapsed - measured_total):12.6f}"
        )
        print("=" * 72 + "\n")

    return experiences