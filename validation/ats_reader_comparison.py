"""
ATS Reader Comparison Validation
================================

Validation-only module for comparing PDFPlumber and PyMuPDF through the
REAL resume parsing + ATS scoring pipeline.

Important:
- Does NOT call production main.py
- Does NOT persist candidate profiles
- Does NOT persist identity
- Does NOT persist scores
- Uses reader-specific extracted text
- Sends both outputs through the same downstream ATS pipeline
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import inspect
import math
import re


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECTIONS_TO_COMPARE = (
    "skills",
    "experience",
    "education",
    "projects",
    "certifications",
)

SCORE_KEYS = (
    "skill_score",
    "experience_score",
    "education_score",
    "semantic_score",
    "final_score",
    "total_score",
    "overall_score",
    "ats_score",
)

FLOAT_TOLERANCE = 0.01


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def normalize_text(value: Any) -> str:
    """Normalize text for comparison."""
    if value is None:
        return ""

    if isinstance(value, str):
        value = value.lower()
        value = re.sub(r"\s+", " ", value)
        value = re.sub(r"[^\w\s.+#/-]", "", value)
        return value.strip()

    return str(value).lower().strip()


def normalize_scalar(value: Any) -> Any:
    """Normalize scalar values before comparison."""
    if value is None:
        return None

    if isinstance(value, str):
        return normalize_text(value)

    if isinstance(value, (int, float)):
        return round(float(value), 4)

    return value


def values_equal(left: Any, right: Any) -> bool:
    """Compare values after normalization."""
    return normalize_scalar(left) == normalize_scalar(right)


def safe_get(data: Any, key: str, default: Any = None) -> Any:
    """Safely read a dictionary key."""
    if not isinstance(data, dict):
        return default

    return data.get(key, default)


def is_empty(value: Any) -> bool:
    """Return True when a value is effectively empty."""
    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0

    return False


# ---------------------------------------------------------------------------
# Recursive comparison
# ---------------------------------------------------------------------------

def compare_values(
    left: Any,
    right: Any,
    path: str = "",
) -> list[dict[str, Any]]:
    """
    Recursively compare dictionaries/lists/scalars.

    Returns a list of mismatch records.
    """

    differences: list[dict[str, Any]] = []

    # Dictionaries
    if isinstance(left, dict) and isinstance(right, dict):
        keys = sorted(set(left.keys()) | set(right.keys()))

        for key in keys:
            current_path = f"{path}.{key}" if path else str(key)

            if key not in left:
                differences.append(
                    {
                        "path": current_path,
                        "type": "MISSING_IN_PDFPLUMBER",
                        "pdfplumber": None,
                        "pymupdf": right[key],
                    }
                )
                continue

            if key not in right:
                differences.append(
                    {
                        "path": current_path,
                        "type": "MISSING_IN_PYMUPDF",
                        "pdfplumber": left[key],
                        "pymupdf": None,
                    }
                )
                continue

            differences.extend(
                compare_values(
                    left[key],
                    right[key],
                    current_path,
                )
            )

        return differences

    # Lists / tuples
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        max_len = max(len(left), len(right))

        for index in range(max_len):
            current_path = f"{path}[{index}]"

            if index >= len(left):
                differences.append(
                    {
                        "path": current_path,
                        "type": "MISSING_IN_PDFPLUMBER",
                        "pdfplumber": None,
                        "pymupdf": right[index],
                    }
                )
                continue

            if index >= len(right):
                differences.append(
                    {
                        "path": current_path,
                        "type": "MISSING_IN_PYMUPDF",
                        "pdfplumber": left[index],
                        "pymupdf": None,
                    }
                )
                continue

            differences.extend(
                compare_values(
                    left[index],
                    right[index],
                    current_path,
                )
            )

        return differences

    # Numeric comparison
    if isinstance(left, (int, float)) and isinstance(
        right, (int, float)
    ):
        if math.isclose(
            float(left),
            float(right),
            abs_tol=FLOAT_TOLERANCE,
        ):
            return []

        differences.append(
            {
                "path": path,
                "type": "VALUE_DIFFERENCE",
                "pdfplumber": left,
                "pymupdf": right,
            }
        )
        return differences

    # Scalar comparison
    if not values_equal(left, right):
        differences.append(
            {
                "path": path,
                "type": "VALUE_DIFFERENCE",
                "pdfplumber": left,
                "pymupdf": right,
            }
        )

    return differences


# ---------------------------------------------------------------------------
# Section comparison
# ---------------------------------------------------------------------------

def compare_sections(
    pdfplumber_profile: dict[str, Any],
    pymupdf_profile: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare ATS-relevant profile sections.
    """

    result: dict[str, Any] = {
        "equivalent": True,
        "sections": {},
        "total_differences": 0,
    }

    for section in SECTIONS_TO_COMPARE:
        left = pdfplumber_profile.get(section)
        right = pymupdf_profile.get(section)

        differences = compare_values(
            left,
            right,
            path=section,
        )

        section_result = {
            "equivalent": len(differences) == 0,
            "pdfplumber": left,
            "pymupdf": right,
            "differences": differences,
            "difference_count": len(differences),
        }

        result["sections"][section] = section_result
        result["total_differences"] += len(differences)

        if differences:
            result["equivalent"] = False

    return result


# ---------------------------------------------------------------------------
# Skill comparison
# ---------------------------------------------------------------------------

def extract_skill_values(profile: dict[str, Any]) -> list[str]:
    """
    Extract skills from several possible profile structures.
    """

    skills = profile.get("skills", [])

    if skills is None:
        return []

    values: list[str] = []

    def collect(value: Any) -> None:
        if value is None:
            return

        if isinstance(value, str):
            text = value.strip()

            if text:
                values.append(text)

            return

        if isinstance(value, (list, tuple, set)):
            for item in value:
                collect(item)

            return

        if isinstance(value, dict):
            for key in (
                "name",
                "skill",
                "skill_name",
                "technology",
                "value",
            ):
                if key in value:
                    collect(value[key])
                    return

    collect(skills)

    return values


def compare_skills(
    pdfplumber_profile: dict[str, Any],
    pymupdf_profile: dict[str, Any],
) -> dict[str, Any]:
    """Compare extracted skills as normalized sets."""

    left_values = extract_skill_values(pdfplumber_profile)
    right_values = extract_skill_values(pymupdf_profile)

    left_normalized = {
        normalize_text(skill)
        for skill in left_values
        if normalize_text(skill)
    }

    right_normalized = {
        normalize_text(skill)
        for skill in right_values
        if normalize_text(skill)
    }

    only_pdfplumber = sorted(left_normalized - right_normalized)
    only_pymupdf = sorted(right_normalized - left_normalized)
    common = sorted(left_normalized & right_normalized)

    union_size = len(left_normalized | right_normalized)

    overlap = (
        len(common) / union_size
        if union_size
        else 1.0
    )

    return {
        "equivalent": (
            len(only_pdfplumber) == 0
            and len(only_pymupdf) == 0
        ),
        "pdfplumber_skills": sorted(left_normalized),
        "pymupdf_skills": sorted(right_normalized),
        "common_skills": common,
        "only_pdfplumber": only_pdfplumber,
        "only_pymupdf": only_pymupdf,
        "skill_overlap": round(overlap, 4),
    }


# ---------------------------------------------------------------------------
# Score extraction
# ---------------------------------------------------------------------------

def extract_scores(score_result: Any) -> dict[str, float]:
    """
    Extract known ATS score fields from an arbitrary scoring result.
    """

    if not isinstance(score_result, dict):
        return {}

    scores: dict[str, float] = {}

    # Direct fields
    for key in SCORE_KEYS:
        value = score_result.get(key)

        if isinstance(value, (int, float)):
            scores[key] = float(value)

    # Common nested structures
    nested_keys = (
        "scores",
        "score_breakdown",
        "component_scores",
        "scoring",
        "candidate_score",
        "ats_score",
    )

    for nested_key in nested_keys:
        nested = score_result.get(nested_key)

        if not isinstance(nested, dict):
            continue

        for key in SCORE_KEYS:
            value = nested.get(key)

            if isinstance(value, (int, float)):
                scores[key] = float(value)

    return scores


def compare_scores(
    pdfplumber_score: Any,
    pymupdf_score: Any,
) -> dict[str, Any]:
    """Compare ATS score outputs."""

    left_scores = extract_scores(pdfplumber_score)
    right_scores = extract_scores(pymupdf_score)

    all_keys = sorted(
        set(left_scores.keys()) |
        set(right_scores.keys())
    )

    comparison: dict[str, Any] = {
        "equivalent": True,
        "scores": {},
        "total_differences": 0,
    }

    for key in all_keys:
        left = left_scores.get(key)
        right = right_scores.get(key)

        if left is None or right is None:
            difference = None
            equivalent = False
        else:
            difference = abs(left - right)
            equivalent = difference <= FLOAT_TOLERANCE

        comparison["scores"][key] = {
            "pdfplumber": left,
            "pymupdf": right,
            "difference": (
                round(difference, 4)
                if difference is not None
                else None
            ),
            "equivalent": equivalent,
        }

        if not equivalent:
            comparison["equivalent"] = False
            comparison["total_differences"] += 1

    return comparison


# ---------------------------------------------------------------------------
# Final score extraction
# ---------------------------------------------------------------------------

def extract_final_score(score_result: Any) -> float | None:
    """Extract final ATS score."""

    scores = extract_scores(score_result)

    for key in (
        "final_score",
        "total_score",
        "overall_score",
        "ats_score",
    ):
        if key in scores:
            return scores[key]

    return None


# ---------------------------------------------------------------------------
# Classification extraction
# ---------------------------------------------------------------------------

def extract_classification(score_result: Any) -> str | None:
    """Extract shortlist/review/reject classification."""

    if not isinstance(score_result, dict):
        return None

    possible_keys = (
        "classification",
        "decision",
        "status",
        "recommendation",
        "shortlist_status",
    )

    for key in possible_keys:
        value = score_result.get(key)

        if isinstance(value, str):
            return value

    nested_keys = (
        "candidate_score",
        "ats_score",
        "scoring",
        "result",
    )

    for nested_key in nested_keys:
        nested = score_result.get(nested_key)

        if not isinstance(nested, dict):
            continue

        for key in possible_keys:
            value = nested.get(key)

            if isinstance(value, str):
                return value

    return None


# ---------------------------------------------------------------------------
# Reader -> real ATS pipeline
# ---------------------------------------------------------------------------

def run_reader_pipeline(
    pdf_path: Path,
    reader_name: str,
    extracted_text: str | None = None,
) -> dict[str, Any]:
    """
    Run the REAL resume pipeline using reader-specific extracted text.

    This is the critical adapter that allows the validation system to test:

        PDFPlumber text -> production parser
        PyMuPDF text   -> production parser
    """

    try:
        from document_processing.resume.resume_pipeline import (
            resume_pipeline,
        )
    except Exception as exc:
        return {
            "success": False,
            "reader": reader_name,
            "profile": None,
            "error": (
                "Could not import resume_pipeline: "
                f"{exc}"
            ),
            "adapter_required": True,
            "method": None,
        }

    if not extracted_text:
        return {
            "success": False,
            "reader": reader_name,
            "profile": None,
            "error": (
                f"No extracted text was supplied for "
                f"{reader_name}."
            ),
            "adapter_required": False,
            "method": "text_override",
        }

    try:
        result = resume_pipeline(
            file=str(pdf_path),
            raw_text=extracted_text,
            save_profile=False,
            debug=True,
        )

        if not isinstance(result, dict):
            return {
                "success": False,
                "reader": reader_name,
                "profile": None,
                "error": (
                    "resume_pipeline() did not return "
                    "a dictionary."
                ),
                "adapter_required": False,
                "method": "text_override",
            }

        return {
            "success": True,
            "reader": reader_name,
            "profile": result,
            "error": None,
            "adapter_required": False,
            "method": "text_override",
        }

    except TypeError as exc:
        # This specifically helps identify an outdated pipeline
        # that does not yet support raw_text.
        signature = None

        try:
            signature = str(
                inspect.signature(resume_pipeline)
            )
        except Exception:
            pass

        return {
            "success": False,
            "reader": reader_name,
            "profile": None,
            "error": str(exc),
            "adapter_required": "raw_text" in str(exc)
            or "unexpected keyword argument" in str(exc),
            "method": "text_override",
            "pipeline_signature": signature,
        }

    except Exception as exc:
        return {
            "success": False,
            "reader": reader_name,
            "profile": None,
            "error": str(exc),
            "adapter_required": False,
            "method": "text_override",
        }

def print_skill_section_debug(
    label: str,
    result: dict[str, Any],
) -> None:
    """
    Print detailed skills-section diagnostics for one reader.
    """

    print()
    print("=" * 80)
    print(f"SKILLS / PIPELINE DEBUG - {label}")
    print("=" * 80)

    if not isinstance(result, dict):
        print("❌ Invalid pipeline result.")
        return

    # run_reader_pipeline() wraps resume_pipeline() output
    pipeline_profile = result.get("profile")

    if not isinstance(pipeline_profile, dict):
        print("❌ Pipeline profile is missing.")
        print(f"Result keys: {list(result.keys())}")
        return

    trace = pipeline_profile.get("debug_trace", {})

    if not isinstance(trace, dict):
        print("❌ debug_trace is missing.")
        print(
            "Make sure resume_pipeline() returns "
            "'debug_trace' when debug=True."
        )
        return

    # ---------------------------------------------------------------
    # Pipeline stages
    # ---------------------------------------------------------------

    print()
    print("-" * 80)
    print("PIPELINE STAGES")
    print("-" * 80)

    for stage_name in (
        "raw_text",
        "cleaned_text",
        "layout_fixed_text",
        "reconstructed_text",
        "normalized_text",
    ):
        value = trace.get(stage_name)

        if value is None:
            print(f"{stage_name:<25}: NOT AVAILABLE")
        elif isinstance(value, str):
            print(
                f"{stage_name:<25}: "
                f"{len(value)} chars"
            )
        else:
            print(
                f"{stage_name:<25}: "
                f"{type(value).__name__}"
            )

    # ---------------------------------------------------------------
    # Sections
    # ---------------------------------------------------------------

    sections = trace.get("sections", {})

    print()
    print("-" * 80)
    print("DETECTED TOP-LEVEL SECTIONS")
    print("-" * 80)

    if not isinstance(sections, dict):
        print("❌ Sections are missing or invalid.")
    else:
        print(list(sections.keys()))

    # ---------------------------------------------------------------
    # Skills section
    # ---------------------------------------------------------------

    print()
    print("-" * 80)
    print("SKILLS SECTION")
    print("-" * 80)

    if isinstance(sections, dict):
        skills_section = sections.get("skills")

        if not skills_section:
            print("❌ NO SKILLS SECTION")
        else:
            for index, block in enumerate(
                skills_section,
                start=1,
            ):
                print(f"\nBlock {index}:")

                if isinstance(block, (list, tuple)):
                    for line in block:
                        print(f"  {line!r}")
                else:
                    print(f"  {block!r}")
    else:
        print("❌ Cannot inspect skills section.")

    # ---------------------------------------------------------------
    # Candidate profile
    # ---------------------------------------------------------------

    candidate_profile = {
    "skills": trace.get("skills"),
    }

    print()
    print("-" * 80)
    print("EXTRACTED SKILLS")
    print("-" * 80)

    if isinstance(candidate_profile, dict):
        print(
            repr(
                trace.get("skills")
                )
            )
        
    else:
        print("❌ Candidate profile not available.")

    # ---------------------------------------------------------------
    # Experience
    # ---------------------------------------------------------------

    print()
    print("-" * 80)
    print("EXTRACTED EXPERIENCE")
    print("-" * 80)

    print(
        repr(
            trace.get("experience_data")
        )
    )

    # ---------------------------------------------------------------
    # Education
    # ---------------------------------------------------------------

    print()
    print("-" * 80)
    print("EXTRACTED EDUCATION")
    print("-" * 80)

    print(
        repr(
            trace.get("education_data")
        )
    )

    # ---------------------------------------------------------------
    # Certifications
    # ---------------------------------------------------------------

    print()
    print("-" * 80)
    print("EXTRACTED CERTIFICATIONS")
    print("-" * 80)

    print(
        repr(
            trace.get("certifications_data")
        )
    )

    # ---------------------------------------------------------------
    # Projects
    # ---------------------------------------------------------------

    print()
    print("-" * 80)
    print("EXTRACTED PROJECTS")
    print("-" * 80)

    print(
        repr(
            trace.get("projects_data")
        )
    )

    print()
    print("=" * 80)
# ---------------------------------------------------------------------------
# ATS scoring
# ---------------------------------------------------------------------------

def run_ats_scoring(
    pipeline_result: dict[str, Any],
    jd_profile: dict[str, Any],
    embedding_generator: Any,
    jd_embedding: Any,
) -> dict[str, Any]:
    """
    Run the REAL ATS scoring engine.

    No score is persisted.
    """

    try:
        from embeddings.embedding_text_builder import (
            profile_to_embedding_text,
        )

        from scoring.ats_scoring_engine import (
            calculate_ats_score,
        )

    except Exception as exc:
        return {
            "success": False,
            "score": None,
            "error": (
                "Could not import ATS scoring components: "
                f"{exc}"
            ),
        }

    if not isinstance(pipeline_result, dict):
        return {
            "success": False,
            "score": None,
            "error": "Invalid pipeline result.",
        }

    pipeline_profile = pipeline_result.get("profile")

    if not isinstance(pipeline_profile, dict):
        return {
            "success": False,
            "score": None,
            "error": "Pipeline profile is missing.",
        }

    # The real resume pipeline returns:
    #
    # {
    #     candidate_id,
    #     masked_profile,
    #     bias_report,
    #     original_profile
    # }
    masked_profile = pipeline_profile.get("masked_profile")

    if not isinstance(masked_profile, dict):
        return {
            "success": False,
            "score": None,
            "error": (
                "masked_profile is missing from "
                "resume_pipeline() result."
            ),
        }

    # Work on a copy so validation never mutates the
    # production pipeline result.
    scoring_profile = deepcopy(masked_profile)

    # Personal information must not participate in ATS scoring.
    scoring_profile.pop("personal_information", None)

    try:
        resume_embedding_text = profile_to_embedding_text(
            scoring_profile
        )

        resume_embedding = (
            embedding_generator.generate_embedding(
                resume_embedding_text
            )
        )

        candidate_score = calculate_ats_score(
            candidate_profile=scoring_profile,
            jd_profile=jd_profile,
            resume_embedding=resume_embedding,
            jd_embedding=jd_embedding,
            embedding_generator=embedding_generator,
        )

        if not isinstance(candidate_score, dict):
            return {
                "success": False,
                "score": None,
                "error": (
                    "calculate_ats_score() did not return "
                    "a dictionary."
                ),
            }

        return {
            "success": True,
            "score": candidate_score,
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "score": None,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Reader result comparison
# ---------------------------------------------------------------------------

def compare_reader_results(
    pdfplumber_pipeline: dict[str, Any],
    pymupdf_pipeline: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare the ATS-relevant masked profiles.

    Candidate IDs, identity information, and bias reports are intentionally
    excluded from the equivalence comparison.
    """

    left_result = pdfplumber_pipeline.get("profile")
    right_result = pymupdf_pipeline.get("profile")

    if not isinstance(left_result, dict):
        return {
            "equivalent": False,
            "error": (
                "PDFPlumber pipeline did not produce "
                "a valid profile."
            ),
        }

    if not isinstance(right_result, dict):
        return {
            "equivalent": False,
            "error": (
                "PyMuPDF pipeline did not produce "
                "a valid profile."
            ),
        }

    left_profile = left_result.get("masked_profile")
    right_profile = right_result.get("masked_profile")

    if not isinstance(left_profile, dict):
        return {
            "equivalent": False,
            "error": (
                "PDFPlumber masked_profile is missing."
            ),
        }

    if not isinstance(right_profile, dict):
        return {
            "equivalent": False,
            "error": (
                "PyMuPDF masked_profile is missing."
            ),
        }

    section_comparison = compare_sections(
        left_profile,
        right_profile,
    )

    skill_comparison = compare_skills(
        left_profile,
        right_profile,
    )

    all_differences = compare_values(
        left_profile,
        right_profile,
        path="masked_profile",
    )

    return {
        "equivalent": (
            len(all_differences) == 0
        ),
        "profile_differences": all_differences,
        "difference_count": len(all_differences),
        "sections": section_comparison,
        "skills": skill_comparison,
    }


# ---------------------------------------------------------------------------
# Complete reader-pair validation
# ---------------------------------------------------------------------------

def validate_reader_pair(
    pdf_path: Path | str,
    pdfplumber_text: str,
    pymupdf_text: str,
    jd_profile: dict[str, Any],
    embedding_generator: Any | None = None,
    jd_embedding: Any | None = None,
) -> dict[str, Any]:
    """
    Complete Phase 2 validation for one PDF.

    Flow:

        PDFPlumber text
              |
              v
        real resume_pipeline
              |
              v
        masked profile
              |
              v
        real ATS scoring

        PyMuPDF text
              |
              v
        real resume_pipeline
              |
              v
        masked profile
              |
              v
        real ATS scoring
    """

    pdf_path = Path(pdf_path)

    # ------------------------------------------------------------------
    # 1. Run PDFPlumber through real parser
    # ------------------------------------------------------------------

    pdfplumber_pipeline = run_reader_pipeline(
        pdf_path=pdf_path,
        reader_name="PDFPlumber",
        extracted_text=pdfplumber_text,
    )

    # ------------------------------------------------------------------
    # 2. Run PyMuPDF through real parser
    # ------------------------------------------------------------------

    pymupdf_pipeline = run_reader_pipeline(
        pdf_path=pdf_path,
        reader_name="PyMuPDF",
        extracted_text=pymupdf_text,
    )
    
        # ------------------------------------------------------------------
    # DEBUG: inspect actual ATS pipeline output
    # ------------------------------------------------------------------

    print_skill_section_debug(
        "PDFPlumber",
        pdfplumber_pipeline,
    )

    print_skill_section_debug(
        "PyMuPDF",
        pymupdf_pipeline,
    )

    # ------------------------------------------------------------------
    # 3. Check pipeline failures
    # ------------------------------------------------------------------

    if not pdfplumber_pipeline["success"]:
        return {
            "pdf": pdf_path.name,
            "classification": "PDFPLUMBER_PIPELINE_ERROR",
            "status": "ERROR",
            "pdfplumber_pipeline": pdfplumber_pipeline,
            "pymupdf_pipeline": pymupdf_pipeline,
            "profile_comparison": None,
            "score_comparison": None,
        }

    if not pymupdf_pipeline["success"]:
        return {
            "pdf": pdf_path.name,
            "classification": "PYMUPDF_PIPELINE_ERROR",
            "status": "ERROR",
            "pdfplumber_pipeline": pdfplumber_pipeline,
            "pymupdf_pipeline": pymupdf_pipeline,
            "profile_comparison": None,
            "score_comparison": None,
        }

    # ------------------------------------------------------------------
    # 4. Compare ATS-relevant profiles
    # ------------------------------------------------------------------

    profile_comparison = compare_reader_results(
        pdfplumber_pipeline,
        pymupdf_pipeline,
    )

    # ------------------------------------------------------------------
    # 5. If embeddings are not supplied, stop at profile comparison
    # ------------------------------------------------------------------

    if (
        embedding_generator is None
        or jd_embedding is None
    ):
        return {
            "pdf": pdf_path.name,
            "classification": (
                "PROFILE_ONLY"
                if profile_comparison["equivalent"]
                else "PROFILE_DIFFERENCE"
            ),
            "status": "COMPLETED",
            "pdfplumber_pipeline": pdfplumber_pipeline,
            "pymupdf_pipeline": pymupdf_pipeline,
            "profile_comparison": profile_comparison,
            "score_comparison": None,
        }

    # ------------------------------------------------------------------
    # 6. Run ATS scoring for PDFPlumber
    # ------------------------------------------------------------------

    pdfplumber_score = run_ats_scoring(
        pipeline_result=pdfplumber_pipeline,
        jd_profile=jd_profile,
        embedding_generator=embedding_generator,
        jd_embedding=jd_embedding,
    )

    if not pdfplumber_score["success"]:
        return {
            "pdf": pdf_path.name,
            "classification": "PDFPLUMBER_SCORING_ERROR",
            "status": "ERROR",
            "pdfplumber_pipeline": pdfplumber_pipeline,
            "pymupdf_pipeline": pymupdf_pipeline,
            "profile_comparison": profile_comparison,
            "score_comparison": None,
            "pdfplumber_score": pdfplumber_score,
        }

    # ------------------------------------------------------------------
    # 7. Run ATS scoring for PyMuPDF
    # ------------------------------------------------------------------

    pymupdf_score = run_ats_scoring(
        pipeline_result=pymupdf_pipeline,
        jd_profile=jd_profile,
        embedding_generator=embedding_generator,
        jd_embedding=jd_embedding,
    )

    if not pymupdf_score["success"]:
        return {
            "pdf": pdf_path.name,
            "classification": "PYMUPDF_SCORING_ERROR",
            "status": "ERROR",
            "pdfplumber_pipeline": pdfplumber_pipeline,
            "pymupdf_pipeline": pymupdf_pipeline,
            "profile_comparison": profile_comparison,
            "score_comparison": None,
            "pdfplumber_score": pdfplumber_score,
            "pymupdf_score": pymupdf_score,
        }

    # ------------------------------------------------------------------
    # 8. Compare ATS scores
    # ------------------------------------------------------------------

    score_comparison = compare_scores(
        pdfplumber_score["score"],
        pymupdf_score["score"],
    )

    # ------------------------------------------------------------------
    # 9. Final ATS classification
    # ------------------------------------------------------------------

    profile_equivalent = profile_comparison["equivalent"]
    score_equivalent = score_comparison["equivalent"]

    if profile_equivalent and score_equivalent:
        classification = "ATS_EQUIVALENT"
    else:
        classification = "ATS_DIFFERENCE"

    pdfplumber_final = extract_final_score(
        pdfplumber_score["score"]
    )

    pymupdf_final = extract_final_score(
        pymupdf_score["score"]
    )

    final_difference = None

    if (
        pdfplumber_final is not None
        and pymupdf_final is not None
    ):
        final_difference = abs(
            pdfplumber_final - pymupdf_final
        )

    return {
        "pdf": pdf_path.name,
        "classification": classification,
        "status": "COMPLETED",

        "pdfplumber_pipeline": pdfplumber_pipeline,
        "pymupdf_pipeline": pymupdf_pipeline,

        "profile_comparison": profile_comparison,

        "pdfplumber_score": pdfplumber_score,
        "pymupdf_score": pymupdf_score,

        "score_comparison": score_comparison,

        "final_score": {
            "pdfplumber": pdfplumber_final,
            "pymupdf": pymupdf_final,
            "difference": (
                round(final_difference, 4)
                if final_difference is not None
                else None
            ),
        },
    }


# ---------------------------------------------------------------------------
# Difference summary
# ---------------------------------------------------------------------------

def build_difference_summary(
    result: dict[str, Any],
) -> list[str]:
    """
    Build human-readable explanations for ATS differences.
    """

    reasons: list[str] = []

    profile_comparison = result.get(
        "profile_comparison"
    )

    if isinstance(profile_comparison, dict):
        skill_result = profile_comparison.get("skills")

        if isinstance(skill_result, dict):
            only_pdfplumber = skill_result.get(
                "only_pdfplumber",
                [],
            )

            only_pymupdf = skill_result.get(
                "only_pymupdf",
                [],
            )

            if only_pdfplumber:
                reasons.append(
                    "Skills extracted only by PDFPlumber: "
                    + ", ".join(only_pdfplumber)
                )

            if only_pymupdf:
                reasons.append(
                    "Skills extracted only by PyMuPDF: "
                    + ", ".join(only_pymupdf)
                )

            if (
                not only_pdfplumber
                and not only_pymupdf
                and skill_result.get("skill_overlap") is not None
            ):
                if skill_result["skill_overlap"] < 1.0:
                    reasons.append(
                        "Skill overlap is "
                        f"{skill_result['skill_overlap']:.4f}"
                    )

        sections = profile_comparison.get(
            "sections",
            {},
        )

        if isinstance(sections, dict):
            for section, data in sections.items():
                if not isinstance(data, dict):
                    continue

                count = data.get(
                    "difference_count",
                    0,
                )

                if count:
                    reasons.append(
                        f"{section}: {count} profile difference(s)"
                    )

    score_comparison = result.get(
        "score_comparison"
    )

    if isinstance(score_comparison, dict):
        score_data = score_comparison.get(
            "scores",
            {},
        )

        if isinstance(score_data, dict):
            for score_name, data in score_data.items():
                if not isinstance(data, dict):
                    continue

                if not data.get("equivalent", True):
                    difference = data.get(
                        "difference"
                    )

                    if difference is None:
                        reasons.append(
                            f"{score_name}: missing from one reader"
                        )
                    else:
                        reasons.append(
                            f"{score_name}: difference = "
                            f"{difference:.4f}"
                        )

    final_score = result.get("final_score")

    if isinstance(final_score, dict):
        difference = final_score.get(
            "difference"
        )

        if (
            isinstance(difference, (int, float))
            and difference > FLOAT_TOLERANCE
        ):
            reasons.append(
                "Final ATS score difference = "
                f"{difference:.4f}"
            )

    if not reasons:
        reasons.append(
            "No specific ATS difference reason was detected."
        )

    return reasons


# ---------------------------------------------------------------------------
# Detailed console report
# ---------------------------------------------------------------------------

def print_ats_difference_report(
    result: dict[str, Any],
) -> None:
    """
    Print detailed ATS comparison for one PDF.
    """

    print()
    print("=" * 78)
    print("ATS PIPELINE DIFFERENCE DETAILS")
    print("=" * 78)

    print(
        f"PDF            : {result.get('pdf')}"
    )

    print(
        f"Classification  : "
        f"{result.get('classification')}"
    )

    print(
        f"Status          : "
        f"{result.get('status')}"
    )

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    profile_comparison = result.get(
        "profile_comparison"
    )

    if isinstance(profile_comparison, dict):

        skill_result = profile_comparison.get(
            "skills"
        )

        print()
        print("-" * 78)
        print("SKILL COMPARISON")
        print("-" * 78)

        if isinstance(skill_result, dict):
            print(
                "Skill overlap       : "
                f"{skill_result.get('skill_overlap', 0.0):.4f}"
            )

            print(
                "PDFPlumber skills   : "
                f"{skill_result.get('pdfplumber_skills', [])}"
            )

            print(
                "PyMuPDF skills      : "
                f"{skill_result.get('pymupdf_skills', [])}"
            )

            print(
                "Only PDFPlumber     : "
                f"{skill_result.get('only_pdfplumber', [])}"
            )

            print(
                "Only PyMuPDF        : "
                f"{skill_result.get('only_pymupdf', [])}"
            )

    # ------------------------------------------------------------------
    # Section comparison
    # ------------------------------------------------------------------

    if isinstance(profile_comparison, dict):

        sections = profile_comparison.get(
            "sections",
            {},
        )

        print()
        print("-" * 78)
        print("SECTION COMPARISON")
        print("-" * 78)

        for section in SECTIONS_TO_COMPARE:

            section_result = sections.get(section)

            if not isinstance(section_result, dict):
                continue

            equivalent = section_result.get(
                "equivalent",
                False,
            )

            count = section_result.get(
                "difference_count",
                0,
            )

            status = (
                "EQUIVALENT"
                if equivalent
                else "DIFFERENT"
            )

            print(
                f"{section:<20} : "
                f"{status}"
                f" ({count} difference(s))"
            )

            if not equivalent:
                differences = section_result.get(
                    "differences",
                    [],
                )

                for difference in differences[:10]:
                    print(
                        "   "
                        f"{difference.get('path')}"
                        " : "
                        f"PDFPlumber="
                        f"{difference.get('pdfplumber')!r}"
                        " | "
                        f"PyMuPDF="
                        f"{difference.get('pymupdf')!r}"
                    )

                if len(differences) > 10:
                    print(
                        "   ... "
                        f"{len(differences) - 10} more"
                    )

    # ------------------------------------------------------------------
    # Score comparison
    # ------------------------------------------------------------------

    score_comparison = result.get(
        "score_comparison"
    )

    print()
    print("-" * 78)
    print("ATS SCORE COMPARISON")
    print("-" * 78)

    if isinstance(score_comparison, dict):

        scores = score_comparison.get(
            "scores",
            {},
        )

        if scores:
            for score_name, score_data in scores.items():

                if not isinstance(score_data, dict):
                    continue

                left = score_data.get(
                    "pdfplumber"
                )

                right = score_data.get(
                    "pymupdf"
                )

                difference = score_data.get(
                    "difference"
                )

                print(
                    f"{score_name:<20} : "
                    f"PDFPlumber={left!s:<10} "
                    f"PyMuPDF={right!s:<10} "
                    f"Difference={difference}"
                )

        else:
            print("No score fields detected.")

    else:
        print("Score comparison unavailable.")

    # ------------------------------------------------------------------
    # Final score
    # ------------------------------------------------------------------

    final_score = result.get(
        "final_score"
    )

    print()
    print("-" * 78)
    print("FINAL ATS SCORE")
    print("-" * 78)

    if isinstance(final_score, dict):
        print(
            "PDFPlumber : "
            f"{final_score.get('pdfplumber')}"
        )

        print(
            "PyMuPDF    : "
            f"{final_score.get('pymupdf')}"
        )

        print(
            "Difference : "
            f"{final_score.get('difference')}"
        )
    else:
        print("Final score unavailable.")

    # ------------------------------------------------------------------
    # Difference reasons
    # ------------------------------------------------------------------

    print()
    print("-" * 78)
    print("IDENTIFIED DIFFERENCE REASONS")
    print("-" * 78)

    reasons = build_difference_summary(result)

    for index, reason in enumerate(
        reasons,
        start=1,
    ):
        print(
            f"{index}. {reason}"
        )

    print("=" * 78)


# ---------------------------------------------------------------------------
# Compact result summary
# ---------------------------------------------------------------------------

def summarize_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """Create compact machine-readable summary."""

    classification = result.get(
        "classification"
    )

    profile_comparison = result.get(
        "profile_comparison"
    )

    score_comparison = result.get(
        "score_comparison"
    )

    final_score = result.get(
        "final_score"
    )

    skill_overlap = None

    if isinstance(profile_comparison, dict):
        skills = profile_comparison.get(
            "skills"
        )

        if isinstance(skills, dict):
            skill_overlap = skills.get(
                "skill_overlap"
            )

    return {
        "pdf": result.get("pdf"),
        "classification": classification,
        "status": result.get("status"),
        "profile_equivalent": (
            profile_comparison.get("equivalent")
            if isinstance(profile_comparison, dict)
            else None
        ),
        "profile_difference_count": (
            profile_comparison.get(
                "difference_count",
                0,
            )
            if isinstance(profile_comparison, dict)
            else None
        ),
        "skill_overlap": skill_overlap,
        "score_equivalent": (
            score_comparison.get("equivalent")
            if isinstance(score_comparison, dict)
            else None
        ),
        "score_difference_count": (
            score_comparison.get(
                "total_differences",
                0,
            )
            if isinstance(score_comparison, dict)
            else None
        ),
        "pdfplumber_final_score": (
            final_score.get("pdfplumber")
            if isinstance(final_score, dict)
            else None
        ),
        "pymupdf_final_score": (
            final_score.get("pymupdf")
            if isinstance(final_score, dict)
            else None
        ),
        "final_score_difference": (
            final_score.get("difference")
            if isinstance(final_score, dict)
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Utility for checking pipeline signature
# ---------------------------------------------------------------------------

def validate_pipeline_adapter() -> dict[str, Any]:
    """
    Verify that resume_pipeline() supports raw_text.

    Useful before running the complete validation dataset.
    """

    try:
        from document_processing.resume.resume_pipeline import (
            resume_pipeline,
        )

        signature = inspect.signature(
            resume_pipeline
        )

        parameters = signature.parameters

        return {
            "valid": "raw_text" in parameters,
            "signature": str(signature),
            "raw_text_supported": (
                "raw_text" in parameters
            ),
        }

    except Exception as exc:
        return {
            "valid": False,
            "signature": None,
            "raw_text_supported": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "SECTIONS_TO_COMPARE",
    "compare_values",
    "compare_sections",
    "compare_skills",
    "compare_scores",
    "run_reader_pipeline",
    "run_ats_scoring",
    "compare_reader_results",
    "validate_reader_pair",
    "build_difference_summary",
    "print_ats_difference_report",
    "print_skill_section_debug",
    "summarize_result",
    "validate_pipeline_adapter",
   
]
