"""
experience_pipeline.py

Combines all experience extraction modules
and creates structured experience data.

Responsibilities
----------------
This pipeline extracts experience-specific information:

    - Job title
    - Company
    - Duration
    - Total experience
    - Description
    - Location
    - Employment type
    - Department

Technical skill extraction is handled centrally by:

    document_processing.resume.entity_extracter.skill.skill_extractor

This prevents duplicate skill extraction logic between
Experience and the main Resume pipeline.
"""


# ============================================================
# EXPERIENCE BLOCK SPLITTER
# ============================================================

from document_processing.resume.entity_extracter.experience.experince_block_splitter import (
    split_experience_blocks
)


# ============================================================
# TITLE
# ============================================================

from document_processing.resume.entity_extracter.experience.title_extractor import (
    extract_titles
)

from document_processing.resume.entity_extracter.experience.title_alases_resolver import (
    resolve_title_alias
)

from document_processing.resume.entity_extracter.experience.title_validator import (
    validate_title
)


# ============================================================
# COMPANY
# ============================================================

from document_processing.resume.entity_extracter.experience.company_extractor import (
    extract_companies
)

from document_processing.resume.entity_extracter.experience.company_alias_resolver import (
    resolve_company_aliases
)

from document_processing.resume.entity_extracter.experience.company_validator import (
    validate_companies
)


# ============================================================
# DURATION
# ============================================================

from document_processing.resume.entity_extracter.experience.duration_calculator import (
    extract_duration
)

from document_processing.resume.entity_extracter.experience.experience_calculator import (
    calculate_experience
)


# ============================================================
# DESCRIPTION
# ============================================================

from document_processing.resume.entity_extracter.experience.description_extraction import (
    extract_description
)


# ============================================================
# LOCATION
# ============================================================

from document_processing.resume.entity_extracter.experience.location_extractor import (
    extract_location
)


# ============================================================
# EMPLOYMENT TYPE
# ============================================================

from document_processing.resume.entity_extracter.experience.employement_type import (
    extract_employment_type
)


# ============================================================
# DEPARTMENT
# ============================================================

from document_processing.resume.entity_extracter.experience.department_extractor import (
    extract_department
)


# ============================================================
# EXPERIENCE EXTRACTOR
# ============================================================

def experience_extractor(experience_section):
    """
    Extract structured experience information.

    Args:
        experience_section:
            Experience section detected from the resume.

    Returns:
        List of structured experience objects.
    """

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not experience_section:
        return []

    # --------------------------------------------------------
    # Split experience section into individual blocks
    # --------------------------------------------------------

    experience_blocks = split_experience_blocks(
        experience_section
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

        # ====================================================
        # TITLE
        # ====================================================

        titles = extract_titles(
            block
        )

        raw_title = (
            titles[0]
            if titles
            else None
        )

        resolved_title = (
            resolve_title_alias(
                raw_title
            )
            if raw_title
            else None
        )

        title = (
            validate_title(
                resolved_title
            )
            if resolved_title
            else None
        )

        # ====================================================
        # COMPANY
        # ====================================================

        companies = extract_companies(
            block
        )

        resolved_companies = (
            resolve_company_aliases(
                companies
            )
        )

        validated_companies = (
            validate_companies(
                resolved_companies
            )
        )

        # Take the first validated company
        company = (
            validated_companies[0]
            if validated_companies
            else None
        )

        # ====================================================
        # DURATION
        # ====================================================

        duration = extract_duration(
            block
        )

        total_experience = (
            calculate_experience(
                duration
            )
        )

        # ====================================================
        # DESCRIPTION
        # ====================================================

        description = extract_description(
            block
        )

        # ====================================================
        # LOCATION
        # ====================================================

        location = extract_location(
            block
        )

        # ====================================================
        # EMPLOYMENT TYPE
        # ====================================================

        employment_type = (
            extract_employment_type(
                block
            )
        )

        # ====================================================
        # DEPARTMENT
        # ====================================================

        department = (
            extract_department(
                block
            )
        )

        # ====================================================
        # FINAL EXPERIENCE OBJECT
        # ====================================================

        experiences.append({

            "title": title,

            "company": company,

            "duration": duration,

            "total_experience": total_experience,

            "location": location,

            "employment_type": employment_type,

            "department": department,

            "description": description

        })

    return experiences