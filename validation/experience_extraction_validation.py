"""
Experience Extraction Validation
================================

Validates the existing experience extraction pipeline.

Production flow:

    experience section
            ↓
    experience_block_splitter
            ↓
    title extraction
            ↓
    title alias resolution
            ↓
    title validation
            ↓
    company extraction
            ↓
    company alias resolution
            ↓
    company validation
            ↓
    duration extraction
            ↓
    experience calculation
            ↓
    description extraction
            ↓
    location extraction
            ↓
    employment type
            ↓
    department
            ↓
    final experience objects

This validator does NOT implement extraction logic itself.
It validates the existing production implementation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# PRODUCTION IMPORTS
# ============================================================

from document_processing.resume.entity_extracter.experience.experinece_pipeline import (
    experience_extractor,
)

from document_processing.resume.experience_parser import (
    DATE_RANGE_RE,
    parse_experience_lines,
)

from document_processing.resume.entity_extracter.experience.experince_block_splitter import (
    split_experience_blocks,
)


# ============================================================
# VALIDATION COUNTERS
# ============================================================

TOTAL_TESTS = 0
PASSED_TESTS = 0
FAILED_TESTS = 0


# ============================================================
# TEST RESULT
# ============================================================

def run_test(
    test_name: str,
    condition: bool,
    details: str = "",
) -> None:

    global TOTAL_TESTS
    global PASSED_TESTS
    global FAILED_TESTS

    TOTAL_TESTS += 1

    if condition:

        PASSED_TESTS += 1

        print(
            f"[PASS] {test_name}"
        )

    else:

        FAILED_TESTS += 1

        print(
            f"[FAIL] {test_name}"
        )

        if details:
            print(
                f"       {details}"
            )


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value: Any) -> str:

    if value is None:
        return ""

    if isinstance(value, (list, tuple)):

        return " ".join(
            normalize_text(item)
            for item in value
        ).strip().lower()

    if isinstance(value, dict):

        return " ".join(
            normalize_text(item)
            for item in value.values()
        ).strip().lower()

    return str(value).strip().lower()


def get_field(
    experience: dict[str, Any],
    *names: str,
) -> Any:

    if not isinstance(experience, dict):
        return None

    for name in names:

        if name in experience:
            return experience[name]

    return None


def find_experience(
    experiences: list[dict[str, Any]],
    company: str | None = None,
    title: str | None = None,
) -> dict[str, Any] | None:

    target_company = (
        normalize_text(company)
        if company
        else None
    )

    target_title = (
        normalize_text(title)
        if title
        else None
    )

    for experience in experiences:

        if not isinstance(experience, dict):
            continue

        current_company = normalize_text(
            get_field(
                experience,
                "company",
                "company_name",
                "organization",
                "employer",
            )
        )

        current_title = normalize_text(
            get_field(
                experience,
                "title",
                "role",
                "job_title",
                "position",
            )
        )

        company_match = (
            target_company is None
            or target_company in current_company
        )

        title_match = (
            target_title is None
            or target_title in current_title
        )

        if company_match and title_match:
            return experience

    return None


def run_pipeline(
    experience_section: Any,
) -> list[dict[str, Any]]:

    try:

        result = experience_extractor(
            experience_section
        )

    except Exception as exc:

        print(
            f"       Pipeline exception: {exc}"
        )

        return []

    if result is None:
        return []

    if isinstance(result, list):

        return [
            item
            for item in result
            if isinstance(item, dict)
        ]

    if isinstance(result, dict):

        return [result]

    return []


# ============================================================
# TEST 1
# DATE RANGE RECOGNITION
# ============================================================

def test_date_range_recognition():

    valid_ranges = [
        "Jan 2022 - Dec 2024",
        "January 2022 - Present",
        "2020 - 2022",
        "2023 - Current",
        "Mar 2021 – Feb 2023",
    ]

    failed = []

    for value in valid_ranges:

        if not DATE_RANGE_RE.search(value):
            failed.append(value)

    run_test(
        "Date range recognition",
        not failed,
        f"Not recognized: {failed}",
    )


# ============================================================
# TEST 2
# BASIC EXPERIENCE PARSER
# ============================================================

def test_basic_parser():

    lines = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications using Django.",
        "Built REST APIs.",
    ]

    records = parse_experience_lines(lines)

    run_test(
        "Basic experience parser",
        len(records) == 1,
        f"Records: {records}",
    )


# ============================================================
# TEST 3
# PARSER TITLE
# ============================================================

def test_parser_title():

    lines = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications.",
    ]

    records = parse_experience_lines(lines)

    title = ""

    if records:
        title = normalize_text(
            records[0].get("title")
        )

    run_test(
        "Parser title extraction",
        "python developer" in title,
        f"Title: {title}",
    )


# ============================================================
# TEST 4
# PARSER COMPANY
# ============================================================

def test_parser_company():

    lines = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications.",
    ]

    records = parse_experience_lines(lines)

    company = ""

    if records:
        company = normalize_text(
            records[0].get("company")
        )

    run_test(
        "Parser company extraction",
        "abc technologies" in company,
        f"Company: {company}",
    )


# ============================================================
# TEST 5
# PARSER DESCRIPTION
# ============================================================

def test_parser_description():

    lines = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications using Django.",
        "Built REST APIs.",
    ]

    records = parse_experience_lines(lines)

    description = ""

    if records:
        description = normalize_text(
            records[0].get("description")
        )

    run_test(
        "Parser description extraction",
        (
            "python applications" in description
            and "rest apis" in description
        ),
        f"Description: {description}",
    )


# ============================================================
# TEST 6
# MULTIPLE EXPERIENCE PARSER
# ============================================================

def test_multiple_parser_records():

    lines = [
        "Python Developer",
        "ABC Technologies",
        "2022 - 2024",
        "Developed Django applications.",
        "Java Developer",
        "XYZ Solutions",
        "2019 - 2021",
        "Developed Java applications.",
    ]

    records = parse_experience_lines(lines)

    run_test(
        "Multiple experience parser records",
        len(records) == 2,
        f"Expected 2, got {len(records)}: {records}",
    )


# ============================================================
# TEST 7
# EXPERIENCE BLOCK SPLITTING
# ============================================================

def test_experience_block_splitting():

    lines = [
        "Python Developer - ABC Technologies",
        "2022 - 2024",
        "Developed Python applications.",
        "Java Developer - XYZ Solutions",
        "2019 - 2021",
        "Developed Java applications.",
    ]

    blocks = split_experience_blocks(lines)

    run_test(
        "Experience block splitting",
        len(blocks) == 2,
        f"Expected 2 blocks, got {len(blocks)}: {blocks}",
    )


# ============================================================
# TEST 8
# FULL PIPELINE - BASIC
# ============================================================

def test_pipeline_basic():

    experience_section = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications using Django.",
        "Built REST APIs.",
    ]

    result = run_pipeline(
        experience_section
    )

    run_test(
        "Full pipeline basic extraction",
        len(result) == 1,
        f"Result: {result}",
    )


# ============================================================
# TEST 9
# FINAL TITLE
# ============================================================

def test_pipeline_title():

    experience_section = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications using Django.",
    ]

    result = run_pipeline(
        experience_section
    )

    experience = find_experience(
        result,
        title="Python Developer",
    )

    run_test(
        "Final title extraction",
        experience is not None,
        f"Result: {result}",
    )


# ============================================================
# TEST 10
# FINAL COMPANY
# ============================================================

def test_pipeline_company():

    experience_section = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications using Django.",
    ]

    result = run_pipeline(
        experience_section
    )

    experience = find_experience(
        result,
        company="ABC Technologies",
    )

    run_test(
        "Final company extraction",
        experience is not None,
        f"Result: {result}",
    )


# ============================================================
# TEST 11
# FINAL DESCRIPTION
# ============================================================

def test_pipeline_description():

    experience_section = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications using Django.",
        "Built REST APIs.",
    ]

    result = run_pipeline(
        experience_section
    )

    experience = find_experience(
        result,
        company="ABC Technologies",
    )

    description = ""

    if experience:

        description = normalize_text(
            experience.get("description")
        )

    run_test(
        "Final description extraction",
        (
            "python" in description
            and "django" in description
        ),
        f"Description: {description}",
    )


# ============================================================
# TEST 12
# DURATION
# ============================================================

def test_duration():

    experience_section = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications.",
    ]

    result = run_pipeline(
        experience_section
    )

    experience = find_experience(
        result,
        company="ABC Technologies",
    )

    duration = None

    if experience:
        duration = experience.get(
            "duration"
        )

    run_test(
        "Duration extraction",
        duration is not None,
        f"Duration: {duration}",
    )


# ============================================================
# TEST 13
# TOTAL EXPERIENCE
# ============================================================

def test_total_experience():

    experience_section = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications.",
    ]

    result = run_pipeline(
        experience_section
    )

    experience = find_experience(
        result,
        company="ABC Technologies",
    )

    total_experience = None

    if experience:

        total_experience = experience.get(
            "total_experience"
        )

    run_test(
        "Total experience calculation",
        total_experience is not None,
        f"Total experience: {total_experience}",
    )


# ============================================================
# TEST 14
# CURRENT EXPERIENCE
# ============================================================

def test_current_experience():

    experience_section = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2024 - Present",
        "Developing Django REST APIs.",
    ]

    result = run_pipeline(
        experience_section
    )

    experience = find_experience(
        result,
        company="ABC Technologies",
    )

    duration = ""

    if experience:

        duration = normalize_text(
            experience.get("duration")
        )

    run_test(
        "Current experience handling",
        (
            experience is not None
            and (
                "present" in duration
                or "current" in duration
                or experience.get("duration") is not None
            )
        ),
        f"Experience: {experience}",
    )


# ============================================================
# TEST 15
# MULTIPLE EXPERIENCES - FULL PIPELINE
# ============================================================

def test_multiple_pipeline_experiences():

    experience_section = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications using Django.",
        "Java Developer",
        "XYZ Solutions",
        "Jan 2019 - Dec 2021",
        "Developed Java applications.",
    ]

    result = run_pipeline(
        experience_section
    )

    run_test(
        "Multiple experiences - full pipeline",
        len(result) == 2,
        f"Expected 2, got {len(result)}: {result}",
    )


# ============================================================
# TEST 16
# CAREER GAP
# ============================================================

def test_career_gap():

    experience_section = [
        "Java Developer",
        "Company A",
        "Jan 2019 - Dec 2020",
        "Developed Java applications.",
        "Python Developer",
        "Company B",
        "Jan 2024 - Present",
        "Developing Python applications.",
    ]

    result = run_pipeline(
        experience_section
    )

    run_test(
        "Career gap preserved",
        len(result) == 2,
        f"Expected 2 experiences, got {len(result)}: {result}",
    )


# ============================================================
# TEST 17
# TITLE-COMPANY SAME LINE
# ============================================================

def test_title_company_same_line():

    experience_section = [
        "Python Developer - ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications.",
    ]

    result = run_pipeline(
        experience_section
    )

    run_test(
        "Title-company combined line",
        len(result) >= 1,
        f"Result: {result}",
    )


# ============================================================
# TEST 18
# EMPTY INPUT
# ============================================================

def test_empty_input():

    result = run_pipeline([])

    run_test(
        "Empty experience handled safely",
        result == [],
        f"Result: {result}",
    )


# ============================================================
# TEST 19
# NONE INPUT
# ============================================================

def test_none_input():

    result = run_pipeline(None)

    run_test(
        "None experience handled safely",
        result == [],
        f"Result: {result}",
    )


# ============================================================
# TEST 20
# EXPERIENCE OBJECT STRUCTURE
# ============================================================

def test_final_object_structure():

    experience_section = [
        "Python Developer",
        "ABC Technologies",
        "Jan 2022 - Dec 2024",
        "Developed Python applications.",
    ]

    result = run_pipeline(
        experience_section
    )

    required_fields = {
        "title",
        "company",
        "duration",
        "total_experience",
        "location",
        "employment_type",
        "department",
        "description",
    }

    valid = False

    if result:

        first = result[0]

        valid = required_fields.issubset(
            first.keys()
        )

    run_test(
        "Final experience object structure",
        valid,
        f"Result: {result}",
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("EXPERIENCE EXTRACTION VALIDATION")
    print("=" * 80)
    print()

    test_date_range_recognition()
    test_basic_parser()
    test_parser_title()
    test_parser_company()
    test_parser_description()
    test_multiple_parser_records()
    test_experience_block_splitting()

    test_pipeline_basic()
    test_pipeline_title()
    test_pipeline_company()
    test_pipeline_description()
    test_duration()
    test_total_experience()
    test_current_experience()
    test_multiple_pipeline_experiences()
    test_career_gap()
    test_title_company_same_line()

    test_empty_input()
    test_none_input()
    test_final_object_structure()

    print()
    print("=" * 80)
    print("EXPERIENCE EXTRACTION VALIDATION SUMMARY")
    print("=" * 80)

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
        PASSED_TESTS / TOTAL_TESTS * 100
        if TOTAL_TESTS
        else 0
    )

    print(
        f"Pass rate   : {pass_rate:.2f}%"
    )

    print()

    if FAILED_TESTS == 0:
        print("STATUS: PASS")
    else:
        print("STATUS: FAIL")

    print("=" * 80)

    return 0 if FAILED_TESTS == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())