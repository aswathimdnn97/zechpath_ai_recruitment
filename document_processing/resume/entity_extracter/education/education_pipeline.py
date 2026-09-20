from document_processing.resume.entity_extracter.education.education_block_splitter import (
    split_education_blocks
)

from document_processing.resume.entity_extracter.education.degree_type_extractor import (
    extract_degree_type
)

from document_processing.resume.entity_extracter.education.degree_aliases_resolver import (
    resolve_degree_alias
)

from document_processing.resume.entity_extracter.education.institution_extractor import (
    extract_institution,
    extract_board,
    extract_university_from_block,
)

from document_processing.resume.entity_extracter.education.graduation_year_extractor import (
    extract_graduation_year
)

from document_processing.resume.entity_extracter.education.field_of_study_extractor import (
    extract_field_of_study
)

from document_processing.resume.entity_extracter.education.field_aliase_resolver import (
    resolve_field_alias
)

from document_processing.resume.entity_extracter.education.education_post_processor import (
    post_process_education
)

from document_processing.resume.entity_extracter.education.school_degree_classifier import (
    classify_school_degree
)


def education_pipeline(education_section):

    # ========================================================
    # STEP 1
    # SPLIT EDUCATION SECTION
    # ========================================================

    blocks = split_education_blocks(
        education_section
    )

    education_data = []

    # ========================================================
    # STEP 2
    # PROCESS EACH EDUCATION BLOCK
    # ========================================================

    for block in blocks:

        # ----------------------------------------------------
        # DEGREE
        # ----------------------------------------------------

        degree_type = extract_degree_type(
            block
        )

        degree_type = resolve_degree_alias(
            degree_type
        )

        # ----------------------------------------------------
        # SCHOOL CLASSIFICATION
        # ----------------------------------------------------

        if not degree_type:

            degree_type = classify_school_degree(
                block
            )

        # ----------------------------------------------------
        # UNIVERSITY
        #
        # Detect ONLY ONCE.
        # ----------------------------------------------------

        university_result = (
            extract_university_from_block(
                block
            )
        )

        university = None

        if university_result:

            university = (
                university_result.get(
                    "value"
                )
            )

        # ----------------------------------------------------
        # INSTITUTION
        #
        # Pass the already detected university result.
        # This prevents duplicate detection and ensures the
        # university is removed before institution extraction.
        # ----------------------------------------------------

        institution = extract_institution(
            block,
            university_result
        )

        # ----------------------------------------------------
        # BOARD
        # ----------------------------------------------------

        board = extract_board(
            block
        )

        # ----------------------------------------------------
        # GRADUATION YEAR
        # ----------------------------------------------------

        graduation_year = (
            extract_graduation_year(
                block
            )
        )

        # ----------------------------------------------------
        # FIELD OF STUDY
        # ----------------------------------------------------

        field_of_study = (
            extract_field_of_study(
                block
            )
        )

        field_of_study = (
            resolve_field_alias(
                field_of_study
            )
        )

        # ----------------------------------------------------
        # BUILD EDUCATION RECORD
        # ----------------------------------------------------

        education_data.append({

            "degree_type":
                degree_type,

            "field_of_study":
                field_of_study,

            "institution":
                institution,

            "university":
                university,

            "board":
                board,

            "graduation_year":
                graduation_year,

        })

    # ========================================================
    # STEP 3
    # POST PROCESS
    # ========================================================

    education_data = post_process_education(
        education_data
    )

    return education_data