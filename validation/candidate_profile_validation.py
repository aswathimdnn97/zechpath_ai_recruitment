"""
candidate_profile_validation.py

Real Resume -> Candidate Profile Integration Validation
=========================================================

Validation resumes:
    data/validation/edge_case_resume/
        - bullet_heavy.pdf
        - image_resume.pdf
        - multi_page.pdf
        - table_resume.pdf
        - two_column.pdf

Purpose
-------
Validate the REAL production resume pipeline using actual resumes.

Flow:
    PDF
      |
      v
    resume_pipeline()
      |
      v
    Candidate Profile
      |
      v
    Structural / Extraction Validation
      |
      v
    Validation Report

This file does NOT duplicate extraction logic.
It only calls the production resume_pipeline() and validates
its returned candidate profile.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any


# ============================================================
# PATH CONFIGURATION
# ============================================================

# validation/candidate_profile_validation.py
# parents[1] = project root

BASE_DIR = Path(__file__).resolve().parents[1]

VALIDATION_RESUME_DIR = (
    BASE_DIR
    / "data"
    / "validation"
    / "edge_case_resumes"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "validation"
    / "candidate_profile_results"
)


EXPECTED_RESUMES = [
    "bullet_heavy.pdf",
    "image_resume.pdf",
    "multi_page.pdf",
    "table_resume.pdf",
    "two_column.pdf",
]


# ============================================================
# IMPORT PRODUCTION PIPELINE
# ============================================================

try:
    from document_processing.resume.resume_pipeline import (
        resume_pipeline,
    )
except Exception as exc:
    print(
        "\nERROR: Could not import production "
        "resume_pipeline()."
    )
    print(f"Reason: {exc}")
    print(
        "\nExpected import:"
        "\n"
        "from document_processing.resume.resume_pipeline "
        "import resume_pipeline"
    )
    raise


# ============================================================
# VALIDATION CONFIGURATION
# ============================================================

# These are the candidate profile sections expected from
# the production pipeline.

EXPECTED_SECTIONS = [
    "personal_information",
    "education",
    "experience",
    "skills",
    "projects",
    "certifications",
]


# Sections where completely empty extraction is suspicious.
#
# We do NOT require every resume to contain every section.
# Instead, the validator records empty sections separately.
OPTIONAL_SECTIONS = {
    "personal_information",
    "education",
    "experience",
    "skills",
    "projects",
    "certifications",
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================


def is_empty(value: Any) -> bool:
    """Return True when a value is effectively empty."""

    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0

    return False


def count_items(value: Any) -> int:
    """Return a useful item count for a profile section."""

    if value is None:
        return 0

    if isinstance(value, dict):
        return len(value)

    if isinstance(value, (list, tuple, set)):
        return len(value)

    if isinstance(value, str):
        return 1 if value.strip() else 0

    return 1


def normalize_pipeline_result(result: Any) -> dict[str, Any]:
    """
    Normalize the production pipeline return value.

    Current production pipeline is expected to return:

        {
            "candidate_id": ...,
            "original_profile": {...},
            "masked_profile": {...},
            "bias_report": {...}
        }

    Older/direct pipeline versions may return the profile itself.

    This helper allows the validation script to inspect both.
    """

    if not isinstance(result, dict):
        return {
            "container": {},
            "profile": {},
            "original_profile": {},
            "masked_profile": {},
            "bias_report": {},
            "candidate_id": None,
        }

    original_profile = result.get("original_profile")
    
    masked_profile = result.get("masked_profile")

    # Current production structure
    if isinstance(original_profile, dict):
        profile = original_profile
    elif isinstance(masked_profile, dict):
        profile = masked_profile
    else:
        # Direct candidate profile
        profile = result

    return {
        "container": result,
        "profile": profile,
        "original_profile": (
            original_profile
            if isinstance(original_profile, dict)
            else {}
        ),
        "masked_profile": (
            masked_profile
            if isinstance(masked_profile, dict)
            else {}
        ),
        "bias_report": (
            result.get("bias_report")
            if isinstance(result.get("bias_report"), dict)
            else {}
        ),
        "candidate_id": result.get("candidate_id"),
    }


# ============================================================
# STRUCTURE VALIDATION
# ============================================================


def validate_profile_structure(
    profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Validate the basic candidate profile structure.
    """

    result = {
        "passed": True,
        "missing_sections": [],
        "empty_sections": [],
        "section_counts": {},
    }

    if not isinstance(profile, dict):
        result["passed"] = False
        result["missing_sections"] = EXPECTED_SECTIONS.copy()
        return result

    for section in EXPECTED_SECTIONS:

        if section not in profile:
            result["missing_sections"].append(section)
            continue

        value = profile.get(section)

        result["section_counts"][section] = count_items(value)

        if is_empty(value):
            result["empty_sections"].append(section)

    # Missing sections are structural failures.
    if result["missing_sections"]:
        result["passed"] = False

    return result


# ============================================================
# PERSONAL INFORMATION VALIDATION
# ============================================================


def validate_personal_information(
    profile: dict[str, Any],
) -> dict[str, Any]:

    section = profile.get("personal_information")

    result = {
        "passed": True,
        "exists": isinstance(section, dict),
        "checks": {},
    }

    if not isinstance(section, dict):
        result["passed"] = False
        result["checks"]["section_is_dict"] = False
        return result

    result["checks"]["section_is_dict"] = True

    # We do not require every contact field because different
    # resumes can legitimately omit them.

    meaningful_fields = [
        "name",
        "email",
        "phone",
        "location",
        "linkedin",
        "github",
    ]

    found_fields = []

    for field in meaningful_fields:
        value = section.get(field)

        if not is_empty(value):
            found_fields.append(field)

    result["found_fields"] = found_fields

    # At least one personal-information value should normally
    # exist in a real resume.
    if not found_fields:
        result["passed"] = False

    return result


# ============================================================
# SKILLS VALIDATION
# ============================================================


def validate_skills(
    profile: dict[str, Any],
) -> dict[str, Any]:

    skills = profile.get("skills")

    result = {
        "passed": True,
        "count": 0,
        "duplicates": [],
        "invalid_items": [],
        "skills": [],
    }

    if skills is None:
        result["passed"] = False
        return result

    if not isinstance(skills, list):
        result["passed"] = False
        result["invalid_items"].append(
            "skills is not a list"
        )
        return result

    result["count"] = len(skills)

    seen = set()

    for index, item in enumerate(skills):

        skill_name = None

        if isinstance(item, str):
            skill_name = item.strip()

        elif isinstance(item, dict):
            skill_name = (
                item.get("skill")
                or item.get("matched_skill")
                or item.get("canonical_skill")
                or item.get("name")
            )

        if not skill_name:
            result["invalid_items"].append(
                f"skills[{index}] has no skill name"
            )
            continue

        skill_name = str(skill_name).strip()

        if not skill_name:
            result["invalid_items"].append(
                f"skills[{index}] contains empty skill"
            )
            continue

        result["skills"].append(skill_name)

        normalized = skill_name.lower()

        if normalized in seen:
            result["duplicates"].append(skill_name)

        seen.add(normalized)

    if result["invalid_items"]:
        result["passed"] = False

    # Duplicate skills indicate an extraction/normalization
    # problem and should be reported as a failure.
    if result["duplicates"]:
        result["passed"] = False

    return result


# ============================================================
# EDUCATION VALIDATION
# ============================================================


def validate_education(
    profile: dict[str, Any],
) -> dict[str, Any]:

    education = profile.get("education")

    result = {
        "passed": True,
        "count": count_items(education),
        "invalid_items": [],
    }

    if education is None:
        result["passed"] = False
        return result

    if not isinstance(education, list):
        result["passed"] = False
        result["invalid_items"].append(
            "education is not a list"
        )
        return result

    for index, item in enumerate(education):

        if not isinstance(item, dict):
            result["invalid_items"].append(
                f"education[{index}] is not a dictionary"
            )
            continue

        meaningful = any(
            not is_empty(item.get(field))
            for field in [
                "degree_type",
                "field_of_study",
                "institution",
                "university",
                "board",
                "graduation_year",
            ]
        )

        if not meaningful:
            result["invalid_items"].append(
                f"education[{index}] contains no meaningful data"
            )

    if result["invalid_items"]:
        result["passed"] = False

    return result


# ============================================================
# EXPERIENCE VALIDATION
# ============================================================


def validate_experience(
    profile: dict[str, Any],
) -> dict[str, Any]:

    experience = profile.get("experience")

    result = {
        "passed": True,
        "count": count_items(experience),
        "invalid_items": [],
    }

    if experience is None:
        result["passed"] = False
        return result

    if not isinstance(experience, list):
        result["passed"] = False
        result["invalid_items"].append(
            "experience is not a list"
        )
        return result

    for index, item in enumerate(experience):

        if not isinstance(item, dict):
            result["invalid_items"].append(
                f"experience[{index}] is not a dictionary"
            )
            continue

        meaningful = any(
            not is_empty(item.get(field))
            for field in [
                "company",
                "company_name",
                "role",
                "job_title",
                "designation",
                "duration",
                "description",
            ]
        )

        if not meaningful:
            result["invalid_items"].append(
                f"experience[{index}] contains no meaningful data"
            )

    if result["invalid_items"]:
        result["passed"] = False

    return result


# ============================================================
# PROJECT VALIDATION
# ============================================================


def validate_projects(
    profile: dict[str, Any],
) -> dict[str, Any]:

    projects = profile.get("projects")

    result = {
        "passed": True,
        "count": count_items(projects),
        "invalid_items": [],
        "duplicate_names": [],
        "projects": [],
    }

    if projects is None:
        result["passed"] = False
        return result

    if not isinstance(projects, list):
        result["passed"] = False
        result["invalid_items"].append(
            "projects is not a list"
        )
        return result

    seen_names = set()

    for index, item in enumerate(projects):

        if not isinstance(item, dict):
            result["invalid_items"].append(
                f"projects[{index}] is not a dictionary"
            )
            continue

        name = (
            item.get("project_name")
            or item.get("name")
            or item.get("title")
        )

        if not name or not str(name).strip():
            result["invalid_items"].append(
                f"projects[{index}] has no project name"
            )
            continue

        name = str(name).strip()

        result["projects"].append(name)

        normalized = name.lower()

        if normalized in seen_names:
            result["duplicate_names"].append(name)

        seen_names.add(normalized)

    if result["invalid_items"]:
        result["passed"] = False

    if result["duplicate_names"]:
        result["passed"] = False

    return result


# ============================================================
# CERTIFICATION VALIDATION
# ============================================================


def validate_certifications(
    profile: dict[str, Any],
) -> dict[str, Any]:

    certifications = profile.get("certifications")

    result = {
        "passed": True,
        "count": count_items(certifications),
        "invalid_items": [],
        "present": certifications is not None,
    }

    # --------------------------------------------------------
    # Certifications are optional
    # --------------------------------------------------------

    if certifications is None:
        result["present"] = False
        return result

    if isinstance(certifications, list) and not certifications:
        return result

    if not isinstance(certifications, list):
        result["passed"] = False
        result["invalid_items"].append(
            "certifications is not a list"
        )
        return result

    # --------------------------------------------------------
    # Validate each certification
    #
    # Production schema:
    #
    # {
    #     "certification_name": ...,
    #     "issuing_organization": ...,
    #     "issue_date": ...,
    #     "expiration_date": ...,
    #     "credential_id": ...
    # }
    # --------------------------------------------------------

    certification_fields = [
        "certification_name",
        "issuing_organization",
        "issue_date",
        "expiration_date",
        "credential_id",
    ]

    for index, item in enumerate(certifications):

        # ----------------------------------------------------
        # String certification
        # ----------------------------------------------------

        if isinstance(item, str):

            if not item.strip():
                result["invalid_items"].append(
                    f"certifications[{index}] is empty"
                )

            continue

        # ----------------------------------------------------
        # Dictionary certification
        # ----------------------------------------------------

        if isinstance(item, dict):

            meaningful = any(
                not is_empty(item.get(field))
                for field in certification_fields
            )

            if not meaningful:
                result["invalid_items"].append(
                    f"certifications[{index}] "
                    f"has no meaningful data"
                )

            continue

        # ----------------------------------------------------
        # Invalid type
        # ----------------------------------------------------

        result["invalid_items"].append(
            f"certifications[{index}] "
            f"has invalid type"
        )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    if result["invalid_items"]:
        result["passed"] = False

    return result

# ============================================================
# PROJECT METADATA VALIDATION
# ============================================================


def validate_project_metadata(
    profile: dict[str, Any],
) -> dict[str, Any]:

    projects = profile.get("projects")

    result = {
        "passed": True,
        "issues": [],
    }

    if not isinstance(projects, list):
        return result

    metadata_words = {
        "technologies",
        "technologies used",
        "technology",
        "technology stack",
        "tech stack",
        "tools",
        "tools used",
        "using",
        "built with",
    }

    for index, project in enumerate(projects):

        if not isinstance(project, dict):
            continue

        name = (
            project.get("project_name")
            or project.get("name")
            or ""
        )

        normalized_name = (
            str(name).strip().lower()
        )

        if normalized_name in metadata_words:
            result["issues"].append(
                f"projects[{index}] project_name "
                f"is technology metadata: {name}"
            )

    if result["issues"]:
        result["passed"] = False

    return result


# ============================================================
# CROSS-SECTION VALIDATION
# ============================================================


def validate_cross_section_integrity(
    profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Detect obvious structural leakage between sections.

    This intentionally performs only conservative checks.
    It should not reject legitimate resume content.
    """

    result = {
        "passed": True,
        "issues": [],
    }

    projects = profile.get("projects", [])

    if isinstance(projects, list):

        for index, project in enumerate(projects):

            if not isinstance(project, dict):
                continue

            name = str(
                project.get("project_name")
                or project.get("name")
                or ""
            ).strip()

            # A project name should not normally be a date.
            if name and (
                name.replace("-", "").replace("/", "").isdigit()
            ):
                result["issues"].append(
                    f"projects[{index}] project name "
                    f"looks like a date: {name}"
                )

    # Duplicate skills are handled separately.
    # This check focuses on gross profile-level problems.

    if result["issues"]:
        result["passed"] = False

    return result


# ============================================================
# SINGLE RESUME VALIDATION
# ============================================================


def validate_resume(
    resume_file: Path,
) -> dict[str, Any]:

    print("\n" + "=" * 78)
    print(
        f"PROCESSING: {resume_file.name}"
    )
    print("=" * 78)

    result: dict[str, Any] = {
        "resume": resume_file.name,
        "path": str(resume_file),
        "status": "FAIL",
        "pipeline_success": False,
        "candidate_id": None,
        "validation": {},
        "profile_summary": {},
        "error": None,
    }

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not resume_file.exists():

        result["error"] = "Resume file does not exist."

        print("FAIL - file not found")

        return result

    # --------------------------------------------------------
    # Run REAL production pipeline
    # --------------------------------------------------------

    try:

        pipeline_output = resume_pipeline(
            str(resume_file)
        )

        result["pipeline_success"] = True

    except Exception as exc:

        result["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

        print(
            f"FAIL - resume_pipeline() error: {exc}"
        )

        return result

    # --------------------------------------------------------
    # Normalize output
    # --------------------------------------------------------

    normalized = normalize_pipeline_result(
        pipeline_output
    )

    profile = normalized["profile"]
    
    print("\n================ EDUCATION DEBUG ================")
    print("EDUCATION OUTPUT:")

    for index, education in enumerate(
        profile.get("education", [])
    ):
        print(f"\nEducation [{index}]:")
        print(education)

    print("==================================================")

    result["candidate_id"] = normalized[
        "candidate_id"
    ]

    # --------------------------------------------------------
    # Profile structure
    # --------------------------------------------------------

    structure = validate_profile_structure(
        profile
    )

    result["validation"]["structure"] = structure

    # --------------------------------------------------------
    # Entity validations
    # --------------------------------------------------------

    result["validation"][
        "personal_information"
    ] = validate_personal_information(
        profile
    )

    result["validation"][
        "education"
    ] = validate_education(
        profile
    )

    result["validation"][
        "skills"
    ] = validate_skills(
        profile
    )

    result["validation"][
        "experience"
    ] = validate_experience(
        profile
    )

    result["validation"][
        "projects"
    ] = validate_projects(
        profile
    )

    result["validation"][
        "certifications"
    ] = validate_certifications(
        profile
    )

    result["validation"][
        "project_metadata"
    ] = validate_project_metadata(
        profile
    )

    result["validation"][
        "cross_section_integrity"
    ] = validate_cross_section_integrity(
        profile
    )

    # --------------------------------------------------------
    # Profile summary
    # --------------------------------------------------------

    result["profile_summary"] = {
        section: count_items(
            profile.get(section)
        )
        for section in EXPECTED_SECTIONS
    }

    # --------------------------------------------------------
    # Overall status
    # --------------------------------------------------------

    failed_checks = []

    for check_name, check_result in (
        result["validation"].items()
    ):

        if isinstance(check_result, dict):

            if check_result.get("passed") is False:
                failed_checks.append(check_name)

    result["failed_checks"] = failed_checks

    if (
        result["pipeline_success"]
        and not failed_checks
    ):
        result["status"] = "PASS"

    else:
        result["status"] = "FAIL"

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print(
        f"\nPipeline       : "
        f"{'PASS' if result['pipeline_success'] else 'FAIL'}"
    )

    print(
        f"Candidate ID   : "
        f"{result['candidate_id'] or 'N/A'}"
    )

    print("\nProfile counts:")

    for section, count in result[
        "profile_summary"
    ].items():

        print(
            f"  {section:<25} : {count}"
        )

    print("\nValidation:")

    for check_name, check_result in (
        result["validation"].items()
    ):

        status = (
            "PASS"
            if check_result.get("passed")
            else "FAIL"
        )

        print(
            f"  {check_name:<25} : {status}"
        )

    print(
        f"\nSTATUS         : {result['status']}"
    )

    if failed_checks:

        print("\nFailed checks:")

        for check in failed_checks:
            print(f"  - {check}")

    return result


# ============================================================
# SAVE RESULT
# ============================================================


def save_result(
    result: dict[str, Any],
) -> Path:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_DIR
        / f"{Path(result['resume']).stem}.json"
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_file


# ============================================================
# FINAL REPORT
# ============================================================


def print_final_report(
    results: list[dict[str, Any]],
) -> None:

    total = len(results)

    passed = sum(
        1
        for result in results
        if result.get("status") == "PASS"
    )

    failed = total - passed

    pass_rate = (
        (passed / total) * 100
        if total
        else 0.0
    )

    print("\n\n")

    print("=" * 78)
    print(
        "CANDIDATE PROFILE INTEGRATION VALIDATION"
    )
    print("=" * 78)

    print()

    print(
        f"{'Resume':<25}"
        f"{'Pipeline':<12}"
        f"{'Profile':<12}"
        f"{'Status':<10}"
    )

    print("-" * 78)

    for result in results:

        pipeline_status = (
            "PASS"
            if result.get("pipeline_success") is True
            else "FAIL"
        )

        failed_checks = result.get(
            "failed_checks",
            [],
        )

        profile_status = (
            "VALID"
            if not failed_checks
            else "INVALID"
        )

        print(
            f"{result.get('resume', 'UNKNOWN'):<25}"
            f"{pipeline_status:<12}"
            f"{profile_status:<12}"
            f"{result.get('status', 'FAIL'):<10}"
        )

    print("-" * 78)

    print(
        f"\nTOTAL RESUMES : {total}"
    )

    print(
        f"PASSED        : {passed}"
    )

    print(
        f"FAILED        : {failed}"
    )

    print(
        f"PASS RATE     : {pass_rate:.2f}%"
    )

    print("-" * 78)

    if failed == 0:
        print(
            "STATUS        : PASS"
        )
    else:
        print(
            "STATUS        : FAIL"
        )

    print("=" * 78)

    # --------------------------------------------------------
    # Failure details
    # --------------------------------------------------------

    failed_results = [
        result
        for result in results
        if result.get("status") == "FAIL"
    ]

    if failed_results:

        print("\n")
        print("=" * 78)
        print("FAILED RESUME DETAILS")
        print("=" * 78)

        for result in failed_results:

            print(
                f"\n{result.get('resume', 'UNKNOWN')}"
            )

            error = result.get("error")

            if error:
                print(
                    f"  Error: {error}"
                )

            failed_checks = result.get(
                "failed_checks",
                [],
            )

            if failed_checks:

                for check in failed_checks:
                    print(
                        f"  FAILED: {check}"
                    )

            else:

                print(
                    "  FAILED: pipeline or "
                    "unexpected validation error"
                )

# ============================================================
# MAIN
# ============================================================


def main() -> int:

    print("=" * 78)
    print(
        "REAL RESUME -> CANDIDATE PROFILE VALIDATION"
    )
    print("=" * 78)

    print(
        f"\nValidation directory:"
        f"\n{VALIDATION_RESUME_DIR}"
    )

    # --------------------------------------------------------
    # Validate directory
    # --------------------------------------------------------

    if not VALIDATION_RESUME_DIR.exists():

        print(
            "\nERROR: Validation resume directory "
            "does not exist."
        )

        print(
            f"\nExpected:"
            f"\n{VALIDATION_RESUME_DIR}"
        )

        return 1

    # --------------------------------------------------------
    # Locate expected resumes
    # --------------------------------------------------------

    resume_files = []

    missing_files = []

    for filename in EXPECTED_RESUMES:

        file_path = (
            VALIDATION_RESUME_DIR
            / filename
        )

        if file_path.exists():
            resume_files.append(file_path)
        else:
            missing_files.append(filename)

    # --------------------------------------------------------
    # Missing files
    # --------------------------------------------------------

    if missing_files:

        print("\nWARNING: Missing validation resumes:")

        for filename in missing_files:
            print(f"  - {filename}")

    # --------------------------------------------------------
    # No files
    # --------------------------------------------------------

    if not resume_files:

        print(
            "\nERROR: No validation resumes found."
        )

        return 1

    print(
        f"\nFound {len(resume_files)} "
        f"validation resume(s)."
    )

    # --------------------------------------------------------
    # Run validation
    # --------------------------------------------------------

    results = []

    for resume_file in resume_files:

        try:

            result = validate_resume(
                resume_file
            )

            results.append(result)

            output_file = save_result(
                result
            )

            print(
                f"\nDetailed result saved:"
                f"\n{output_file}"
            )

        except Exception as exc:

            print(
                "\nUNEXPECTED VALIDATION ERROR:"
            )

            print(
                f"{type(exc).__name__}: {exc}"
            )

            traceback.print_exc()

            results.append(
                {
                    "resume": resume_file.name,
                    "path": str(resume_file),
                    "status": "FAIL",
                    "pipeline_success": False,
                    "candidate_id": None,
                    "validation": {},
                    "profile_summary": {},
                    "failed_checks": [
                        "unexpected_validation_error"
                    ],
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                }
            )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print_final_report(
        results
    )

    # --------------------------------------------------------
    # Save combined report
    # --------------------------------------------------------

    combined_file = (
        OUTPUT_DIR
        / "candidate_profile_validation_report.json"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with combined_file.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            {
                "validation_directory": str(
                    VALIDATION_RESUME_DIR
                ),
                "expected_resumes": (
                    EXPECTED_RESUMES
                ),
                "total": len(results),
                "passed": sum(
                    r["status"] == "PASS"
                    for r in results
                ),
                "failed": sum(
                    r["status"] == "FAIL"
                    for r in results
                ),
                "results": results,
            },
            file,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"\nCombined report:"
        f"\n{combined_file}"
    )

    # --------------------------------------------------------
    # Exit code
    # --------------------------------------------------------

    all_passed = all(
        result["status"] == "PASS"
        for result in results
    )

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
