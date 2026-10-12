"""
education_extraction_validation.py

Education Extraction Validation
--------------------------------

Validates the complete education extraction pipeline:

    Education Section
        ↓
    Block Splitter
        ↓
    Degree Extraction
        ↓
    Degree Alias Resolution
        ↓
    School Classification
        ↓
    University Extraction
        ↓
    Institution Extraction
        ↓
    Board Extraction
        ↓
    Graduation Year
        ↓
    Field of Study
        ↓
    Field Alias Resolution
        ↓
    Post Processing
        ↓
    Final Education Records

Run:

    python validation education_extraction_validation.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from document_processing.resume.entity_extracter.education.education_block_splitter import (
    split_education_blocks,
    is_degree_start,
    is_school_start,
    is_university_continuation,
)

from document_processing.resume.entity_extracter.education.degree_type_extractor import (
    extract_degree_type,
)

from document_processing.resume.entity_extracter.education.degree_aliases_resolver import (
    resolve_degree_alias,
)

from document_processing.resume.entity_extracter.education.institution_extractor import (
    extract_institution,
    extract_board,
    extract_university_from_block,
)

from document_processing.resume.entity_extracter.education.graduation_year_extractor import (
    extract_graduation_year,
)

from document_processing.resume.entity_extracter.education.field_of_study_extractor import (
    extract_field_of_study,
)

from document_processing.resume.entity_extracter.education.field_aliase_resolver import (
    resolve_field_alias,
)

from document_processing.resume.entity_extracter.education.education_post_processor import (
    post_process_education,
    normalize_education_record,
    extract_board_from_field,
    clean_field_of_study,
    classify_school_record,
    merge_degree_records,
)

from document_processing.resume.entity_extracter.education.school_degree_classifier import (
    classify_school_degree,
)

from document_processing.resume.entity_extracter.education.university_extractor import (
    extract_university,
)


# ============================================================
# TEST RESULT STORAGE
# ============================================================

TOTAL_TESTS = 0
PASSED_TESTS = 0
FAILED_TESTS = 0


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value):
    """
    Normalize text for comparison only.
    """

    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


def contains_text(value, expected):
    """
    Case-insensitive containment check.
    """

    if value is None:
        return False

    return normalize_text(expected) in normalize_text(value)


def get_field(record, field):
    """
    Safely get a field from an education record.
    """

    if not isinstance(record, dict):
        return None

    return record.get(field)


def first_record(records):
    """
    Return first valid education record.
    """

    if not records:
        return None

    for record in records:
        if isinstance(record, dict):
            return record

    return None


def find_record(records, degree_text=None):
    """
    Find an education record containing the requested
    degree text.
    """

    if not records:
        return None

    for record in records:

        if not isinstance(record, dict):
            continue

        degree = record.get("degree_type")

        if degree_text is None:
            return record

        if contains_text(
            degree,
            degree_text,
        ):
            return record

    return None


def run_test(name, condition, details=""):
    """
    Execute one validation test.
    """

    global TOTAL_TESTS
    global PASSED_TESTS
    global FAILED_TESTS

    TOTAL_TESTS += 1

    if condition:

        PASSED_TESTS += 1

        print(
            f"[PASS] {name}"
        )

    else:

        FAILED_TESTS += 1

        print(
            f"[FAIL] {name}"
        )

        if details:
            print(
                f"       {details}"
            )


def run_pipeline(education):
    """
    Execute the real education pipeline.

    Imported here so that validation failures in an
    individual module can still be isolated.
    """

    from document_processing.resume.entity_extracter.education.education_pipeline import (
        education_pipeline,
    )

    return education_pipeline(
        education
    )


# ============================================================
# HEADER
# ============================================================

print(
    "\n"
    + "=" * 80
)

print(
    "EDUCATION EXTRACTION VALIDATION"
)

print(
    "=" * 80
)


# ============================================================
# 1. EDUCATION BLOCK SPLITTER
# ============================================================

education_basic = [
    "Bachelor of Technology in Computer Science",
    "ABC College of Engineering",
    "XYZ University",
    "2019 - 2023",
]


blocks = split_education_blocks(
    education_basic
)

run_test(
    "Education block splitting",
    len(blocks) >= 1,
    f"Blocks: {blocks}",
)


# ============================================================
# 2. DEGREE START DETECTION
# ============================================================

run_test(
    "Degree start detection",
    is_degree_start(
        "Bachelor of Technology in Computer Science"
    ),
)


# ============================================================
# 3. SCHOOL START DETECTION
# ============================================================

run_test(
    "School qualification detection",
    is_school_start(
        "All India Senior School Certificate Exam"
    ),
)


# ============================================================
# 4. UNIVERSITY CONTINUATION DETECTION
# ============================================================

run_test(
    "University continuation detection",
    is_university_continuation(
        "XYZ University"
    ),
)


# ============================================================
# 5. DEGREE EXTRACTION - FULL NAME
# ============================================================

degree_block = [
    "Bachelor of Technology in Computer Science",
    "ABC College of Engineering",
    "2019 - 2023",
]


degree = extract_degree_type(
    degree_block
)

run_test(
    "Full degree extraction",
    contains_text(
        degree,
        "Bachelor of Technology",
    ),
    f"Degree: {degree}",
)


# ============================================================
# 6. DEGREE EXTRACTION - ABBREVIATION
# ============================================================

degree_abbreviation = extract_degree_type(
    [
        "B.Tech Computer Science",
        "ABC College",
        "2023",
    ]
)

run_test(
    "Degree abbreviation extraction",
    contains_text(
        degree_abbreviation,
        "B.Tech",
    ),
    f"Degree: {degree_abbreviation}",
)


# ============================================================
# 7. DEGREE EXTRACTION - B.COM
# ============================================================

bcom_degree = extract_degree_type(
    [
        "B.Com. Finance",
        "ABC College",
        "2025",
    ]
)

run_test(
    "B.Com degree extraction",
    bcom_degree is not None
    and "com" in normalize_text(
        bcom_degree
    ),
    f"Degree: {bcom_degree}",
)


# ============================================================
# 8. DEGREE ALIAS RESOLUTION
# ============================================================

resolved_degree = resolve_degree_alias(
    degree_abbreviation
)

run_test(
    "Degree alias resolution",
    resolved_degree is not None
    and isinstance(
        resolved_degree,
        str,
    ),
    f"Resolved degree: {resolved_degree}",
)


# ============================================================
# 9. UNIVERSITY EXTRACTION
# ============================================================

university_result = extract_university(
    "ABC Technological University"
)

run_test(
    "University extraction",
    university_result is not None
    and university_result.get(
        "value"
    ),
    f"University result: {university_result}",
)


# ============================================================
# 10. UNKNOWN UNIVERSITY FALLBACK
# ============================================================

unknown_university = extract_university(
    "Random Example University"
)

run_test(
    "Unknown university fallback",
    unknown_university is not None
    and unknown_university.get(
        "value"
    ) == "Random Example University",
    f"University result: {unknown_university}",
)


# ============================================================
# 11. INSTITUTION EXTRACTION
# ============================================================

institution_block = [
    "Bachelor of Technology in Computer Science",
    "ABC College of Engineering",
    "Random Example University",
    "2019 - 2023",
]

institution_university = (
    extract_university_from_block(
        institution_block
    )
)

institution = extract_institution(
    institution_block,
    institution_university,
)

run_test(
    "Institution extraction",
    institution is not None
    and "college" in normalize_text(
        institution
    ),
    f"Institution: {institution}",
)


# ============================================================
# ============================================================
# 12. BOARD EXTRACTION
# ============================================================

school_block = [
    "Higher Secondary School",
    "ABC Higher Secondary School",
    "Kerala Board",
    "2020",
]

board = extract_board(
    school_block
)

run_test(
    "Board extraction",
    board is not None
    and contains_text(
        board,
        "Kerala Board",
    ),
    f"Board: {board}",
)


# ============================================================
# 13. GRADUATION YEAR EXTRACTION
# ============================================================

graduation_year = extract_graduation_year(
    [
        "Bachelor of Technology",
        "ABC College",
        "XYZ University",
        "2019 - 2023",
    ]
)

run_test(
    "Graduation year extraction",
    graduation_year is not None
    and "2023" in str(graduation_year),
    f"Graduation year: {graduation_year}",
)


# ============================================================
# 14. FIELD OF STUDY EXTRACTION
# ============================================================

field_block = [
    "Bachelor of Technology in Computer Science",
    "ABC College of Engineering",
    "XYZ University",
    "2019 - 2023",
]

field = extract_field_of_study(
    field_block
)

run_test(
    "Field of study extraction",
    field is not None
    and contains_text(
        field,
        "Computer Science",
    ),
    f"Field of study: {field}",
)


# ============================================================
# 15. FIELD ALIAS RESOLUTION
# ============================================================

resolved_field = resolve_field_alias(
    field
)

run_test(
    "Field alias resolution",
    resolved_field is not None
    and isinstance(
        resolved_field,
        str,
    ),
    f"Resolved field: {resolved_field}",
)


# ============================================================
# 16. SCHOOL DEGREE CLASSIFICATION
# ============================================================

school_degree = classify_school_degree(
    [
        "All India Senior School Certificate Examination",
        "Kerala Board",
        "2020",
    ]
)

run_test(
    "School degree classification",
    school_degree == "Higher Secondary",
    f"School degree: {school_degree}",
)

# ============================================================
# 17. SCHOOL RECORD CLASSIFICATION
# ============================================================

school_record = {
    "degree_type": "Higher Secondary",
    "institution": "ABC Higher Secondary School",
    "board": "Kerala Board",
    "graduation_year": "2020",
}

classified_school = classify_school_record(
    school_record
)

run_test(
    "School record classification",
    classified_school is not None,
    f"Classified school record: {classified_school}",
)


# ============================================================
# 18. BOARD FROM FIELD EXTRACTION
# ============================================================

board_from_field = extract_board_from_field(
    "Central Board of Secondary Education"
)

run_test(
    "Board extraction from field",
    board_from_field == (
        "Central Board of Secondary Education"
    ),
    f"Board from field: {board_from_field}",
)

# ============================================================
# 18B. NORMAL FIELD IS NOT A BOARD
# ============================================================

normal_field_board = extract_board_from_field(
    "Computer Science"
)

run_test(
    "Normal field not classified as board",
    normal_field_board is None,
    f"Board from normal field: {normal_field_board}",
)


# ============================================================
# 19. FIELD CLEANING
# ============================================================

cleaned_field = clean_field_of_study(
    "Computer Science - ABC University"
)

run_test(
    "Field of study cleaning",
    cleaned_field is not None
    and isinstance(
        cleaned_field,
        str,
    ),
    f"Cleaned field: {cleaned_field}",
)


# ============================================================
# 20. EDUCATION RECORD NORMALIZATION
# ============================================================

raw_record = {
    "degree_type": "B.Tech",
    "institution": "ABC College of Engineering",
    "university": "XYZ University",
    "graduation_year": "2023",
    "field_of_study": "Computer Science",
}

normalized_record = normalize_education_record(
    raw_record
)

run_test(
    "Education record normalization",
    normalized_record is not None
    and isinstance(
        normalized_record,
        dict,
    ),
    f"Normalized record: {normalized_record}",
)


# ============================================================
# 21. DEGREE RECORD MERGING
# ============================================================

degree_records = [
    {
        "degree_type": "B.Tech",
        "institution": "ABC College",
        "university": "XYZ University",
        "graduation_year": "2023",
    },
    {
        "degree_type": "B.Tech",
        "institution": "ABC College",
        "university": "XYZ University",
        "graduation_year": "2023",
    },
]

merged_records = merge_degree_records(
    degree_records
)

run_test(
    "Degree record merging",
    merged_records is not None,
    f"Merged records: {merged_records}",
)


# ============================================================
# 22. EMPTY EDUCATION INPUT
# ============================================================

empty_result = run_pipeline([])

run_test(
    "Empty education handled safely",
    empty_result == []
    or empty_result is None,
    f"Result: {empty_result}",
)


# ============================================================
# 23. NONE EDUCATION INPUT
# ============================================================

none_result = run_pipeline(None)

run_test(
    "None education handled safely",
    none_result == []
    or none_result is None,
    f"Result: {none_result}",
)


# ============================================================
# 24. MULTIPLE EDUCATION RECORDS
# ============================================================

multiple_education = [
    "Bachelor of Technology in Computer Science",
    "ABC College of Engineering",
    "XYZ University",
    "2019 - 2023",

    "Higher Secondary",
    "Government Higher Secondary School",
    "Kerala Board",
    "2017 - 2019",
]

multiple_result = run_pipeline(
    multiple_education
)

run_test(
    "Multiple education records",
    isinstance(
        multiple_result,
        list,
    )
    and len(multiple_result) >= 2,
    f"Records: {multiple_result}",
)


# ============================================================
# 25. FINAL EDUCATION OBJECT STRUCTURE
# ============================================================

final_result = run_pipeline(
    [
        "Bachelor of Technology in Computer Science",
        "ABC College of Engineering",
        "XYZ University",
        "2019 - 2023",
    ]
)

final_record = first_record(
    final_result
)

expected_fields = {
    "degree_type",
    "institution",
    "university",
    "graduation_year",
    "field_of_study",
}

actual_fields = (
    set(final_record.keys())
    if isinstance(final_record, dict)
    else set()
)

run_test(
    "Final education object structure",
    isinstance(final_record, dict)
    and expected_fields.issubset(
        actual_fields
    ),
    f"Record: {final_record}",
)


# ============================================================
# 26. FULL EDUCATION PIPELINE INTEGRATION
# ============================================================

integration_result = run_pipeline(
    [
        "Bachelor of Technology in Computer Science",
        "ABC College of Engineering",
        "XYZ University",
        "2019 - 2023",
    ]
)

integration_record = first_record(
    integration_result
)

run_test(
    "Full education pipeline integration",
    isinstance(
        integration_result,
        list,
    )
    and len(integration_result) >= 1
    and isinstance(
        integration_record,
        dict,
    )
    and integration_record.get(
        "degree_type"
    ),
    f"Pipeline result: {integration_result}",
)

# ============================================================
# 28. KTU UNIVERSITY MUST NOT BECOME INSTITUTION
# ============================================================

ktu_block = [
    "B.Tech Computer Science",
    "ABC College of Engineering",
    "KTU",
    "2019 - 2023",
]

ktu_university = extract_university_from_block(
    ktu_block
)

ktu_institution = extract_institution(
    ktu_block,
    ktu_university,
)

run_test(
    "KTU university not classified as institution",
    ktu_institution is not None
    and "college" in normalize_text(
        ktu_institution
    )
    and "ktu" not in normalize_text(
        ktu_institution
    ),
    (
        f"Institution: {ktu_institution} | "
        f"University: {ktu_university}"
    ),
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print(
    "\n"
    + "=" * 80
)

print(
    "EDUCATION VALIDATION SUMMARY"
)

print(
    "=" * 80
)

print(
    f"Total tests : {TOTAL_TESTS}"
)

print(
    f"Passed      : {PASSED_TESTS}"
)

print(
    f"Failed      : {FAILED_TESTS}"
)

pass_rate = (
    (PASSED_TESTS / TOTAL_TESTS) * 100
    if TOTAL_TESTS
    else 0
)

print(
    f"Pass rate   : {pass_rate:.2f}%"
)

print(
    "STATUS      : "
    + (
        "PASS"
        if FAILED_TESTS == 0
        else "FAIL"
    )
)

print(
    "=" * 80
)
