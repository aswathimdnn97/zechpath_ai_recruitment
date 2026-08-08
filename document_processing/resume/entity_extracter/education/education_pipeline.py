from document_processing.resume.entity_extracter.education.education_block_splitter import split_education_blocks
from document_processing.resume.entity_extracter.education.degree_type_extractor import extract_degree_type
from document_processing.resume.entity_extracter.education.degree_aliases_resolver import resolve_degree_alias
from document_processing.resume.entity_extracter.education.institution_extractor import (
    extract_institution,
    extract_board,
    extract_university,
)
from document_processing.resume.entity_extracter.education.graduation_year_extractor import extract_graduation_year
from document_processing.resume.entity_extracter.education.field_of_study_extractor import extract_field_of_study
from document_processing.resume.entity_extracter.education.field_aliase_resolver import resolve_field_alias
from document_processing.resume.entity_extracter.education.education_post_processor import post_process_education
from document_processing.resume.entity_extracter.education.education_relevence_logic import (filter_education_blocks)
from document_processing.resume.entity_extracter.education.school_degree_classifier import classify_school_degree

def education_pipeline(education_section):

    # -----------------------------------------------------
    # Step 1: Split education section
    # -----------------------------------------------------

    blocks = split_education_blocks(
        education_section
    )
 

    education_data = []

    # -----------------------------------------------------
    # Step 2: Extract entities from each block
    # -----------------------------------------------------

    for block in blocks:

        degree_type = extract_degree_type(block)

        degree_type = resolve_degree_alias(
            degree_type
        )

        # School classification
        if not degree_type:
            degree_type = classify_school_degree(
                block
            )

        institution = extract_institution(block)

        university = extract_university(
            block,
            institution
        )

        board = extract_board(block)

        graduation_year = extract_graduation_year(
            block
        )

        field_of_study = extract_field_of_study(
            block
        )

        field_of_study = resolve_field_alias(
            field_of_study
        )

        education_data.append({
            "degree_type": degree_type,
            "field_of_study": field_of_study,
            "institution": institution,
            "university": university,
            "board": board,
            "graduation_year": graduation_year,
        })

    print("\n========== BEFORE POST PROCESSOR ==========")

    for i, record in enumerate(education_data, 1):
        print(f"\nEducation {i}:")
        print(record)

    print("\n===========================================")
    # -----------------------------------------------------
    # Step 3: Post-process education
    # -----------------------------------------------------

    education_data = post_process_education(
        education_data
    )

    return education_data

