"""
Education extraction pipeline with optional Ollama fallback.

Deterministic extraction remains the primary method.
The LLM is called only when both degree and institution
are unresolved, and its suggestions fill missing fields only.
"""

import logging

from document_processing.resume.entity_extracter.education.education_block_splitter import (
    split_education_blocks,
)
from document_processing.resume.entity_extracter.education.degree_type_extractor import (
    extract_degree_type,
)
from document_processing.resume.entity_extracter.education.degree_aliases_resolver import (
    resolve_degree_alias,
)
from document_processing.resume.entity_extracter.education.institution_extractor import (
    extract_institution,
    extract_board,
    extract_university_from_block,
)
from document_processing.resume.entity_extracter.education.graduation_year_extractor import (
    extract_graduation_year,
)
from document_processing.resume.entity_extracter.education.field_of_study_extractor import (
    extract_field_of_study,
)
from document_processing.resume.entity_extracter.education.field_aliase_resolver import (
    resolve_field_alias,
)
from document_processing.resume.entity_extracter.education.education_post_processor import (
    post_process_education,
)
from document_processing.resume.entity_extracter.education.school_degree_classifier import (
    classify_school_degree,
)
from document_processing.common.llm_fallback_service import (
    llm_fallback_service,
)

logger = logging.getLogger(__name__)


EDUCATION_FALLBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "degree_type": {"type": ["string", "null"]},
        "field_of_study": {"type": ["string", "null"]},
        "institution": {"type": ["string", "null"]},
        "university": {"type": ["string", "null"]},
        "board": {"type": ["string", "null"]},
        "graduation_year": {"type": ["integer", "null"]},
    },
    "required": [
        "degree_type",
        "field_of_study",
        "institution",
        "university",
        "board",
        "graduation_year",
    ],
    "additionalProperties": False,
}


EDUCATION_FIELDS = (
    "degree_type",
    "field_of_study",
    "institution",
    "university",
    "board",
    "graduation_year",
)


def _education_llm_fallback(block):
    """
    Extract possible education fields from one block.

    Returns an empty dictionary if the LLM is unavailable,
    returns invalid data, or fails to produce a valid response.
    """

    if not isinstance(block, str) or not block.strip():
        return {}

    result = llm_fallback_service.extract_json(
        entity_name="education",
        text=block,
        output_schema=EDUCATION_FALLBACK_SCHEMA,
    )

    if not isinstance(result, dict):
        return {}

    suggestion = {}

    for field in EDUCATION_FIELDS:
        value = result.get(field)

        if isinstance(value, str):
            value = value.strip() or None

        if field == "graduation_year":
            # bool is a subclass of int in Python, so reject it explicitly.
            if isinstance(value, bool):
                value = None
            elif value is not None:
                if (
                    not isinstance(value, int)
                    or not 1900 <= value <= 2100
                ):
                    value = None

        elif value is not None and not isinstance(value, str):
            value = None

        suggestion[field] = value

    return suggestion


def _fill_missing_education_fields(
    education_record,
    suggestion,
):
    """
    Fill only missing values.

    Existing deterministic extraction results are never overwritten.
    """

    for field in EDUCATION_FIELDS:
        current_value = education_record.get(field)

        if current_value is None or (
            isinstance(current_value, str)
            and not current_value.strip()
        ):
            suggested_value = suggestion.get(field)

            if suggested_value is not None:
                education_record[field] = suggested_value

    return education_record


def education_pipeline(education_section):
    """
    Extract education records from a detected education section.

    Output structure remains compatible with the existing pipeline.
    """

    # Step 1: split the section into individual education blocks.
    blocks = split_education_blocks(education_section)

    education_data = []

    logger.debug("Education blocks: %r", blocks)

    # Step 2: extract fields from each block.
    for block in blocks:

        # ----------------------------------------------------
        # DEGREE
        # ----------------------------------------------------

        degree_type = extract_degree_type(block)

        degree_type = resolve_degree_alias(degree_type)

        # ----------------------------------------------------
        # SCHOOL CLASSIFICATION
        # ----------------------------------------------------

        if not degree_type:
            degree_type = classify_school_degree(block)

        # ----------------------------------------------------
        # UNIVERSITY
        # ----------------------------------------------------

        university_result = extract_university_from_block(block)

        university = None

        if university_result:
            university = university_result.get("value")

        # ----------------------------------------------------
        # INSTITUTION
        # ----------------------------------------------------

        institution = extract_institution(
            block,
            university_result,
        )

        # ----------------------------------------------------
        # BOARD
        # ----------------------------------------------------

        board = extract_board(block)

        # ----------------------------------------------------
        # GRADUATION YEAR
        # ----------------------------------------------------

        graduation_year = extract_graduation_year(block)

        # ----------------------------------------------------
        # FIELD OF STUDY
        # ----------------------------------------------------

        field_of_study = extract_field_of_study(block)

        field_of_study = resolve_field_alias(field_of_study)

        logger.debug(
            "Education field resolution: field=%r block=%r",
            field_of_study,
            block,
        )

        # ----------------------------------------------------
        # BUILD INITIAL RECORD
        # ----------------------------------------------------

        education_record = {
            "degree_type": degree_type,
            "field_of_study": field_of_study,
            "institution": institution,
            "university": university,
            "board": board,
            "graduation_year": graduation_year,
        }

        # ----------------------------------------------------
        # CONDITIONAL LLM FALLBACK
        # ----------------------------------------------------
        # Do not call the LLM if either a degree or institution
        # has already been identified by deterministic extraction.
        # ----------------------------------------------------

        if not degree_type and not institution:
            logger.info(
                "Degree and institution unresolved; "
                "trying education LLM fallback"
            )

            suggestion = _education_llm_fallback(block)

            education_record = _fill_missing_education_fields(
                education_record,
                suggestion,
            )

        education_data.append(education_record)

    # Step 3: run the existing post-processing logic.
    education_data = post_process_education(education_data)

    return education_data