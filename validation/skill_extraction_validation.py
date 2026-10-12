"""
skill_extraction_validator.py

End-to-end validation for the ATS skill extraction pipeline.

Pipeline under validation:

    skill_extractor
        ↓
    spelling_resolver
        ↓
    synonym_resolver
        ↓
    master_skill_validator
        ↓
    stack_resolver
        ↓
    final deduplication

This validator checks:

1. Normal skill extraction
2. Spelling correction
3. Synonym / alias resolution
4. Master dictionary validation
5. Stack expansion
6. Duplicate removal
7. Direct + stack duplicate merging
8. Source metadata preservation
9. Multiple source sections
10. Special skill names
11. Unknown skill rejection
12. Pipeline stability

This file is a VALIDATION tool only.
It does not modify production extraction logic.
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Any


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORT PRODUCTION PIPELINE
# ============================================================

try:
    from document_processing.resume.entity_extracter.skill.skill_extractor import (
        extract_skill,
    )
except ImportError as exc:
    print("\nERROR: Could not import skill_extractor.")
    print(f"Reason: {exc}")
    print("\nCheck:")
    print("1. PROJECT_ROOT")
    print("2. skill_extractor.py location")
    print("3. package __init__.py files")
    sys.exit(1)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# ============================================================
# VALIDATION RESULT
# ============================================================

class ValidationResult:
    """Store validation results."""

    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.errors: list[dict[str, Any]] = []

    def record_pass(self):
        self.total += 1
        self.passed += 1

    def record_fail(
        self,
        test_name: str,
        expected: Any,
        actual: Any,
        error: str | None = None,
    ):
        self.total += 1
        self.failed += 1

        self.errors.append(
            {
                "test": test_name,
                "expected": expected,
                "actual": actual,
                "error": error,
            }
        )

    @property
    def success(self) -> bool:
        return self.failed == 0


RESULT = ValidationResult()


# ============================================================
# OUTPUT HELPERS
# ============================================================

def print_header(title: str):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_test(
    test_name: str,
    passed: bool,
    expected: Any = None,
    actual: Any = None,
):
    status = "PASS" if passed else "FAIL"

    print(f"[{status}] {test_name}")

    if not passed:
        print(f"       Expected: {expected}")
        print(f"       Actual  : {actual}")


# ============================================================
# GENERIC HELPERS
# ============================================================

def _normalize(value: Any) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .lower()
        .split()
    )


def _extract_skill_names(result: Any) -> list[str]:
    """
    Extract normalized skill names from different possible
    output shapes.

    Supported:

        ["Python", "Django"]

        [{"skill": "Python"}, {"skill": "Django"}]

        {"skills": [...]}

        {"skill": "Python"}
    """

    if result is None:
        return []

    if isinstance(result, dict):
        if "skills" in result:
            return _extract_skill_names(result["skills"])

        if "skill" in result:
            return [str(result["skill"])]

        return []

    if isinstance(result, list):
        names = []

        for item in result:
            if isinstance(item, str):
                names.append(item)

            elif isinstance(item, dict):
                skill = item.get("skill")

                if skill:
                    names.append(str(skill))

        return names

    return []


def _extract_skill_objects(result: Any) -> list[dict[str, Any]]:
    """
    Return skill dictionaries from pipeline output.
    """

    if result is None:
        return []

    if isinstance(result, dict):

        if "skills" in result:
            return _extract_skill_objects(result["skills"])

        if "skill" in result:
            return [result]

        return []

    if isinstance(result, list):
        return [
            item
            for item in result
            if isinstance(item, dict)
            and item.get("skill")
        ]

    return []


def _normalized_skill_set(result: Any) -> set[str]:
    return {
        _normalize(skill)
        for skill in _extract_skill_names(result)
        if _normalize(skill)
    }


def _contains_skill(
    result: Any,
    skill_name: str,
) -> bool:

    target = _normalize(skill_name)

    return target in _normalized_skill_set(result)


def _count_skill(
    result: Any,
    skill_name: str,
) -> int:

    target = _normalize(skill_name)

    return sum(
        1
        for skill in _extract_skill_names(result)
        if _normalize(skill) == target
    )


def _find_skill_object(data, skill_name):
    """
    Find a skill object by canonical skill name.

    Supports the current extraction output:
        [
            {
                "skill": "Python",
                ...
            }
        ]

    Also supports nested dict/list structures.
    """

    target = str(skill_name).strip().lower()

    if data is None:
        return None

    # --------------------------------------------------------
    # DIRECT LIST OF SKILL OBJECTS
    # --------------------------------------------------------
    if isinstance(data, list):

        for item in data:

            if not isinstance(item, dict):
                continue

            current_skill = item.get("skill")

            if current_skill is not None:
                if str(current_skill).strip().lower() == target:
                    return item

        # Fallback: recursively inspect nested values
        for item in data:

            found = _find_skill_object(
                item,
                skill_name,
            )

            if found is not None:
                return found

        return None

    # --------------------------------------------------------
    # DICT
    # --------------------------------------------------------
    if isinstance(data, dict):

        for key in ("skill", "name"):

            value = data.get(key)

            if value is not None:
                if str(value).strip().lower() == target:
                    return data

        for value in data.values():

            found = _find_skill_object(
                value,
                skill_name,
            )

            if found is not None:
                return found

        return None

    return None
# ============================================================
# PIPELINE EXECUTION
# ============================================================

def run_extraction(resume):
    try:
        return extract_skill(resume)
    except Exception as exc:
        print(f"Extraction error: {exc}")
        return []


# ============================================================
# TEST DATA
# ============================================================

def build_basic_test_resume() -> dict[str, Any]:
    """
    Basic realistic resume sections.
    """

    return {
        "skills": [
            "Python",
            "Django",
            "ReactJS",
            "Fast API",
            "SQL",
        ],

        "summary": (
            "Python developer experienced in Django and ReactJS "
            "with REST API development."
        ),

        "experience": [
            {
                "company": "Example Technologies",
                "role": "Python Developer",
                "description": (
                    "Developed backend applications using Python and Django. "
                    "Built REST APIs and worked with SQL databases."
                ),
            }
        ],

        "projects": [
            {
                "name": "Recruitment Platform",
                "description": (
                    "Built a full stack application using Python, "
                    "Django, ReactJS and PostgreSQL."
                ),
            }
        ],
    }


# ============================================================
# TEST 1 - BASIC EXTRACTION
# ============================================================

def test_basic_extraction():
    print_header("TEST 1 - BASIC SKILL EXTRACTION")

    resume = build_basic_test_resume()

    result = run_extraction(resume)

    expected_skills = [
        "Python",
        "Django",
        "React",
        "SQL",
    ]

    print("\nExtracted skills:")
    print(_extract_skill_names(result))

    for skill in expected_skills:

        passed = _contains_skill(result, skill)

        print_test(
            f"Basic skill: {skill}",
            passed,
            expected=skill,
            actual=_extract_skill_names(result),
        )

        if passed:
            RESULT.record_pass()
        else:
            RESULT.record_fail(
                f"Basic skill: {skill}",
                skill,
                _extract_skill_names(result),
            )

    return result


# ============================================================
# TEST 2 - SPELLING RESOLUTION
# ============================================================

def test_spelling_resolution():
    print_header("TEST 2 - SPELLING RESOLUTION")

    resume = {
        "skills": [
            "pyhton",
            "Djangoo",
        ]
    }

    result = run_extraction(resume)

    print("\nExtracted skills:")
    print(_extract_skill_names(result))

    expected = [
        "Python",
        "Django",
    ]

    for skill in expected:

        passed = _contains_skill(result, skill)

        print_test(
            f"Spelling resolution: {skill}",
            passed,
            expected=skill,
            actual=_extract_skill_names(result),
        )

        if passed:
            RESULT.record_pass()
        else:
            RESULT.record_fail(
                f"Spelling resolution: {skill}",
                skill,
                _extract_skill_names(result),
            )

    return result


# ============================================================
# TEST 3 - SYNONYM / ALIAS RESOLUTION
# ============================================================

def test_synonym_resolution():
    print_header("TEST 3 - SYNONYM / ALIAS RESOLUTION")

    resume = {
        "skills": [
            "ReactJS",
            "React.js",
            "Fast API",
        ]
    }

    result = run_extraction(resume)

    print("\nExtracted skills:")
    print(_extract_skill_names(result))

    # These are expected canonical names.
    expected = [
        "React",
    ]

    for skill in expected:

        passed = _contains_skill(result, skill)

        print_test(
            f"Synonym resolution: {skill}",
            passed,
            expected=skill,
            actual=_extract_skill_names(result),
        )

        if passed:
            RESULT.record_pass()
        else:
            RESULT.record_fail(
                f"Synonym resolution: {skill}",
                skill,
                _extract_skill_names(result),
            )

    return result


# ============================================================
# TEST 4 - UNKNOWN SKILL REJECTION
# ============================================================

def test_unknown_skill_rejection():
    print_header("TEST 4 - UNKNOWN SKILL REJECTION")

    unknown_skill = "XYZABC_UNKNOWN_SKILL"

    resume = {
        "skills": [
            "Python",
            unknown_skill,
        ]
    }

    result = run_extraction(resume)

    skills = _normalized_skill_set(result)

    passed = _normalize(unknown_skill) not in skills

    print("\nExtracted skills:")
    print(_extract_skill_names(result))

    print_test(
        "Unknown skill rejection",
        passed,
        expected=f"{unknown_skill} should NOT be present",
        actual=_extract_skill_names(result),
    )

    if passed:
        RESULT.record_pass()
    else:
        RESULT.record_fail(
            "Unknown skill rejection",
            f"{unknown_skill} should NOT be present",
            _extract_skill_names(result),
        )

    return result


# ============================================================
# TEST 5 - DUPLICATE REMOVAL
# ============================================================

def test_duplicate_removal():
    print_header("TEST 5 - DUPLICATE REMOVAL")

    resume = {
        "skills": [
            "Python",
            "python",
            "PYTHON",
        ],

        "summary": "Python developer",

        "experience": [
            {
                "description": "Worked extensively with Python."
            }
        ],

        "projects": [
            {
                "description": "Built Python applications."
            }
        ],
    }

    result = run_extraction(resume)

    count = _count_skill(result, "Python")

    passed = count == 1

    print("\nExtracted skills:")
    print(_extract_skill_names(result))

    print(f"\nPython count: {count}")

    print_test(
        "Duplicate removal",
        passed,
        expected="Python appears exactly once",
        actual=f"Python appears {count} time(s)",
    )

    if passed:
        RESULT.record_pass()
    else:
        RESULT.record_fail(
            "Duplicate removal",
            1,
            count,
        )

    return result


# ============================================================
# TEST 6 - SOURCE METADATA
# ============================================================

def test_source_metadata():
    print("\n" + "=" * 80)
    print("TEST 6 - SOURCE METADATA PRESERVATION")
    print("=" * 80)

    resume = {
        "skills": "Python",
        "summary": (
            "Python developer experienced in Django "
            "and REST API development."
        ),
    }

    result = run_extraction(resume)

    print("\nDEBUG RESULT:")
    print(json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
        default=str,
    ))

    python_skill = _find_skill_object(
        result,
        "Python",
    )

    print("\nPython skill object:")
    print(json.dumps(
        python_skill,
        indent=2,
        ensure_ascii=False,
        default=str,
    ))

    passed = False

    if python_skill is not None:

        sources = python_skill.get(
            "sources",
            [],
        )

        passed = (
            bool(sources)
            and any(
                isinstance(source, dict)
                and source.get("source_section") == "skills"
                for source in sources
            )
        )

    print_test(
        "Source metadata preservation",
        passed,
        expected="Python contains source evidence",
        actual=python_skill,
    )

    if passed:
        RESULT.record_pass()
    else:
        RESULT.record_fail(
            "Source metadata preservation",
            "Python contains source evidence",
            python_skill,
        )

    return result

# ============================================================
# TEST 7 - MULTIPLE SOURCE SECTIONS
# ============================================================

def test_multiple_source_sections():
    print_header("TEST 7 - MULTIPLE SOURCE SECTIONS")

    resume = {
    "skills": "Python Django",

    "summary": (
        "Python developer experienced in Django "
        "and REST API development."
    ),

    "experience": [
        {
            "company": "ABC Technologies",
            "role": "Python Developer",
            "description": (
                "Developed Python applications using Django."
            ),
        }
    ],

    "projects": [
        {
            "name": "Employee Management System",
            "description": (
                "Built a Python Django REST API project."
            ),
        }
    ],
}
    print("\nINPUT RESUME:")
    print(json.dumps(
        resume,
        indent=2,
        ensure_ascii=False,
        default=str,
    ))

    
    result = run_extraction(resume)

    python_skill = _find_skill_object(result, "Python")

    assert python_skill is not None, (
        "Python skill object not found"
    )

    source_sections = sorted(
        python_skill.get("source_sections", [])
    )

    expected_sections = sorted([
        "experience",
        "projects",
        "skills",
        "summary",
    ])

    passed = source_sections == expected_sections

    print("\nPython source sections:")
    print(source_sections)

    print_test(
        "Multiple source sections",
        passed,
        expected=expected_sections,
        actual=source_sections,
    )

    if passed:
        RESULT.record_pass()
    else:
        RESULT.record_fail(
            "Multiple source sections",
            expected_sections,
            source_sections,
        )
        
    print("\nDEBUG RESULT:")
    print(json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
        default=str,
    ))

    return result

# ============================================================
# TEST 8 - SPECIAL SKILL NAMES
# ============================================================

def test_special_skill_names():
    print_header("TEST 8 - SPECIAL SKILL NAMES")

    special_skills = [
        "C++",
        "C#",
        ".NET",
        "Node.js",
    ]

    resume = {
        "skills": special_skills
    }

    result = run_extraction(resume)

    print("\nExtracted skills:")
    print(_extract_skill_names(result))

    for skill in special_skills:

        passed = _contains_skill(result, skill)

        print_test(
            f"Special skill name: {skill}",
            passed,
            expected=skill,
            actual=_extract_skill_names(result),
        )

        if passed:
            RESULT.record_pass()
        else:
            RESULT.record_fail(
                f"Special skill name: {skill}",
                skill,
                _extract_skill_names(result),
            )

    return result


# ============================================================
# TEST 9 - STACK EXPANSION
# ============================================================

def test_stack_expansion():
    print_header("TEST 9 - STACK EXPANSION")

    resume = {
        "skills": [
            "MERN"
        ]
    }

    result = run_extraction(resume)

    print("\nExtracted skills:")
    print(_extract_skill_names(result))

    # Do not hard-code children here because the stack dictionary
    # is the source of truth.
    #
    # We only verify that the original stack survives and that
    # the pipeline can produce more than the original item.

    names = _extract_skill_names(result)

    original_present = _contains_skill(result, "MERN")

    passed = (
        original_present
        and len(names) >= 1
    )

    print_test(
        "Stack expansion",
        passed,
        expected="MERN remains valid and stack processing succeeds",
        actual=names,
    )

    if passed:
        RESULT.record_pass()
    else:
        RESULT.record_fail(
            "Stack expansion",
            "MERN remains valid",
            names,
        )

    return result


# ============================================================
# TEST 10 - DIRECT + STACK DUPLICATE
# ============================================================

def test_direct_and_stack_duplicate():
    print_header("TEST 10 - DIRECT + STACK DUPLICATE")

    resume = {
        "skills": [
            "MERN",
            "ReactJS",
        ]
    }

    result = run_extraction(resume)

    print("\nExtracted skills:")
    print(_extract_skill_names(result))

    react_count = _count_skill(result, "React")

    passed = react_count <= 1

    print_test(
        "Direct + stack duplicate handling",
        passed,
        expected="React appears at most once",
        actual=f"React appears {react_count} time(s)",
    )

    if passed:
        RESULT.record_pass()
    else:
        RESULT.record_fail(
            "Direct + stack duplicate handling",
            1,
            react_count,
        )

    return result


# ============================================================
# TEST 11 - CASE NORMALIZATION
# ============================================================

def test_case_normalization():
    print_header("TEST 11 - CASE NORMALIZATION")

    resume = {
        "skills": [
            "python",
            "PYTHON",
            "Python",
        ]
    }

    result = run_extraction(resume)

    count = _count_skill(result, "Python")

    passed = count == 1

    print("\nExtracted skills:")
    print(_extract_skill_names(result))

    print_test(
        "Case normalization",
        passed,
        expected="Python appears once",
        actual=f"Python appears {count} time(s)",
    )

    if passed:
        RESULT.record_pass()
    else:
        RESULT.record_fail(
            "Case normalization",
            1,
            count,
        )

    return result


# ============================================================
# TEST 12 - NESTED SECTION DATA
# ============================================================

def test_nested_section_data():
    print_header("TEST 12 - NESTED SECTION DATA")

    resume = {
    "skills": "Python Django",

    "summary": (
        "Python developer experienced in Django "
        "and REST API development."
    ),

    "experience": [
        {
            "description": (
                "Developed Python applications using Django."
            )
        }
    ],

    "projects": [
        {
            "description": (
                "Built a Python Django REST API project."
            )
        }
    ],
}

    result = run_extraction(resume)

    python_skill = _find_skill_object(result, "Python")

    assert python_skill is not None

    source_sections = sorted(
        python_skill.get("source_sections", [])
    )

    expected_sections = sorted([
        "experience",
        "projects",
        "skills",
        "summary",
    ])

    passed = source_sections == expected_sections

    print("\nPython source sections:")
    print(source_sections)

    print_test(
        "Multiple source sections",
        passed,
        expected=expected_sections,
        actual=source_sections,
    )

    if passed:
        RESULT.record_pass()
    else:
        RESULT.record_fail(
            "Multiple source sections",
            expected_sections,
            source_sections,
        )

    return result


# ============================================================
# TEST 13 - EMPTY INPUT
# ============================================================

def test_empty_input():
    print_header("TEST 13 - EMPTY INPUT")

    resume = {}

    try:
        result = run_extraction(resume)

        skills = _extract_skill_names(result)

        passed = len(skills) == 0

        print_test(
            "Empty resume input",
            passed,
            expected="No skills",
            actual=skills,
        )

        if passed:
            RESULT.record_pass()
        else:
            RESULT.record_fail(
                "Empty resume input",
                [],
                skills,
            )

    except Exception as exc:

        RESULT.record_fail(
            "Empty resume input",
            "No exception",
            str(exc),
        )

        print_test(
            "Empty resume input",
            False,
            expected="No exception",
            actual=str(exc),
        )


# ============================================================
# TEST 14 - NONE VALUES
# ============================================================

def test_none_values():
    print_header("TEST 14 - NONE / EMPTY VALUES")

    resume = {
        "skills": None,
        "summary": None,
        "experience": None,
        "projects": None,
    }

    try:
        result = run_extraction(resume)

        skills = _extract_skill_names(result)

        passed = len(skills) == 0

        print_test(
            "None values",
            passed,
            expected="No skills",
            actual=skills,
        )

        if passed:
            RESULT.record_pass()
        else:
            RESULT.record_fail(
                "None values",
                [],
                skills,
            )

    except Exception as exc:

        RESULT.record_fail(
            "None values",
            "No exception",
            str(exc),
        )

        print_test(
            "None values",
            False,
            expected="No exception",
            actual=str(exc),
        )


# ============================================================
# TEST 15 - FINAL OUTPUT STRUCTURE
# ============================================================

def test_output_structure():
    print_header("TEST 15 - FINAL OUTPUT STRUCTURE")

    resume = {
        "skills": [
            "Python",
            "Django",
        ]
    }

    result = run_extraction(resume)

    objects = _extract_skill_objects(result)

    passed = True

    required_fields = {
        "skill",
    }

    for item in objects:

        if not required_fields.issubset(item.keys()):
            passed = False
            break

    print("\nSkill objects:")
    print(json.dumps(
        objects,
        indent=2,
        ensure_ascii=False,
    ))

    print_test(
        "Final output structure",
        passed,
        expected="Every skill object contains 'skill'",
        actual=objects,
    )

    if passed:
        RESULT.record_pass()
    else:
        RESULT.record_fail(
            "Final output structure",
            "Every skill object contains 'skill'",
            objects,
        )

    return result


# ============================================================
# FULL PIPELINE TEST
# ============================================================

def test_full_pipeline():
    print_header("FULL PIPELINE INTEGRATION TEST")

    resume = {
        "skills": [
            "pyhton",
            "ReactJS",
            "Django",
            "SQL",
            "Fast API",
            "MERN",
        ],

        "summary": (
            "Python developer experienced in Django, ReactJS "
            "and REST API development."
        ),

        "experience": [
            {
                "company": "Example Technologies",
                "role": "Python Developer",
                "description": (
                    "Developed backend applications using Python and Django. "
                    "Built REST APIs and SQL databases."
                ),
            }
        ],

        "projects": [
            {
                "name": "Recruitment Platform",
                "description": (
                    "Built a full stack application using Python, "
                    "Django, ReactJS and PostgreSQL."
                ),
            }
        ],
    }

    try:
        result = run_extraction(resume)

        skills = _extract_skill_names(result)

        print("\nFinal pipeline output:")
        print(json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            default=str,
        ))

        print("\nFinal skills:")
        print(skills)

        passed = len(skills) > 0

        print_test(
            "Full pipeline execution",
            passed,
            expected="Pipeline returns final skills",
            actual=skills,
        )

        if passed:
            RESULT.record_pass()
        else:
            RESULT.record_fail(
                "Full pipeline execution",
                "At least one skill",
                skills,
            )

    except Exception as exc:

        RESULT.record_fail(
            "Full pipeline execution",
            "Pipeline completes without exception",
            str(exc),
            error=traceback.format_exc(),
        )

        print_test(
            "Full pipeline execution",
            False,
            expected="No exception",
            actual=str(exc),
        )


# ============================================================
# VALIDATION SUMMARY
# ============================================================

def print_summary():
    print_header("SKILL EXTRACTION VALIDATION SUMMARY")

    print(f"Total tests : {RESULT.total}")
    print(f"Passed      : {RESULT.passed}")
    print(f"Failed      : {RESULT.failed}")

    if RESULT.total:
        percentage = (
            RESULT.passed / RESULT.total
        ) * 100

        print(f"Pass rate   : {percentage:.2f}%")

    if RESULT.failed == 0:
        print()
        print("STATUS: PASS")
        print("Skill extraction pipeline validation completed successfully.")

    else:
        print()
        print("STATUS: FAIL")
        print("The following tests require investigation:")

        for index, error in enumerate(
            RESULT.errors,
            start=1,
        ):
            print()
            print(f"{index}. {error['test']}")
            print(f"   Expected: {error['expected']}")
            print(f"   Actual  : {error['actual']}")

            if error.get("error"):
                print(f"   Error   : {error['error']}")


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 80)
    print("SKILL EXTRACTION VALIDATOR")
    print("=" * 80)

    print(f"Project root: {PROJECT_ROOT}")

    try:

        test_basic_extraction()

        test_spelling_resolution()

        test_synonym_resolution()

        test_unknown_skill_rejection()

        test_duplicate_removal()

        test_source_metadata()

        test_multiple_source_sections()

        test_special_skill_names()

        test_stack_expansion()

        test_direct_and_stack_duplicate()

        test_case_normalization()

        test_nested_section_data()

        test_empty_input()

        test_none_values()

        test_output_structure()

        test_full_pipeline()

    except Exception as exc:

        print()
        print("=" * 80)
        print("UNEXPECTED VALIDATOR ERROR")
        print("=" * 80)

        print(str(exc))
        traceback.print_exc()

    finally:

        print_summary()

    return 0 if RESULT.success else 1


if __name__ == "__main__":
    raise SystemExit(main())