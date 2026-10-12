import re
import sys
import time
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORT REAL ATS PIPELINE
# ============================================================

from document_processing.resume.section_detector import detect_sections
from document_processing.resume.headings import heading_aliases

from parsers.pdf_reader import read_pdf

from document_processing.common.cleaner import clean_text
from document_processing.common.handling_layout import fix_layout
from document_processing.resume.text_reconstruction import reconstruct_text
from document_processing.resume.resume_normalizer import normalize_text


# ============================================================
# TEST DATA
# ============================================================

TEST_DIR = (
    PROJECT_ROOT
    / "data"
    / "validation"
    / "edge_case_resumes"
)


# ============================================================
# OCR REQUIRED FILES
# ============================================================

OCR_REQUIRED_FILES = {
    "image_resume.pdf",
}


# ============================================================
# EXPECTED CONTENT
# ============================================================

EXPECTED_CONTENT = {

    "bullet_heavy.pdf": {

        "education": [
            "B.Tech",
            "Higher Secondary",
        ],

        "certifications": [
            "Python Programming Fundamentals",
            "REST API Development with FastAPI",
            "SQL and PostgreSQL Essentials",
        ],
    },


    "multi_page.pdf": {

        "skills": [
            "Python",
            "SQL",
            "JavaScript",
            "FastAPI",
            "Django",
            "PostgreSQL",
        ],

        "education": [
            "B.Tech",
            "Higher Secondary",
        ],

        "certifications": [
            "Python Programming Fundamentals",
            "REST API Development with FastAPI",
            "SQL and PostgreSQL Essentials",
        ],
    },


    "table_resume.pdf": {

        "education": [
            "B.Tech",
            "Higher Secondary",
        ],

        "certifications": [
            "Python Programming Fundamentals",
            "REST API Development with FastAPI",
            "SQL and PostgreSQL Essentials",
        ],

        "skills": [
            "Python",
            "FastAPI",
            "Django",
            "PostgreSQL",
            "MySQL",
            "SQLite",
            "SQLAlchemy",
        ],
    },


    "two_column.pdf": {

        "education": [
            "B.Tech",
            "Higher Secondary",
        ],

        "certifications": [
            "Python Programming Fundamentals",
            "REST API Development with FastAPI",
            "SQL and PostgreSQL Essentials",
        ],

        "experience": [
            "Python Backend Developer Intern",
            "Software Engineering Trainee",
        ],

        "projects": [
            "Recruitment ATS API",
            "Inventory Management REST API",
            "Student Registration Portal",
        ],
    },
}


# ============================================================
# KNOWN SUSPICIOUS CONTENT
# ============================================================

# These are not automatically treated as failures.
#
# They are specifically used to detect the issue already
# observed in table_resume.pdf.
#
# The purpose is to determine whether the contamination
# actually exists after the real pipeline runs.

SUSPICIOUS_CONTENT = {

    "table_resume.pdf": {

        "certifications": [
            "Backend Python",
            "Database PostgreSQL",
        ],
    },
}


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_for_comparison(value):
    """
    Normalize text for content comparison.
    """

    if value is None:
        return ""

    value = str(value)

    value = value.replace("\u00a0", " ")

    value = value.lower()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


# ============================================================
# FLATTEN SECTION CONTENT
# ============================================================

def flatten_value(value):
    """
    Recursively flatten nested section structures.
    """

    if value is None:
        return []

    if isinstance(value, str):
        return [value]

    if isinstance(value, (list, tuple)):
        result = []

        for item in value:
            result.extend(
                flatten_value(item)
            )

        return result

    return [str(value)]


def flatten_sections(sections):
    """
    Convert section detector output into:

        {
            "education": [
                "B.Tech ...",
                "Higher Secondary ..."
            ]
        }
    """

    flattened = {}

    for section_name, value in sections.items():

        flattened[section_name] = [
            line.strip()
            for line in flatten_value(value)
            if isinstance(line, str)
            and line.strip()
        ]

    return flattened


# ============================================================
# SECTION TEXT
# ============================================================

def get_section_text(
    sections,
    section_name,
):
    """
    Return complete normalized text for a section.
    """

    lines = sections.get(
        section_name,
        [],
    )

    return normalize_for_comparison(
        " ".join(lines)
    )


# ============================================================
# WORD COUNT
# ============================================================

def count_words(text):

    return len(
        re.findall(
            r"\b[\w.+#/-]+\b",
            text or "",
        )
    )


# ============================================================
# REAL ATS PIPELINE
# ============================================================

def extract_normalized_text(pdf_path):
    """
    Run exactly the same pipeline used by Phase 6.

    PDF
      -> read_pdf()
      -> clean_text()
      -> fix_layout()
      -> reconstruct_text()
      -> normalize_text()
    """

    raw_text = read_pdf(
        str(pdf_path)
    )

    if not raw_text or not raw_text.strip():

        return (
            "",
            "OCR_REQUIRED",
        )

    cleaned = clean_text(
        raw_text
    )

    layout_fixed = fix_layout(
        cleaned
    )

    reconstructed = reconstruct_text(
        layout_fixed
    )

    normalized = normalize_text(
        reconstructed
    )

    if not normalized or not normalized.strip():

        return (
            "",
            "NO_TEXT_AFTER_NORMALIZATION",
        )

    return (
        normalized,
        "TEXT_AVAILABLE",
    )


# ============================================================
# REQUIRED CONTENT VALIDATION
# ============================================================

def validate_expected_content(
    pdf_name,
    sections,
):

    expected = EXPECTED_CONTENT.get(
        pdf_name,
        {},
    )

    results = []

    for section_name, expected_items in expected.items():

        actual_text = get_section_text(
            sections,
            section_name,
        )

        for expected_item in expected_items:

            normalized_expected = (
                normalize_for_comparison(
                    expected_item
                )
            )

            found = (
                normalized_expected
                in actual_text
            )

            results.append({
                "section": section_name,
                "expected": expected_item,
                "found": found,
            })

    return results


# ============================================================
# SUSPICIOUS CONTENT VALIDATION
# ============================================================

def validate_suspicious_content(
    pdf_name,
    sections,
):

    suspicious = SUSPICIOUS_CONTENT.get(
        pdf_name,
        {},
    )

    results = []

    for section_name, suspicious_items in suspicious.items():

        actual_text = get_section_text(
            sections,
            section_name,
        )

        for suspicious_item in suspicious_items:

            normalized_item = (
                normalize_for_comparison(
                    suspicious_item
                )
            )

            found = (
                normalized_item
                in actual_text
            )

            results.append({
                "section": section_name,
                "content": suspicious_item,
                "found": found,
            })

    return results


# ============================================================
# SECTION CONTENT PREVIEW
# ============================================================

def print_section_content(sections):

    print()
    print("SECTION CONTENT")
    print("-" * 70)

    for section_name, lines in sections.items():

        print()
        print(
            f"[{section_name}]"
        )

        if not lines:

            print(
                "  <EMPTY>"
            )

            continue

        for line in lines:

            print(
                f"  {line}"
            )


# ============================================================
# CONTENT ORIGIN VALIDATION
# ============================================================

def validate_content_origin(
    normalized_text,
    sections,
):
    """
    Verify that section content actually exists in the
    normalized text produced by the pipeline.

    This detects fabricated or mutated section content.
    """

    errors = []

    normalized_source = (
        normalize_for_comparison(
            normalized_text
        )
    )

    for section_name, lines in sections.items():

        for line in lines:

            normalized_line = (
                normalize_for_comparison(
                    line
                )
            )

            if not normalized_line:
                continue

            # Very short tokens are not reliable
            # substring checks.
            if len(normalized_line) <= 5:
                continue

            if normalized_line not in normalized_source:

                errors.append(
                    f"Content not found in normalized "
                    f"text: {section_name} -> {line}"
                )

    return errors


# ============================================================
# EMPTY SECTION VALIDATION
# ============================================================

def validate_empty_sections(sections):

    errors = []

    for section_name, lines in sections.items():

        if not lines:

            errors.append(
                f"Empty section: {section_name}"
            )

    return errors


# ============================================================
# SECTION CONTENT QUALITY
# ============================================================

def validate_section_content_quality(
    sections,
):

    errors = []

    for section_name, lines in sections.items():

        usable_lines = [
            line
            for line in lines
            if isinstance(line, str)
            and line.strip()
        ]

        if not usable_lines:

            errors.append(
                f"Section has no usable content: "
                f"{section_name}"
            )

    return errors


# ============================================================
# CROSS SECTION DUPLICATION
# ============================================================

def validate_cross_section_duplication(
    sections,
):

    warnings = []

    section_names = list(
        sections.keys()
    )

    section_words = {}

    for section_name in section_names:

        text = get_section_text(
            sections,
            section_name,
        )

        section_words[section_name] = set(
            text.split()
        )

    for index, first_section in enumerate(
        section_names
    ):

        first_words = section_words[
            first_section
        ]

        if not first_words:
            continue

        for second_section in section_names[
            index + 1:
        ]:

            second_words = section_words[
                second_section
            ]

            if not second_words:
                continue

            overlap = (
                len(
                    first_words
                    & second_words
                )
                /
                max(
                    1,
                    min(
                        len(first_words),
                        len(second_words),
                    ),
                )
            )

            if overlap >= 0.90:

                warnings.append(
                    "High content overlap between "
                    f"{first_section} and "
                    f"{second_section}"
                )

    return warnings


# ============================================================
# VALIDATE ONE PDF
# ============================================================

def validate_pdf(pdf_path):

    start_time = time.perf_counter()

    print()
    print("=" * 78)
    print(
        "PHASE 7 - SECTION CONTENT VALIDATION"
    )
    print("=" * 78)

    print(
        f"PDF : {pdf_path.name}"
    )

    # --------------------------------------------------------
    # OCR CHECK
    # --------------------------------------------------------

    if pdf_path.name in OCR_REQUIRED_FILES:

        print()
        print(
            "STATUS : OCR_REQUIRED"
        )

        print(
            "Reason : Image/scanned PDF requires OCR."
        )

        return {
            "status": "OCR_REQUIRED",
            "time": 0.0,
            "expected_pass": 0,
            "expected_fail": 0,
            "warnings": 0,
            "errors": [],
        }

    # --------------------------------------------------------
    # REAL PIPELINE
    # --------------------------------------------------------

    try:

        normalized_text, text_status = (
            extract_normalized_text(
                pdf_path
            )
        )

    except Exception as exc:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print()
        print(
            "STATUS : FAIL"
        )

        print(
            f"ERROR  : "
            f"{type(exc).__name__}: {exc}"
        )

        return {
            "status": "FAIL",
            "time": elapsed,
            "expected_pass": 0,
            "expected_fail": 1,
            "warnings": 0,
            "errors": [
                str(exc)
            ],
        }

    elapsed = (
        time.perf_counter()
        - start_time
    )

    # --------------------------------------------------------
    # TEXT STATUS
    # --------------------------------------------------------

    if text_status != "TEXT_AVAILABLE":

        print()
        print(
            f"STATUS : {text_status}"
        )

        return {
            "status": "FAIL",
            "time": elapsed,
            "expected_pass": 0,
            "expected_fail": 1,
            "warnings": 0,
            "errors": [
                text_status
            ],
        }

    # --------------------------------------------------------
    # SECTION DETECTION
    # --------------------------------------------------------

    sections = detect_sections(
        normalized_text,
        headings_override=heading_aliases,
    )

    flattened = flatten_sections(
        sections
    )

    # --------------------------------------------------------
    # PRINT NORMALIZED TEXT
    # --------------------------------------------------------

    print()
    print("NORMALIZED TEXT")
    print("-" * 78)

    print(
        normalized_text
    )

    print("-" * 78)

    # --------------------------------------------------------
    # PRINT SECTION CONTENT
    # --------------------------------------------------------

    print_section_content(
        flattened
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    errors = []
    warnings = []

    # --------------------------------------------------------
    # Empty sections
    # --------------------------------------------------------

    errors.extend(
        validate_empty_sections(
            flattened
        )
    )

    # --------------------------------------------------------
    # Section content quality
    # --------------------------------------------------------

    errors.extend(
        validate_section_content_quality(
            flattened
        )
    )

    # --------------------------------------------------------
    # Content origin
    # --------------------------------------------------------

    errors.extend(
        validate_content_origin(
            normalized_text,
            flattened,
        )
    )

    # --------------------------------------------------------
    # Expected content
    # --------------------------------------------------------

    expected_results = (
        validate_expected_content(
            pdf_path.name,
            flattened,
        )
    )

    expected_pass = 0
    expected_fail = 0

    print()
    print("EXPECTED CONTENT CHECK")
    print("-" * 78)

    if not expected_results:

        print(
            "No explicit expected-content rules."
        )

    for result in expected_results:

        if result["found"]:

            expected_pass += 1

            print(
                "[PASS] "
                f"{result['section']} -> "
                f"{result['expected']}"
            )

        else:

            expected_fail += 1

            errors.append(
                "Expected content missing: "
                f"{result['section']} -> "
                f"{result['expected']}"
            )

            print(
                "[FAIL] "
                f"{result['section']} -> "
                f"{result['expected']}"
            )

    # --------------------------------------------------------
    # Suspicious content
    # --------------------------------------------------------

    suspicious_results = (
        validate_suspicious_content(
            pdf_path.name,
            flattened,
        )
    )

    print()
    print("SUSPICIOUS CONTENT CHECK")
    print("-" * 78)

    suspicious_found = 0

    if not suspicious_results:

        print(
            "No suspicious-content rules."
        )

    for result in suspicious_results:

        if result["found"]:

            suspicious_found += 1

            warnings.append(
                "Suspicious content found in "
                f"{result['section']}: "
                f"{result['content']}"
            )

            print(
                "[WARNING] "
                f"{result['section']} contains -> "
                f"{result['content']}"
            )

        else:

            print(
                "[OK] "
                f"{result['section']} does not contain -> "
                f"{result['content']}"
            )

    # --------------------------------------------------------
    # Cross section duplication
    # --------------------------------------------------------

    duplication_warnings = (
        validate_cross_section_duplication(
            flattened
        )
    )

    warnings.extend(
        duplication_warnings
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print()
    print("SECTION CONTENT SUMMARY")
    print("-" * 78)

    print(
        f"Detected sections : "
        f"{len(flattened)}"
    )

    print(
        f"Expected checks   : "
        f"{expected_pass + expected_fail}"
    )

    print(
        f"Expected passed   : "
        f"{expected_pass}"
    )

    print(
        f"Expected failed   : "
        f"{expected_fail}"
    )

    print(
        f"Suspicious found  : "
        f"{suspicious_found}"
    )

    print(
        f"Errors            : "
        f"{len(errors)}"
    )

    print(
        f"Warnings          : "
        f"{len(warnings)}"
    )

    # --------------------------------------------------------
    # FINAL STATUS
    # --------------------------------------------------------

    if errors:

        status = "FAIL"

    elif warnings:

        status = "PASS_WITH_WARNINGS"

    else:

        status = "PASS"

    print()
    print(
        f"SECTION CONTENT STATUS : "
        f"{status}"
    )

    print(
        f"Time                   : "
        f"{elapsed:.3f} sec"
    )

    # --------------------------------------------------------
    # ERROR DETAILS
    # --------------------------------------------------------

    if errors:

        print()
        print("ERROR DETAILS")
        print("-" * 78)

        for error in errors:

            print(
                f"[ERROR] {error}"
            )

    # --------------------------------------------------------
    # WARNING DETAILS
    # --------------------------------------------------------

    if warnings:

        print()
        print("WARNING DETAILS")
        print("-" * 78)

        for warning in warnings:

            print(
                f"[WARNING] {warning}"
            )

    return {
        "status": status,
        "time": elapsed,
        "expected_pass": expected_pass,
        "expected_fail": expected_fail,
        "warnings": len(warnings),
        "errors": errors,
        "sections": list(
            flattened.keys()
        ),
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 78)
    print(
        "PHASE 7 - SECTION CONTENT VALIDATION"
    )
    print("=" * 78)

    print()
    print(
        "Validation stages:"
    )

    print(
        "PDF -> PDF Reader -> clean_text() -> "
        "fix_layout() -> reconstruct_text() -> "
        "normalize_text() -> detect_sections() -> "
        "CONTENT VALIDATION"
    )

    print()
    print(
        "Test folder:"
    )

    print(
        TEST_DIR
    )

    # --------------------------------------------------------
    # TEST DIRECTORY
    # --------------------------------------------------------

    if not TEST_DIR.exists():

        print()
        print(
            "ERROR: Test folder not found:"
        )

        print(
            TEST_DIR
        )

        return 1

    pdf_files = sorted(
        TEST_DIR.glob("*.pdf")
    )

    if not pdf_files:

        print()
        print(
            "No PDF files found."
        )

        return 1

    # --------------------------------------------------------
    # RUN VALIDATION
    # --------------------------------------------------------

    results = []

    for pdf_path in pdf_files:

        result = validate_pdf(
            pdf_path
        )

        results.append(
            (
                pdf_path.name,
                result,
            )
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 78)
    print(
        "PHASE 7 - SECTION CONTENT VALIDATION SUMMARY"
    )
    print("=" * 78)

    print()

    print(
        f"{'PDF':35} "
        f"{'Status':22} "
        f"{'Expected':10} "
        f"{'Warnings':10}"
    )

    print("-" * 78)

    for filename, result in results:

        expected_total = (
            result.get(
                "expected_pass",
                0,
            )
            +
            result.get(
                "expected_fail",
                0,
            )
        )

        print(
            f"{filename:<35} "
            f"{result['status']:<22} "
            f"{expected_total:<10} "
            f"{result.get('warnings', 0):<10}"
        )

    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    pass_count = sum(
        1
        for _, result in results
        if result["status"] == "PASS"
    )

    warning_count = sum(
        1
        for _, result in results
        if result["status"]
        == "PASS_WITH_WARNINGS"
    )

    fail_count = sum(
        1
        for _, result in results
        if result["status"] == "FAIL"
    )

    ocr_count = sum(
        1
        for _, result in results
        if result["status"]
        == "OCR_REQUIRED"
    )

    print()

    print(
        f"Total PDFs          : "
        f"{len(results)}"
    )

    print(
        f"PASS                : "
        f"{pass_count}"
    )

    print(
        f"PASS_WITH_WARNINGS  : "
        f"{warning_count}"
    )

    print(
        f"FAIL                : "
        f"{fail_count}"
    )

    print(
        f"OCR_REQUIRED        : "
        f"{ocr_count}"
    )

    # --------------------------------------------------------
    # OVERALL STATUS
    # --------------------------------------------------------

    if fail_count > 0:

        overall_status = "FAIL"

    elif warning_count > 0:

        overall_status = "PASS_WITH_WARNINGS"

    else:

        overall_status = "PASS"

    print()

    print(
        f"PHASE 7 STATUS : "
        f"{overall_status}"
    )

    print()

    if overall_status == "PASS":

        print(
            "Section content validation passed."
        )

    elif overall_status == "PASS_WITH_WARNINGS":

        print(
            "Section content validation passed "
            "with warnings."
        )

    else:

        print(
            "Section content validation failed."
        )

    print()

    return 0 if fail_count == 0 else 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    sys.exit(main())