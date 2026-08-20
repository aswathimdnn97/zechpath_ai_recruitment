from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.resume.resume_normalizer import normalize_text
from document_processing.common.handling_layout import fix_layout
from document_processing.common.json_writer import save_resume

from document_processing.resume.section_detector import detect_sections
from document_processing.resume.headings import headings

from document_processing.resume.text_reconstruction import (
    text_reconstructor
)

from document_processing.resume.entity_extracter.personal_information.personal_information_extractor import (
    extract_personal_information
)

from document_processing.resume.entity_extracter.skill.skill_extractor import (
    extract_skill
)

from document_processing.resume.entity_extracter.skill.skill_list_splitter import (
    split_skill_line
)

from document_processing.resume.entity_extracter.skill.synonym_resolver import (
    resolve_synonyms
)

from document_processing.resume.entity_extracter.skill.spelling_resolver import (
    resolve_spelling
)

from document_processing.resume.entity_extracter.skill.master_skill_validator import (
    validate_skills
)

from document_processing.resume.entity_extracter.skill.stack_resolver import (
    expand_skill_stacks
)

from document_processing.resume.entity_extracter.experience.experinece_pipeline import (
    experience_extractor
)

from document_processing.resume.entity_extracter.education.education_pipeline import (
    education_pipeline
)

from document_processing.resume.entity_extracter.certifications.certification_pipeline import (
    certification_pipeline
)

from document_processing.resume.entity_extracter.projects.project_extraction_pipeline import (
    extract_projects
)

from document_processing.resume.candidate_profile.candidate_profile_builder import (
    build_candidate_profile
)

from scoring.bias_mitigation.personal_attribute_masker import (
    mask_personal_attributes
)

from scoring.bias_mitigation.bias_indicator_detector import (
    detect_bias_indicators
)


def resume_pipeline(file):
    """
    Complete resume processing pipeline.

    Steps:
        1. Extract raw text
        2. Clean text
        3. Fix layout
        4. Reconstruct text
        5. Normalize text
        6. Detect resume sections
        7. Extract personal information
        8. Extract and normalize skills
        9. Extract experience
        10. Extract education
        11. Extract certifications
        12. Extract projects
        13. Build candidate profile
        14. Detect bias indicators
        15. Create scoring-safe masked profile

    Returns:
        {
            "candidate_id": "...",
            "masked_profile": {...},
            "bias_report": {...},
            "original_profile": {...}
        }
    """

    # ============================================================
    # 1. RAW TEXT EXTRACTION
    # ============================================================

    raw_text = extract_raw_text(file)

    if not raw_text:
        raise ValueError(
            f"Could not extract text from resume: {file}"
        )


    # ============================================================
    # 2. CLEAN TEXT
    # ============================================================

    cleaned_text = clean_text(raw_text)


    # ============================================================
    # 3. FIX LAYOUT
    # ============================================================

    handled_text = fix_layout(
        cleaned_text
    )


    # ============================================================
    # 4. TEXT RECONSTRUCTION
    # ============================================================

    reconstructed_text = text_reconstructor(
        handled_text
    )


    # ============================================================
    # 5. NORMALIZATION
    # ============================================================

    normalized_text = normalize_text(
        reconstructed_text
    )


    # ============================================================
    # 6. SECTION DETECTION
    # ============================================================

    section_detected_text = detect_sections(
        normalized_text,
        headings
    )


    # ============================================================
    # 7. PERSONAL INFORMATION
    # ============================================================

    personal_information = extract_personal_information(
        normalized_text
    )


    # ============================================================
    # 8. SKILLS
    # ============================================================

    skill_section = section_detected_text.get(
        "skills",
        ""
    )

    skill_splitter = split_skill_line(
        skill_section
    )

    if skill_splitter:
        extracted_skills = skill_splitter
    else:
        extracted_skills = extract_skill(
            skill_section
        )

    # Spelling correction
    spelling_resolved_skills = resolve_spelling(
        extracted_skills
    )

    # Synonym / alias resolution
    synonym_resolved_skills = resolve_synonyms(
        spelling_resolved_skills
    )

    # Validate against master skill dictionary
    validated_skills = validate_skills(
        synonym_resolved_skills
    )

    # Expand valid skill stacks
    stack_skills = expand_skill_stacks(
        validated_skills
    )


    # ============================================================
    # 9. EXPERIENCE
    # ============================================================

    experience_section = section_detected_text.get(
        "experience",
        []
    )

    experience_data = experience_extractor(
        experience_section
    )


    # ============================================================
    # 10. EDUCATION
    # ============================================================

    education_section = section_detected_text.get(
        "education",
        []
    )

    education_data = education_pipeline(
        education_section
    )


    # ============================================================
    # 11. CERTIFICATIONS
    # ============================================================

    certification_section = section_detected_text.get(
        "certifications",
        []
    )

    certification_data = certification_pipeline(
        certification_section
    )


    # ============================================================
    # 12. PROJECTS
    # ============================================================

    project_section = section_detected_text.get(
        "projects",
        []
    )

    # Handle nested project-section structure
    if (
        isinstance(project_section, list)
        and len(project_section) == 1
        and isinstance(project_section[0], list)
    ):
        project_section = project_section[0]

    project_data = extract_projects(
        project_section
    )


    # ============================================================
    # 13. BUILD ORIGINAL CANDIDATE PROFILE
    # ============================================================

    candidate_profile = build_candidate_profile(
        personal_information=personal_information,
        education=education_data,
        experience=experience_data,
        skills=stack_skills,
        projects=project_data,
        certifications=certification_data
    )


    if not isinstance(
        candidate_profile,
        dict
    ):
        raise ValueError(
            "build_candidate_profile() "
            "must return a dictionary."
        )


    # ============================================================
    # 14. SAVE ORIGINAL PROFILE
    # ============================================================

    save_resume(
        candidate_profile,
        file
    )


    # ============================================================
    # 15. CANDIDATE ID
    # ============================================================

    candidate_id = candidate_profile.get(
        "candidate_id"
    )

    if not candidate_id:
        raise ValueError(
            "Candidate profile does not contain "
            "'candidate_id'."
        )


    # ============================================================
    # 16. BIAS DETECTION
    # ============================================================

    bias_report = detect_bias_indicators(
        candidate_profile
    )


    # ============================================================
    # 17. MASK PERSONAL ATTRIBUTES
    # ============================================================

    masked_profile = mask_personal_attributes(
        candidate_profile
    )


    # ============================================================
    # 18. SAFETY VALIDATION
    # ============================================================

    if "personal_information" in masked_profile:
        raise ValueError(
            "Masking failed: personal_information "
            "is still present in masked_profile."
        )


    # ============================================================
    # 19. RETURN
    # ============================================================

    return {
        "candidate_id": candidate_id,
        "masked_profile": masked_profile,
        "bias_report": bias_report,
        "original_profile": candidate_profile
    }