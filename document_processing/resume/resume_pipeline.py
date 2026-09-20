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


def _safe_list_section(section):
    if not section:
        return []
    if isinstance(section, list):
        if len(section) == 1 and isinstance(section[0], list):
            return section[0]
        return section
    return [section]


def _safe_section_text(section):
    section_items = _safe_list_section(section)
    if not section_items:
        return ""
    if isinstance(section_items[0], list):
        items = []
        for item in section_items:
            if isinstance(item, list):
                items.extend(item)
        return "\n".join(str(i) for i in items if i)
    return "\n".join(str(i) for i in section_items if i)


def _validate_extracted_profile(candidate_profile):
    if not isinstance(candidate_profile, dict):
        return False

    personal_information = candidate_profile.get("personal_information") or {}
    if isinstance(personal_information, dict):
        location = personal_information.get("location")
        if isinstance(location, str):
            lowered = location.lower()
            if any(keyword in lowered for keyword in ["developer", "engineer", "intern", "fresher", "analyst"]):
                return False

    return True


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

    print("\n================ RAW RESUME TEXT ================\n")
    print(raw_text)

    print("\n================ RAW LINES ================\n")

    for i, line in enumerate(raw_text.splitlines()):
        print(i, repr(line))

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
    
     # ============================================================
    # 6. SECTION DETECTION
    # ============================================================

    print("\n================ AFTER CLEANING ================\n")
    for i, line in enumerate(cleaned_text.splitlines(), start=1):
        print(f"{i:03d}: {line!r}")

    print("\n================ AFTER LAYOUT FIX ================\n")
    for i, line in enumerate(handled_text.splitlines(), start=1):
        print(f"{i:03d}: {line!r}")

    print("\n================ AFTER TEXT RECONSTRUCTION ================\n")
    for i, line in enumerate(reconstructed_text.splitlines(), start=1):
        print(f"{i:03d}: {line!r}")

    print("\n================ AFTER NORMALIZATION ================\n")
    for i, line in enumerate(normalized_text.splitlines(), start=1):
        print(f"{i:03d}: {line!r}")

    print("\n================ CERTIFICATION LINES ================\n")

    for stage_name, stage_text in [
        ("RAW", raw_text),
        ("CLEANED", cleaned_text),
        ("LAYOUT", handled_text),
        ("RECONSTRUCTED", reconstructed_text),
        ("NORMALIZED", normalized_text),
    ]:
        print(f"\n--- {stage_name} ---")

        for line in stage_text.splitlines():
            if "cert" in line.lower():
                print(repr(line))


    section_detected_text = detect_sections(
        normalized_text,
        headings
    )

    # Fallback when headings are variant-heavy or split across layouts.
    if not section_detected_text or not any(section_detected_text.values()):
        fallback_sections = detect_sections(
            cleaned_text,
            headings
        )
        if fallback_sections:
            section_detected_text = fallback_sections


    # ============================================================
    # 7. PERSONAL INFORMATION
    # ============================================================

    personal_information = extract_personal_information(
        normalized_text
    )


    # ============================================================
    # 8. SKILLS
    # ============================================================

    final_skills = extract_skill(
        section_detected_text
    )



    # ============================================================
    # 9. EXPERIENCE
    # ============================================================

    experience_section = _safe_list_section(
        section_detected_text.get("experience", [])
    )

    experience_data = experience_extractor(
        experience_section
    )


    # ============================================================
    # 10. EDUCATION
    # ============================================================

    education_section = _safe_list_section(
        section_detected_text.get("education", [])
    )

    education_data = education_pipeline(
        education_section
    )


    # ============================================================
    # 11. CERTIFICATIONS
    # ============================================================
    print("\n================ SECTION OUTPUT DEBUG ================")
    print("SECTIONS:")
    print(repr(section_detected_text))

    print("\nCERTIFICATION SECTION:")
    print(repr(section_detected_text.get("certifications")))

    certification_lines = section_detected_text.get("certifications", [])

    print("\nCERTIFICATION LINES PASSED TO PIPELINE:")
    print(repr(certification_lines))

    certification_section = _safe_list_section(
        section_detected_text.get("certifications", [])
    )
    
    print("\n================ CERTIFICATION PIPELINE DEBUG ================")

    print("1. DETECTED:")
    print(repr(section_detected_text.get("certifications")))

    print("\n2. AFTER _safe_list_section:")
    print(repr(certification_section))

    certification_data = certification_pipeline(
        certification_section
    )
    
    print("\n3. CERTIFICATION PIPELINE RESULT:")
    print(repr(certification_data))

    print("==============================================================")


    # ============================================================
    # 12. PROJECTS
    # ============================================================

    project_section = _safe_list_section(
        section_detected_text.get("projects", [])
    )

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
        skills=final_skills,
        projects=project_data,
        certifications=certification_data
    )

    if not _validate_extracted_profile(candidate_profile):
        candidate_profile["personal_information"] = {
            "name": personal_information.get("name"),
            "email": personal_information.get("email"),
            "phone": personal_information.get("phone"),
            "location": personal_information.get("location"),
            "linkedin": personal_information.get("linkedin"),
            "github": personal_information.get("github"),
            "portfolio": personal_information.get("portfolio"),
        }

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