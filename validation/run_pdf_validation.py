"""
Temporary PDF Reader Validation Runner
======================================

Purpose
-------
Compare PDFPlumber and PyMuPDF extraction and then compare their
impact on the ATS parsing/scoring pipeline.

IMPORTANT
---------
This runner is completely isolated from the production ATS pipeline.

It does NOT:
    - call api/main.py
    - persist candidate profiles
    - persist candidate identity
    - persist scoring results
    - modify production data
    - run production API endpoints

Validation data is kept in memory only.

Usage
-----
Run all PDFs:

    python -m validation.run_pdf_validation

Run one PDF:

    python -m validation.run_pdf_validation --pdf two_column.pdf

Print JSON result:

    python -m validation.run_pdf_validation --json

Run one PDF and print JSON:

    python -m validation.run_pdf_validation --pdf two_column.pdf --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from embeddings.embedding_generator import EmbeddingGenerator
from embeddings.embedding_text_builder import profile_to_embedding_text
from validation.ats_reader_comparison import (
    validate_reader_pair,
    print_ats_difference_report,
)

embedding_generator = EmbeddingGenerator()


# ============================================================================
# IMPORT ATS READER COMPARISON
# ============================================================================

try:
    from validation.ats_reader_comparison import validate_reader_pair
except ImportError as exc:
    print("\nERROR: Could not import ats_reader_comparison.py")
    print(f"Details: {exc}")
    print("\nMake sure you are running from the project root:")
    print("    python -m validation.run_pdf_validation")
    sys.exit(1)


# ============================================================================
# PROJECT PATHS
# ============================================================================

CURRENT_FILE = Path(__file__).resolve()
VALIDATION_DIR = CURRENT_FILE.parent
PROJECT_ROOT = VALIDATION_DIR.parent

RESUME_DIR = (
    PROJECT_ROOT
    / "data"
    / "validation"
    / "edge_case_resumes"
)

JD_FILE = (
    PROJECT_ROOT
    / "data"
    / "extracted"
    / "jd"
    / "PythonDeveloperFresher.json"
)


# ============================================================================
# IMPORT PDF VALIDATION ENGINE
# ============================================================================

try:
    from validation.pdf_reader_validation import (
        validate_pdf,
        print_case_report,
        print_summary,
    )
except ImportError as exc:
    print("\nERROR: Could not import pdf_reader_validation.py")
    print(f"Details: {exc}")
    print("\nMake sure you are running from the project root:")
    print("    python -m validation.run_pdf_validation")
    sys.exit(1)


# ============================================================================
# ARGUMENTS
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Temporary PDFPlumber vs PyMuPDF validation runner"
    )

    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="Validate only the specified PDF filename",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete validation result as JSON",
    )

    return parser.parse_args()


# ============================================================================
# PDF DISCOVERY
# ============================================================================

def discover_pdfs(
    resume_dir: Path,
    requested_pdf: str | None = None,
) -> list[Path]:
    """
    Discover unique PDF files.

    Duplicate files are removed using their resolved absolute path.
    """

    if not resume_dir.exists():
        raise FileNotFoundError(
            f"Resume validation directory does not exist:\n{resume_dir}"
        )

    if not resume_dir.is_dir():
        raise NotADirectoryError(
            f"Resume validation path is not a directory:\n{resume_dir}"
        )

    all_pdfs = sorted(
        resume_dir.rglob("*.pdf"),
        key=lambda p: str(p).lower(),
    )

    if requested_pdf:
        requested_name = Path(requested_pdf).name.lower()

        matches = [
            pdf
            for pdf in all_pdfs
            if pdf.name.lower() == requested_name
        ]

        if not matches:
            raise FileNotFoundError(
                f"Requested PDF was not found:\n"
                f"    {requested_pdf}\n\n"
                f"Search directory:\n"
                f"    {resume_dir}"
            )

        all_pdfs = matches

    unique_pdfs: list[Path] = []
    seen: set[str] = set()

    for pdf in all_pdfs:
        try:
            resolved = pdf.resolve()
        except OSError:
            resolved = pdf.absolute()

        key = str(resolved).lower()

        if key in seen:
            continue

        seen.add(key)
        unique_pdfs.append(resolved)

    return unique_pdfs


# ============================================================================
# JD VALIDATION
# ============================================================================

def validate_jd_file(jd_file: Path) -> dict[str, Any]:
    """
    Load and validate the configured JD.

    The JD is loaded into memory only.
    It is NOT modified or persisted.
    """

    result: dict[str, Any] = {
        "exists": False,
        "valid_json": False,
        "job_title": None,
        "jd_profile": None,
        "error": None,
    }

    if not jd_file.exists():
        result["error"] = f"JD file does not exist: {jd_file}"
        return result

    result["exists"] = True

    try:
        with jd_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            jd_data = json.load(file)

        if not isinstance(jd_data, dict):
            result["error"] = "JD JSON root must be an object/dictionary."
            return result

        result["valid_json"] = True

        result["job_title"] = (
            jd_data.get("job_title")
            or jd_data.get("title")
            or jd_data.get("jobTitle")
        )

        # Keep the complete JD profile in memory for Phase 2 ATS validation.
        result["jd_profile"] = jd_data

    except Exception as exc:
        result["error"] = str(exc)

    return result


# ============================================================================
# HEADER
# ============================================================================

def print_header(
    pdf_count: int,
    jd_info: dict[str, Any],
) -> None:

    print()
    print("=" * 78)
    print("                    PDF EXTRACTOR ATS VALIDATION")
    print("=" * 78)

    print("Mode              : TEMPORARY VALIDATION")
    print("Production main.py: NOT CALLED")
    print("Profile storage   : DISABLED")
    print("Identity storage  : DISABLED")
    print("Score storage     : DISABLED")
    print("Validation output : IN MEMORY ONLY")
    print("Phase 1           : RAW PDF READER COMPARISON")
    print("Phase 2           : ATS PIPELINE COMPARISON")

    print(f"Comparison key    : RESOLVED PDF PATH")
    print(f"Resume directory  : {RESUME_DIR}")
    print(f"JD file           : {JD_FILE}")
    print(f"Unique PDFs found : {pdf_count}")

    print()

    if jd_info["exists"] and jd_info["valid_json"]:
        print("JD status         : VALID")
        print(
            f"Job title         : "
            f"{jd_info['job_title'] or 'NOT FOUND'}"
        )

    elif jd_info["exists"]:
        print("JD status         : INVALID JSON")
        print(f"JD error          : {jd_info['error']}")

    else:
        print("JD status         : NOT FOUND")
        print(f"JD error          : {jd_info['error']}")

    print("=" * 78)


# ============================================================================
# SAFE RESULT CONVERSION
# ============================================================================

def make_json_safe(value: Any) -> Any:
    """
    Convert Path and other objects into JSON-safe values.
    """

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(val)
            for key, val in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            make_json_safe(item)
            for item in value
        ]

    if isinstance(value, set):
        return sorted(
            make_json_safe(item)
            for item in value
        )

    return value


# ============================================================================
# PHASE 2 - ATS READER COMPARISON
# ============================================================================

def run_ats_validation(
    pdf_path: Path,
    pdfplumber_text: str,
    pymupdf_text: str,
    jd_profile: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Run Phase 2 ATS comparison.

    This delegates the actual PDFPlumber-vs-PyMuPDF ATS comparison
    to ats_reader_comparison.py.

    Everything remains in memory.
    """
    
    jd_embedding_text = profile_to_embedding_text(jd_profile)

    jd_embedding = embedding_generator.generate_embedding(
        jd_embedding_text
    )

    if not isinstance(jd_profile, dict):
        return {
            "classification": "ATS_NOT_RUN",
            "status": "ERROR",
            "reason": "JD profile is not available.",
        }

    try:
        ats_result = validate_reader_pair(
            pdf_path=pdf_path,
            pdfplumber_text=pdfplumber_text,
            pymupdf_text=pymupdf_text,
            jd_profile=jd_profile,
            embedding_generator=embedding_generator,
            jd_embedding=jd_embedding,
        )
        if not isinstance(ats_result, dict):
            return {
                "classification": "ATS_NOT_RUN",
                "status": "ERROR",
                "reason": (
                    "validate_reader_pair() did not return a dictionary."
                ),
                "raw_result": str(ats_result),
            }

        return make_json_safe(ats_result)

    except Exception as exc:
        return {
            "classification": "ATS_NOT_RUN",
            "status": "ERROR",
            "reason": str(exc),
        }


# ============================================================================
# PRINT ATS RESULT
# ============================================================================

def print_ats_report(
    pdf_path: Path,
    ats_result: dict[str, Any],
) -> None:
    """
    Print a compact Phase 2 ATS comparison report.
    """

    print()
    print("-" * 78)
    print("PHASE 2 - ATS PIPELINE COMPARISON")
    print("-" * 78)

    print(f"PDF                  : {pdf_path.name}")

    classification = ats_result.get(
        "classification",
        "UNKNOWN",
    )

    print(
        f"ATS classification   : "
        f"{classification}"
    )

    if "adapter_required" in ats_result:
        print(
            f"Adapter required     : "
            f"{ats_result.get('adapter_required')}"
        )

    if "status" in ats_result:
        print(
            f"ATS status           : "
            f"{ats_result.get('status')}"
        )

    if ats_result.get("reason"):
        print(
            f"Reason               : "
            f"{ats_result.get('reason')}"
        )

    # Optional score information.
    comparison = ats_result.get("comparison")

    if isinstance(comparison, dict):

        if "final_score_a" in comparison:
            print(
                f"PDFPlumber score     : "
                f"{comparison.get('final_score_a')}"
            )

        if "final_score_b" in comparison:
            print(
                f"PyMuPDF score        : "
                f"{comparison.get('final_score_b')}"
            )

        if "score_difference" in comparison:
            print(
                f"Score difference     : "
                f"{comparison.get('score_difference')}"
            )

    print("-" * 78)
    
    print_ats_difference_report(ats_result)


# ============================================================================
# RUN VALIDATION
# ============================================================================

def run_validation(
    pdfs: list[Path],
    jd_file: Path,
) -> dict[str, Any]:
    """
    Run Phase 1 and Phase 2 validation for all selected PDFs.

    Everything remains in memory.
    """

    results: list[dict[str, Any]] = []

    validation_errors = 0

    # ------------------------------------------------------------------------
    # Load JD once.
    # ------------------------------------------------------------------------

    jd_info = validate_jd_file(jd_file)

    jd_profile = jd_info.get("jd_profile")

    # ------------------------------------------------------------------------
    # Validate every PDF.
    # ------------------------------------------------------------------------

    for index, pdf_path in enumerate(pdfs, start=1):

        print()
        print("=" * 78)
        print(
            f"[{index}/{len(pdfs)}] "
            f"VALIDATING: {pdf_path.name}"
        )
        print("=" * 78)

        # ====================================================================
        # PHASE 1
        # ====================================================================

        try:

            try:
                result = validate_pdf(
                    pdf_path=pdf_path,
                    jd_file=jd_file,
                )

            except TypeError:
                # Compatibility with older validate_pdf(pdf_path)
                result = validate_pdf(pdf_path)

            result = make_json_safe(result)

            # ================================================================
            # PHASE 2
            # ================================================================

            print_case_report(result)

            print()
            print("Starting ATS pipeline comparison...")

            reader_text = result.get(
                "reader_text",
                {},
            )

            ats_result = run_ats_validation(
                pdf_path=pdf_path,
                pdfplumber_text=reader_text.get(
                    "pdfplumber",
                    "",
                ),
                pymupdf_text=reader_text.get(
                    "pymupdf",
                    "",
                ),
                jd_profile=jd_profile,
            )

            print_ats_report(
                pdf_path=pdf_path,
                ats_result=ats_result,
            )

            result["ats_comparison"] = ats_result

            results.append(result)

        except Exception as exc:

            validation_errors += 1

            error_result = {
                "pdf": str(pdf_path),
                "pdf_name": pdf_path.name,
                "status": "ERROR",
                "error": str(exc),
                "ats_comparison": {
                    "classification": "ATS_NOT_RUN",
                    "status": "ERROR",
                    "reason": (
                        "Phase 1 validation failed; "
                        "ATS comparison was not executed."
                    ),
                },
            }

            results.append(error_result)

            print()
            print("VALIDATION ERROR")
            print(f"PDF   : {pdf_path.name}")
            print(f"Error : {exc}")

    # ========================================================================
    # PHASE 1 SUMMARY
    # ========================================================================

    summary = None

    try:
        summary = print_summary(results)
    except Exception:
        summary = None

    if summary is None:
        summary = build_fallback_summary(results)

    # ========================================================================
    # PHASE 2 SUMMARY
    # ========================================================================

    ats_summary = build_ats_summary(results)

    # ========================================================================
    # FINAL REPORT
    # ========================================================================

    return {
        "mode": "TEMPORARY_VALIDATION",

        "production_main_called": False,

        "profile_storage_enabled": False,
        "identity_storage_enabled": False,
        "score_storage_enabled": False,

        "results_in_memory_only": True,

        "resume_directory": str(RESUME_DIR),
        "jd_file": str(jd_file),

        "pdf_count": len(pdfs),
        "validation_errors": validation_errors,

        "results": results,

        "summary": make_json_safe(summary),

        "ats_summary": make_json_safe(ats_summary),
    }


# ============================================================================
# PHASE 1 FALLBACK SUMMARY
# ============================================================================

def build_fallback_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a summary if pdf_reader_validation.print_summary()
    does not return one.
    """

    total = len(results)

    errors = sum(
        1
        for result in results
        if result.get("status") == "ERROR"
        or result.get("classification") == "ERROR"
    )

    ocr_required = sum(
        1
        for result in results
        if result.get("classification") == "OCR_REQUIRED"
    )

    raw_equivalent = sum(
        1
        for result in results
        if result.get("classification") == "RAW_EQUIVALENT"
    )

    layout_difference = sum(
        1
        for result in results
        if result.get("classification") == "LAYOUT_DIFFERENCE"
    )

    raw_difference = sum(
        1
        for result in results
        if result.get("classification") == "RAW_DIFFERENCE"
    )

    overlaps: list[float] = []

    for result in results:

        comparison = result.get("comparison", {})

        if not isinstance(comparison, dict):
            continue

        overlap = (
            comparison.get("word_overlap")
            or comparison.get("word_overlap_ratio")
        )

        if isinstance(overlap, (int, float)):
            overlaps.append(float(overlap))

    average_overlap = (
        sum(overlaps) / len(overlaps)
        if overlaps
        else 0.0
    )

    return {
        "total": total,
        "errors": errors,
        "ocr_required": ocr_required,
        "raw_equivalent": raw_equivalent,
        "layout_difference": layout_difference,
        "raw_difference": raw_difference,
        "average_word_overlap": round(
            average_overlap,
            4,
        ),
    }


# ============================================================================
# PHASE 2 ATS SUMMARY
# ============================================================================

def build_ats_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build ATS comparison summary from nested ats_comparison results.
    """

    summary = {
        "total": len(results),
        "ats_equivalent": 0,
        "ats_difference": 0,
        "ats_not_run": 0,
        "adapter_required": 0,
        "errors": 0,
    }

    for result in results:

        ats_result = result.get(
            "ats_comparison",
            {},
        )

        if not isinstance(ats_result, dict):
            summary["ats_not_run"] += 1
            continue

        classification = ats_result.get(
            "classification"
        )

        if classification == "ATS_EQUIVALENT":
            summary["ats_equivalent"] += 1

        elif classification == "ATS_DIFFERENCE":
            summary["ats_difference"] += 1

        elif classification == "ADAPTER_REQUIRED":
            summary["adapter_required"] += 1

        else:
            summary["ats_not_run"] += 1

        if (
            ats_result.get("status") == "ERROR"
            or classification == "ERROR"
        ):
            summary["errors"] += 1

    return summary


# ============================================================================
# JSON OUTPUT
# ============================================================================

def print_json_report(
    report: dict[str, Any],
) -> None:

    print()
    print("=" * 78)
    print("                    COMPLETE JSON VALIDATION")
    print("=" * 78)

    print(
        json.dumps(
            make_json_safe(report),
            indent=2,
            ensure_ascii=False,
        )
    )


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:

    args = parse_arguments()
    
    

    # ------------------------------------------------------------------------
    # Validate JD
    # ------------------------------------------------------------------------

    jd_info = validate_jd_file(JD_FILE)

    # ------------------------------------------------------------------------
    # Discover PDFs
    # ------------------------------------------------------------------------

    try:

        pdfs = discover_pdfs(
            resume_dir=RESUME_DIR,
            requested_pdf=args.pdf,
        )

    except Exception as exc:

        print()
        print("=" * 78)
        print("VALIDATION STARTUP ERROR")
        print("=" * 78)
        print(str(exc))
        print("=" * 78)

        return 1

    # ------------------------------------------------------------------------
    # Nothing found
    # ------------------------------------------------------------------------

    if not pdfs:

        print()
        print("=" * 78)
        print("NO PDF FILES FOUND")
        print("=" * 78)
        print(f"Directory: {RESUME_DIR}")
        print("=" * 78)

        return 1

    # ------------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------------

    print_header(
        pdf_count=len(pdfs),
        jd_info=jd_info,
    )

    # ------------------------------------------------------------------------
    # Run validation
    # ------------------------------------------------------------------------

    report = run_validation(
        pdfs=pdfs,
        jd_file=JD_FILE,
    )

    # ------------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------------

    summary = report.get(
        "summary",
        {},
    )

    ats_summary = report.get(
        "ats_summary",
        {},
    )

    print()
    print("=" * 78)
    print("                         FINAL VALIDATION")
    print("=" * 78)

    print(
        f"Total PDFs              : "
        f"{report.get('pdf_count', 0)}"
    )

    print(
        f"Validation errors       : "
        f"{report.get('validation_errors', 0)}"
    )

    print()
    print("PHASE 1 - RAW PDF READER")
    print("-" * 78)

    if isinstance(summary, dict):

        if "raw_equivalent" in summary:
            print(
                f"RAW_EQUIVALENT          : "
                f"{summary['raw_equivalent']}"
            )

        if "layout_difference" in summary:
            print(
                f"LAYOUT_DIFFERENCE      : "
                f"{summary['layout_difference']}"
            )

        if "raw_difference" in summary:
            print(
                f"RAW_DIFFERENCE         : "
                f"{summary['raw_difference']}"
            )

        if "ocr_required" in summary:
            print(
                f"OCR_REQUIRED           : "
                f"{summary['ocr_required']}"
            )

        if "average_word_overlap" in summary:
            print(
                f"Average word overlap   : "
                f"{summary['average_word_overlap']:.4f}"
            )

    print()
    print("PHASE 2 - ATS PIPELINE")
    print("-" * 78)

    if isinstance(ats_summary, dict):

        print(
            f"ATS_EQUIVALENT         : "
            f"{ats_summary.get('ats_equivalent', 0)}"
        )

        print(
            f"ATS_DIFFERENCE         : "
            f"{ats_summary.get('ats_difference', 0)}"
        )

        print(
            f"ATS_NOT_RUN            : "
            f"{ats_summary.get('ats_not_run', 0)}"
        )

        print(
            f"ADAPTER_REQUIRED       : "
            f"{ats_summary.get('adapter_required', 0)}"
        )

        print(
            f"ATS_ERRORS             : "
            f"{ats_summary.get('errors', 0)}"
        )

    print()
    print("Production main.py      : NOT CALLED")
    print("Profile persistence     : DISABLED")
    print("Identity persistence    : DISABLED")
    print("Score persistence       : DISABLED")
    print("Results                 : IN MEMORY ONLY")

    print("=" * 78)

    # ------------------------------------------------------------------------
    # Optional JSON
    # ------------------------------------------------------------------------

    if args.json:
        print_json_report(report)

    # ------------------------------------------------------------------------
    # Exit status
    # ------------------------------------------------------------------------

    validation_errors = report.get(
        "validation_errors",
        0,
    )

    if validation_errors:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
