
import re
import time

from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.resume.resume_normalizer import normalize_text
from document_processing.common.handling_layout import fix_layout
from document_processing.common.json_writer import save_file

from document_processing.resume.section_detection_orchestrator import (
    detect_resume_sections,
)
from document_processing.resume.headings import headings

from document_processing.resume.text_reconstruction import (
    text_reconstructor,
)

from document_processing.resume.entity_extracter.personal_information.personal_information_extractor import (
    extract_personal_information,
)
from document_processing.resume.entity_extracter.skill.skill_extractor import (
    extract_skill,
)
from document_processing.resume.entity_extracter.experience.experinece_pipeline import (
    experience_extractor,
)
from document_processing.resume.entity_extracter.education.education_pipeline import (
    education_pipeline,
)
from document_processing.resume.entity_extracter.certifications.certification_pipeline import (
    certification_pipeline,
)
from document_processing.resume.entity_extracter.projects.project_extraction_pipeline import (
    extract_projects,
)

from document_processing.resume.candidate_profile.candidate_profile_builder import (
    build_candidate_profile,
)

from scoring.bias_mitigation.personal_attribute_masker import (
    mask_personal_attributes,
)
from scoring.bias_mitigation.bias_indicator_detector import (
    detect_bias_indicators,
)


# ================================================================
# SAFE SECTION HELPERS
# ================================================================

def _safe_list_section(section):
    """Normalize a section into a flat list where possible."""

    if not section:
        return []

    if isinstance(section, list):
        if len(section) == 1 and isinstance(section[0], list):
            return section[0]

        return section

    return [section]


# ================================================================
# PROFILE SAFETY VALIDATION
# ================================================================

def _is_suspicious_location(location):
    """
    Detect likely job titles incorrectly extracted as locations.

    This is a basic contamination check, not a complete
    geographical location validator.
    """

    if not isinstance(location, str) or not location.strip():
        return False

    suspicious_patterns = (
        r"\bdeveloper\b",
        r"\bengineer\b",
        r"\bintern\b",
        r"\bfresher\b",
        r"\banalyst\b",
        r"\bsoftware\s+development\b",
    )

    return any(
        re.search(pattern, location, re.IGNORECASE)
        for pattern in suspicious_patterns
    )


def _validate_extracted_profile(candidate_profile):
    """
    Validate the candidate profile and clear suspicious locations.

    Returns:
        bool: True when the profile has the expected dictionary type.
    """

    if not isinstance(candidate_profile, dict):
        return False

    personal_information = candidate_profile.get(
        "personal_information"
    )

    if not isinstance(personal_information, dict):
        return True

    location = personal_information.get("location")

    if _is_suspicious_location(location):
        personal_information["location"] = None

    return True


# ================================================================
# DEBUG HELPERS
# ================================================================

def _print_lines(title, text):
    """Print pipeline-stage lines only when debug=True."""

    print(f"\n================ {title} ================\n")

    for index, line in enumerate(text.splitlines(), start=1):
        print(f"{index:03d}: {line!r}")


def _print_certification_lines(stages):
    """Print certification-related lines for debugging."""

    print(
        "\n================ CERTIFICATION LINES ================\n"
    )

    for stage_name, stage_text in stages:
        print(f"\n--- {stage_name} ---")

        for line in stage_text.splitlines():
            if "cert" in line.lower():
                print(repr(line))


# ================================================================
# PERFORMANCE REPORT
# ================================================================

def _print_profile_timing(timings, total_time):
    """Print an aggregated timing report."""

    measured_total = sum(timings.values())
    overhead = max(0.0, total_time - measured_total)

    print("\n" + "=" * 88)
    print("FULL RESUME PIPELINE PERFORMANCE")
    print("=" * 88)
    print(f"{'Stage':<42} {'Time (s)':>13} {'Total (%)':>12}")
    print("-" * 88)

    for stage, duration in sorted(
        timings.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        percentage = (
            duration / total_time * 100
            if total_time > 0
            else 0.0
        )

        print(
            f"{stage:<42} "
            f"{duration:>13.6f} "
            f"{percentage:>11.2f}%"
        )

    print("-" * 88)
    print(f"{'Measured stages':<42} {measured_total:>13.6f}")
    print(f"{'Other / unmeasured work':<42} {overhead:>13.6f}")
    print(f"{'TOTAL':<42} {total_time:>13.6f}")
    print("=" * 88)


# ================================================================
# RESUME PIPELINE
# ================================================================

def resume_pipeline(
    file,
    save_profile: bool = True,
    debug: bool = False,
    profile: bool = True,
):
    """
    Process a resume and return the candidate profile and masked profile.

    Args:
        file: Resume file path.
        save_profile: Persist the candidate profile.
        debug: Print intermediate processing information.
        profile: Print stage-level performance timings.

    Returns:
        dict containing candidate_id, masked_profile,
        bias_report, and original_profile.
    """

    pipeline_start = time.perf_counter()
    timings = {}

    # 1. RAW TEXT EXTRACTION
    start = time.perf_counter()

    raw_text = extract_raw_text(file, debug=debug)

    timings["extract_raw_text"] = time.perf_counter() - start

    if not raw_text:
        raise ValueError(
            f"Could not extract text from resume: {file}"
        )

    # Avoid printing complete resume text in normal production logs.
    if debug:
        _print_lines("RAW RESUME TEXT", raw_text)

    # 2. CLEAN TEXT
    start = time.perf_counter()

    cleaned_text = clean_text(raw_text)

    timings["clean_text"] = time.perf_counter() - start

    if debug:
        _print_lines("AFTER CLEANING", cleaned_text)

    # 3. FIX LAYOUT
    start = time.perf_counter()

    handled_text = fix_layout(cleaned_text)

    timings["fix_layout"] = time.perf_counter() - start

    if debug:
        _print_lines("AFTER LAYOUT FIX", handled_text)

    # 4. TEXT RECONSTRUCTION
    start = time.perf_counter()

    reconstructed_text = text_reconstructor(handled_text)

    timings["text_reconstruction"] = time.perf_counter() - start

    if debug:
        _print_lines(
            "AFTER TEXT RECONSTRUCTION",
            reconstructed_text,
        )

    # 5. TEXT NORMALIZATION
    start = time.perf_counter()

    normalized_text = normalize_text(reconstructed_text)

    timings["text_normalization"] = time.perf_counter() - start

    if debug:
        _print_lines("AFTER NORMALIZATION", normalized_text)

    # 6. SECTION DETECTION
    start = time.perf_counter()

    section_detected_text, section_detection_meta = (
        detect_resume_sections(
            normalized_text=normalized_text,
            cleaned_text=cleaned_text,
            headings_override=headings,
        )
    )

    timings["section_detection"] = time.perf_counter() - start

    if not isinstance(section_detected_text, dict):
        section_detected_text = {}

    if debug:
        print("\n================ SECTION OUTPUT DEBUG ================")
        print("Sections:", repr(section_detected_text))
        print("Section detection meta:", section_detection_meta)

    # 7. PERSONAL INFORMATION
    start = time.perf_counter()

    personal_information = extract_personal_information(
        normalized_text
    )

    timings["personal_information_extraction"] = (
        time.perf_counter() - start
    )

    # 8. SKILLS
    start = time.perf_counter()

    final_skills = extract_skill(
        section_detected_text,
        profile=False,
    )

    timings["skill_extraction"] = time.perf_counter() - start

    # 9. EXPERIENCE
    start = time.perf_counter()

    experience_section = _safe_list_section(
        section_detected_text.get("experience", [])
    )

    experience_data = experience_extractor(
        experience_section,
        profile=True,
    )

    timings["experience_extraction"] = time.perf_counter() - start

    # 10. EDUCATION
    start = time.perf_counter()

    education_section = _safe_list_section(
        section_detected_text.get("education", [])
    )

    education_data = education_pipeline(education_section)

    timings["education_extraction"] = time.perf_counter() - start

    # 11. CERTIFICATIONS
    start = time.perf_counter()

    certification_section = _safe_list_section(
        section_detected_text.get("certifications", [])
    )

    if debug:
        print("\nCERTIFICATION SECTION:")
        print(repr(section_detected_text.get("certifications")))
        print("\nCERTIFICATION LINES PASSED TO PIPELINE:")
        print(repr(certification_section))

    certification_data = certification_pipeline(
        certification_section
    )

    timings["certification_extraction"] = (
        time.perf_counter() - start
    )

    if debug:
        print("\nCERTIFICATION PIPELINE RESULT:")
        print(repr(certification_data))

    # 12. PROJECTS
    start = time.perf_counter()

    project_section = _safe_list_section(
        section_detected_text.get("projects", [])
    )

    project_data = extract_projects(project_section)

    timings["project_extraction"] = time.perf_counter() - start

    # 13. BUILD CANDIDATE PROFILE
    start = time.perf_counter()

    candidate_profile = build_candidate_profile(
        personal_information=personal_information,
        education=education_data,
        experience=experience_data,
        skills=final_skills,
        projects=project_data,
        certifications=certification_data,
    )

    timings["candidate_profile_building"] = (
        time.perf_counter() - start
    )

    if not isinstance(candidate_profile, dict):
        raise ValueError(
            "build_candidate_profile() must return a dictionary."
        )

    metadata = candidate_profile.setdefault("metadata", {})

    if isinstance(metadata, dict):
        metadata["section_detection"] = section_detection_meta

    # 14. PROFILE SAFETY VALIDATION
    start = time.perf_counter()

    if not _validate_extracted_profile(candidate_profile):
        raise ValueError(
            "Candidate profile must be a dictionary."
        )

    timings["profile_safety_validation"] = (
        time.perf_counter() - start
    )

    # 15. OPTIONAL PROFILE PERSISTENCE
    start = time.perf_counter()

    if save_profile:
        save_file(candidate_profile, file)

    timings["profile_persistence"] = time.perf_counter() - start

    # 16. CANDIDATE ID VALIDATION
    start = time.perf_counter()

    candidate_id = candidate_profile.get("candidate_id")

    if not candidate_id:
        raise ValueError(
            "Candidate profile does not contain 'candidate_id'."
        )

    timings["candidate_id_validation"] = time.perf_counter() - start

    # 17. BIAS DETECTION
    start = time.perf_counter()

    bias_report = detect_bias_indicators(candidate_profile)

    timings["bias_detection"] = time.perf_counter() - start

    # 18. MASK PERSONAL ATTRIBUTES
    start = time.perf_counter()

    masked_profile = mask_personal_attributes(candidate_profile)

    timings["personal_attribute_masking"] = (
        time.perf_counter() - start
    )

    # 19. MASKED PROFILE SAFETY VALIDATION
    start = time.perf_counter()

    if not isinstance(masked_profile, dict):
        raise ValueError(
            "mask_personal_attributes() must return a dictionary."
        )

    if "personal_information" in masked_profile:
        raise ValueError(
            "Masking failed: personal_information "
            "is still present in masked_profile."
        )

    timings["masked_profile_validation"] = (
        time.perf_counter() - start
    )

    # 20. RETURN
    total_time = time.perf_counter() - pipeline_start

    if profile:
        _print_profile_timing(timings, total_time)

    return {
        "candidate_id": candidate_id,
        "masked_profile": masked_profile,
        "bias_report": bias_report,
        "original_profile": candidate_profile,
    }
