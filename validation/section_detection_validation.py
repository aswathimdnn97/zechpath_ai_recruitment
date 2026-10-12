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
# CANONICAL SECTIONS
# ============================================================

CANONICAL_SECTIONS = {
    "summary",
    "skills",
    "experience",
    "education",
    "projects",
    "certifications",
    "achievements",
    "languages",
    "interests",
    "references",
    "activities",
    "declaration",
    "publications",
}


# ============================================================
# SKILL SUBSECTIONS
# ============================================================

SKILL_SUBSECTIONS = {
    "languages",
    "language",
    "backend",
    "frontend",
    "databases",
    "database",
    "libraries",
    "library",
    "frameworks",
    "framework",
    "testing",
    "tools",
    "tool",
    "platforms",
    "cloud",
    "devops",
    "web technologies",
    "programming languages",
    "operating systems",
    "development tools",
    "database skills",
    "web technology",
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize_for_comparison(value):
    """
    Normalize text for validation comparisons.
    """

    if value is None:
        return ""

    value = str(value).lower()

    value = value.replace("\u00a0", " ")

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_line(value):
    """
    Normalize one line for heading comparisons.
    """

    if value is None:
        return ""

    value = str(value)

    value = value.replace("\u00a0", " ")

    value = re.sub(
        r"^[\s•●▪◦○\-*]+",
        "",
        value,
    )

    value = re.sub(
        r"^\s*\d+[\.\)]\s*",
        "",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip().lower()


def flatten_sections(sections):
    """
    Convert nested section blocks into one list of lines.

    Example:

        {
            "skills": [
                ["Python", "SQL"],
                ["Django"]
            ]
        }

    becomes:

        {
            "skills": [
                "Python",
                "SQL",
                "Django"
            ]
        }
    """

    flattened = {}

    for section_name, blocks in sections.items():

        flattened[section_name] = []

        if not isinstance(blocks, list):
            continue

        for block in blocks:

            if isinstance(block, list):

                for line in block:

                    if isinstance(line, str) and line.strip():

                        flattened[section_name].append(
                            line.strip()
                        )

            elif isinstance(block, str):

                if block.strip():

                    flattened[section_name].append(
                        block.strip()
                    )

    return flattened


def section_text(sections, section_name):
    """
    Return complete text of one section.
    """

    lines = sections.get(
        section_name,
        [],
    )

    return normalize_for_comparison(
        " ".join(lines)
    )


def count_words(text):

    return len(
        re.findall(
            r"\b[\w.+#/-]+\b",
            text or "",
        )
    )


def count_lines(sections):

    total = 0

    for lines in sections.values():

        total += len(lines)

    return total


# ============================================================
# PIPELINE
# ============================================================

def extract_normalized_text(pdf_path):
    """
    Run the real ATS text-processing pipeline.

    PDF
      -> PDF reader
      -> cleaner
      -> layout fixer
      -> text reconstruction
      -> normalizer
    """

    raw_text = read_pdf(
        str(pdf_path)
    )

    if not raw_text or not raw_text.strip():

        return "", "OCR_REQUIRED"

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

        return "", "NO_TEXT_AFTER_NORMALIZATION"

    return normalized, "TEXT_AVAILABLE"


# ============================================================
# SECTION NAME VALIDATION
# ============================================================

def validate_section_names(sections):

    errors = []

    detected = set(
        sections.keys()
    )

    unexpected = sorted(
        detected - CANONICAL_SECTIONS
    )

    for section in unexpected:

        errors.append(
            f"Unexpected canonical section: {section}"
        )

    return errors


# ============================================================
# DUPLICATE CANONICAL KEY VALIDATION
# ============================================================

def validate_duplicate_sections(sections):

    errors = []

    keys = list(
        sections.keys()
    )

    normalized_keys = [
        normalize_for_comparison(key)
        for key in keys
    ]

    if len(normalized_keys) != len(
        set(normalized_keys)
    ):

        errors.append(
            "Duplicate canonical section keys detected"
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
# SKILL SUBSECTION VALIDATION
# ============================================================

def validate_skill_subsections(
    normalized_text,
    sections,
):
    """
    Validate skill subsection behavior.

    Important:

    A top-level "languages" section is NOT automatically
    an error.

    Example:

        Skills
        Languages
        Python, SQL

    should produce:

        skills

    But:

        Languages
        English, Malayalam

    should legitimately produce:

        languages
    """

    errors = []

    normalized_lines = [
        normalize_line(line)
        for line in normalized_text.splitlines()
        if line.strip()
    ]

    # --------------------------------------------------------
    # If skills does not exist, a top-level languages section
    # may be completely legitimate.
    # --------------------------------------------------------

    if "skills" not in sections:

        return errors

    # --------------------------------------------------------
    # If skills exists, skill subsection headings should not
    # become separate top-level sections.
    # --------------------------------------------------------

    for subsection in SKILL_SUBSECTIONS:

        if subsection not in sections:
            continue

        # ----------------------------------------------------
        # "languages" is special because it is also a valid
        # top-level resume section.
        # ----------------------------------------------------

        if subsection == "languages":

            # If "languages" exists alongside "skills", this
            # indicates that detector probably failed to keep
            # the subsection inside skills.
            errors.append(
                "Skill subsection incorrectly detected as "
                "top-level section: languages"
            )

        else:

            errors.append(
                "Skill subsection incorrectly detected as "
                f"top-level section: {subsection}"
            )

    return errors


# ============================================================
# SKILL SUBSECTION STRUCTURE TEST
# ============================================================

def validate_skill_subsection_structure():

    """
    Independent unit-style validation of the detector's
    intended skill-subsection behavior.

    This does NOT depend on a PDF.
    """

    errors = []

    # --------------------------------------------------------
    # CASE 1
    # Skill subsections should remain inside skills.
    # --------------------------------------------------------

    skills_text = """
    Summary
    Python developer

    Skills
    Languages
    Python, SQL

    Backend
    FastAPI, Django

    Databases
    PostgreSQL, MySQL

    Experience
    Python Developer
    """

    result = detect_sections(
        skills_text,
        headings_override=heading_aliases,
    )

    if "skills" not in result:

        errors.append(
            "Synthetic skill test: skills section not detected"
        )

    if "languages" in result:

        errors.append(
            "Synthetic skill test: languages incorrectly "
            "detected as top-level section"
        )

    # --------------------------------------------------------
    # CASE 2
    # A genuine top-level Languages section must remain
    # top-level when it is outside Skills.
    # --------------------------------------------------------

    languages_text = """
    Summary
    Python developer

    Experience
    Python Developer

    Languages
    English
    Malayalam

    Education
    B.Tech
    """

    result = detect_sections(
        languages_text,
        headings_override=heading_aliases,
    )

    if "languages" not in result:

        errors.append(
            "Synthetic language test: top-level languages "
            "section was not detected"
        )

    return errors


# ============================================================
# CONTENT PRESERVATION
# ============================================================

def validate_content_presence(
    normalized_text,
    sections,
):
    """
    Verify that detected section content originated from the
    normalized text.
    """

    errors = []

    normalized_text = normalize_for_comparison(
        normalized_text
    )

    for section_name, lines in sections.items():

        for line in lines:

            normalized_line = normalize_for_comparison(
                line
            )

            if not normalized_line:
                continue

            # Very short strings are ignored because values such
            # as "C", "SQL", "IT", etc. are not reliable
            # substring validation targets.
            if len(normalized_line) <= 10:
                continue

            if normalized_line not in normalized_text:

                errors.append(
                    "Section content not found in normalized "
                    f"text: {section_name} -> {line}"
                )

    return errors


# ============================================================
# SECTION CONTENT QUALITY
# ============================================================

def validate_section_content(sections):

    errors = []

    for section_name, lines in sections.items():

        if not lines:
            errors.append(
                f"Section has no content lines: {section_name}"
            )
            continue

        valid_lines = [
            line
            for line in lines
            if isinstance(line, str)
            and line.strip()
        ]

        if not valid_lines:

            errors.append(
                f"Section has no usable content: {section_name}"
            )

    return errors


# ============================================================
# CROSS SECTION DUPLICATION
# ============================================================

def validate_cross_section_duplicates(sections):

    warnings = []

    section_names = list(
        sections.keys()
    )

    normalized_content = {}

    for name in section_names:

        normalized_content[name] = section_text(
            sections,
            name,
        )

    for i, first in enumerate(section_names):

        first_words = set(
            normalized_content[first].split()
        )

        if not first_words:
            continue

        for second in section_names[i + 1:]:

            second_words = set(
                normalized_content[second].split()
            )

            if not second_words:
                continue

            overlap = (
                len(
                    first_words & second_words
                )
                / max(
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
                    f"{first} and {second}"
                )

    return warnings


# ============================================================
# SECTION ORDER
# ============================================================

def report_section_order(sections):

    """
    Section ordering is informational only.

    It is NOT considered a validation warning/error because:
    - resumes legitimately use different orders
    - two-column PDFs can change physical extraction order
    - ATS systems should not reject a resume because of order
    """

    preferred_order = [
        "summary",
        "skills",
        "experience",
        "education",
        "projects",
        "certifications",
        "achievements",
        "languages",
        "interests",
        "activities",
        "publications",
        "references",
        "declaration",
    ]

    positions = []

    for section in sections:

        if section in preferred_order:

            positions.append(
                preferred_order.index(section)
            )

    if positions != sorted(positions):

        return "Non-standard section ordering"

    return "Standard section ordering"


# ============================================================
# UNKNOWN HEADING-LIKE LINES
# ============================================================

def find_known_heading_lines(normalized_text):

    """
    Identify heading lines that are explicitly known by the
    project's heading vocabulary.

    This is useful for checking whether known aliases were
    actually recognized by the detector.
    """

    known_aliases = set()

    for alias in heading_aliases:

        known_aliases.add(
            normalize_line(alias)
        )

    lines = [
        normalize_line(line)
        for line in normalized_text.splitlines()
        if line.strip()
    ]

    return [
        line
        for line in lines
        if line in known_aliases
    ]


def validate_known_heading_detection(
    normalized_text,
    sections,
):
    """
    Every known top-level heading should result in a
    corresponding canonical section, except skill
    subsections.
    """

    warnings = []

    known_heading_lines = (
        find_known_heading_lines(
            normalized_text
        )
    )

    # --------------------------------------------------------
    # Canonical aliases that can legitimately appear inside
    # the skills section.
    # --------------------------------------------------------

    skill_subsections = {
        normalize_line(value)
        for value in SKILL_SUBSECTIONS
    }

    canonical_alias_map = {}

    for alias in heading_aliases:

        normalized_alias = normalize_line(
            alias
        )

        canonical_alias_map[
            normalized_alias
        ] = normalized_alias

    for heading_line in known_heading_lines:

        if heading_line in skill_subsections:

            continue

        # ----------------------------------------------------
        # Resolve the heading using the actual detector.
        # ----------------------------------------------------

        detected = False

        for section_name in sections:

            if normalize_line(section_name) == heading_line:

                detected = True
                break

        # ----------------------------------------------------
        # The alias itself may map to a different canonical
        # name, so check the project's actual detector mapping
        # by running a tiny synthetic input.
        # ----------------------------------------------------

        if not detected:

            test_result = detect_sections(
                heading_line,
                headings_override=heading_aliases,
            )

            if not test_result:

                warnings.append(
                    "Known heading was not detected: "
                    f"{heading_line}"
                )

    return warnings


# ============================================================
# SINGLE PDF VALIDATION
# ============================================================

def validate_pdf(pdf_path):

    start_time = time.perf_counter()

    normalized_text, text_status = (
        extract_normalized_text(
            pdf_path
        )
    )

    elapsed = (
        time.perf_counter()
        - start_time
    )

    print()
    print("=" * 70)

    print(
        f"PDF                 : {pdf_path.name}"
    )

    print(
        f"Status              : {text_status}"
    )

    print(
        f"Time                : {elapsed:.3f} sec"
    )

    # --------------------------------------------------------
    # OCR REQUIRED
    # --------------------------------------------------------

    if text_status == "OCR_REQUIRED":

        print()
        print(
            "PDF contains no extractable text."
        )

        print(
            "Section detection skipped."
        )

        print(
            "OCR may be required."
        )

        return {
            "status": "OCR_REQUIRED",
            "time": elapsed,
        }

    # --------------------------------------------------------
    # NO TEXT
    # --------------------------------------------------------

    if text_status != "TEXT_AVAILABLE":

        print()
        print(
            "No normalized text available."
        )

        return {
            "status": "FAIL",
            "time": elapsed,
            "errors": [
                text_status
            ],
            "warnings": [],
            "sections": [],
            "section_count": 0,
        }

    # --------------------------------------------------------
    # SHOW NORMALIZED TEXT
    # --------------------------------------------------------

    print()
    print("NORMALIZED TEXT")
    print("-" * 70)

    print(normalized_text)

    print("-" * 70)

    # --------------------------------------------------------
    # DETECT SECTIONS
    # --------------------------------------------------------

    sections = detect_sections(
        normalized_text,
        headings_override=heading_aliases,
    )

    flattened = flatten_sections(
        sections
    )

    detected_sections = list(
        flattened.keys()
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    errors = []
    warnings = []

    # --------------------------------------------------------
    # Canonical section names
    # --------------------------------------------------------

    errors.extend(
        validate_section_names(
            flattened
        )
    )

    # --------------------------------------------------------
    # Duplicate canonical keys
    # --------------------------------------------------------

    errors.extend(
        validate_duplicate_sections(
            flattened
        )
    )

    # --------------------------------------------------------
    # Empty sections
    # --------------------------------------------------------

    errors.extend(
        validate_empty_sections(
            flattened
        )
    )

    # --------------------------------------------------------
    # Section content
    # --------------------------------------------------------

    errors.extend(
        validate_section_content(
            flattened
        )
    )

    # --------------------------------------------------------
    # Skill subsection behavior
    # --------------------------------------------------------

    errors.extend(
        validate_skill_subsections(
            normalized_text,
            flattened,
        )
    )

    # --------------------------------------------------------
    # Content preservation
    # --------------------------------------------------------

    errors.extend(
        validate_content_presence(
            normalized_text,
            flattened,
        )
    )

    # --------------------------------------------------------
    # Cross-section duplication
    # --------------------------------------------------------

    warnings.extend(
        validate_cross_section_duplicates(
            flattened
        )
    )

    # --------------------------------------------------------
    # Section order is informational only
    # --------------------------------------------------------

    section_order_status = (
        report_section_order(
            flattened
        )
    )

    # --------------------------------------------------------
    # Known heading recognition
    # --------------------------------------------------------

    warnings.extend(
        validate_known_heading_detection(
            normalized_text,
            flattened,
        )
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    print()
    print("SECTION DETECTION")
    print("-" * 70)

    print(
        f"Detected sections       : "
        f"{len(detected_sections)}"
    )

    print(
        f"Detected lines          : "
        f"{count_lines(flattened)}"
    )

    print(
        f"Normalized words        : "
        f"{count_words(normalized_text)}"
    )

    print(
        f"Section order           : "
        f"{section_order_status}"
    )

    print()
    print("DETECTED SECTIONS")
    print("-" * 70)

    if detected_sections:

        for section in detected_sections:

            lines = flattened.get(
                section,
                [],
            )

            words = count_words(
                " ".join(lines)
            )

            print(
                f"{section:<25} "
                f"lines={len(lines):<4} "
                f"words={words}"
            )

    else:

        print(
            "No sections detected."
        )

    # --------------------------------------------------------
    # ERRORS
    # --------------------------------------------------------

    print()
    print("SECTION SAFETY")
    print("-" * 70)

    print(
        f"Errors                  : "
        f"{len(errors)}"
    )

    print(
        f"Warnings                : "
        f"{len(warnings)}"
    )

    if errors:

        print()
        print("ERROR DETAILS")
        print("-" * 70)

        for error in errors:

            print(
                f"[ERROR] {error}"
            )

    if warnings:

        print()
        print("WARNING DETAILS")
        print("-" * 70)

        for warning in warnings:

            print(
                f"[WARNING] {warning}"
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
        f"SECTION DETECTION STATUS : {status}"
    )

    return {
        "status": status,
        "time": elapsed,
        "sections": detected_sections,
        "section_count": len(
            detected_sections
        ),
        "errors": errors,
        "warnings": warnings,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "PHASE 6 - SECTION DETECTION VALIDATION"
    )

    print("=" * 70)

    print()
    print("Validation stages:")

    print(
        "PDF -> PDF Reader -> clean_text() -> "
        "fix_layout() -> reconstruct_text() -> "
        "normalize_text() -> detect_sections()"
    )

    print()
    print("Test folder:")

    print(TEST_DIR)

    # --------------------------------------------------------
    # Synthetic detector validation
    # --------------------------------------------------------

    print()
    print("=" * 70)

    print(
        "SYNTHETIC SECTION DETECTOR TESTS"
    )

    print("=" * 70)

    synthetic_errors = (
        validate_skill_subsection_structure()
    )

    if synthetic_errors:

        print()

        for error in synthetic_errors:

            print(
                f"[ERROR] {error}"
            )

    else:

        print()
        print(
            "Skill subsection behavior : PASS"
        )

    # --------------------------------------------------------
    # Test directory
    # --------------------------------------------------------

    if not TEST_DIR.exists():

        print()

        print(
            f"ERROR: Test folder not found: "
            f"{TEST_DIR}"
        )

        return

    pdf_files = sorted(
        TEST_DIR.glob("*.pdf")
    )

    if not pdf_files:

        print()

        print(
            "No PDF files found."
        )

        return

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
    print("=" * 70)

    print(
        "PHASE 6 - SECTION DETECTION VALIDATION SUMMARY"
    )

    print("=" * 70)

    print()

    print(
        f"{'PDF':<35} "
        f"{'Status':<20} "
        f"{'Sections':<10}"
    )

    print("-" * 70)

    for filename, result in results:

        print(
            f"{filename:<35} "
            f"{result['status']:<20} "
            f"{result.get('section_count', '-'): <10}"
        )

    # --------------------------------------------------------
    # Counts
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
        f"Total PDFs          : {len(results)}"
    )

    print(
        f"PASS                : {pass_count}"
    )

    print(
        f"PASS_WITH_WARNINGS  : {warning_count}"
    )

    print(
        f"FAIL                : {fail_count}"
    )

    print(
        f"OCR_REQUIRED        : {ocr_count}"
    )

    # --------------------------------------------------------
    # Synthetic test affects overall result
    # --------------------------------------------------------

    if synthetic_errors:

        overall_status = "FAIL"

    elif fail_count > 0:

        overall_status = "FAIL"

    elif warning_count > 0:

        overall_status = "PASS_WITH_WARNINGS"

    else:

        overall_status = "PASS"

    print()

    print(
        f"PHASE 6 STATUS : {overall_status}"
    )

    print()

    if overall_status == "PASS":

        print(
            "Section detection validation passed."
        )

    elif overall_status == "PASS_WITH_WARNINGS":

        print(
            "Section detection passed with warnings."
        )

    else:

        print(
            "Section detection validation failed."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()