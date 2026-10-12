"""
university_abbreviation_validation.py

Responsibilities
----------------
Validate university abbreviation handling.

Scenarios
---------
1. Full university name.
2. University abbreviation.
3. Dotted abbreviation.
4. Full name + abbreviation.
5. Case variations.
6. Abbreviation with surrounding text.
7. Unknown university fallback.
8. Original university text preservation.
9. Canonical university resolution.
10. KTU must be recognized as university, not institution.
"""

from document_processing.resume.entity_extracter.education.university_extractor import (
    extract_university,
    remove_university_content,
)


# ============================================================
# EXPECTED VALUES
# ============================================================

KTU_CANONICAL = (
    "APJ Abdul Kalam Technological University"
)


# ============================================================
# BASIC KTU ABBREVIATION
# ============================================================

def test_ktu_abbreviation():

    result = extract_university("KTU")

    assert result is not None

    assert result["value"] == "KTU"

    assert (
        result["canonical_name"]
        == KTU_CANONICAL
    )

    assert result["source"] == "dictionary"


# ============================================================
# LOWERCASE KTU
# ============================================================

def test_ktu_lowercase():

    result = extract_university("ktu")

    assert result is not None

    assert (
        result["canonical_name"]
        == KTU_CANONICAL
    )


# ============================================================
# DOTTED KTU
# ============================================================

def test_ktu_dotted():

    result = extract_university("K.T.U.")

    assert result is not None

    assert (
        result["canonical_name"]
        == KTU_CANONICAL
    )


# ============================================================
# FULL UNIVERSITY NAME
# ============================================================

def test_ktu_full_name():

    result = extract_university(
        "APJ Abdul Kalam Technological University"
    )

    assert result is not None

    assert (
        result["canonical_name"]
        == KTU_CANONICAL
    )

    assert result["source"] == "dictionary"


# ============================================================
# FULL NAME + ABBREVIATION
# ============================================================

def test_ktu_full_name_with_abbreviation():

    result = extract_university(
        "APJ Abdul Kalam Technological University (KTU)"
    )

    assert result is not None

    assert (
        result["canonical_name"]
        == KTU_CANONICAL
    )

    assert result["source"] == "dictionary"


# ============================================================
# APJAKTU
# ============================================================

def test_apjaktu():

    result = extract_university("APJAKTU")

    assert result is not None

    assert (
        result["canonical_name"]
        == KTU_CANONICAL
    )


# ============================================================
# ABBREVIATION INSIDE A LINE
# ============================================================

def test_ktu_inside_line():

    text = "B.Tech Computer Science - KTU"

    result = extract_university(text)

    assert result is not None

    assert result["value"] == "KTU"

    assert (
        result["canonical_name"]
        == KTU_CANONICAL
    )


# ============================================================
# ORIGINAL VALUE PRESERVATION
# ============================================================

def test_original_value_preserved():

    result = extract_university("KTU")

    assert result is not None

    # Important:
    # Do NOT replace the original resume value.
    assert result["value"] == "KTU"

    # Canonical value is separate.
    assert (
        result["canonical_name"]
        == KTU_CANONICAL
    )


# ============================================================
# REMOVE UNIVERSITY CONTENT
# ============================================================

def test_remove_ktu_from_line():

    text = "B.Tech Computer Science - KTU"

    result = extract_university(text)

    cleaned = remove_university_content(
        text,
        result
    )

    assert "KTU" not in cleaned.upper()


# ============================================================
# UNKNOWN UNIVERSITY FALLBACK
# ============================================================

def test_unknown_university():

    result = extract_university(
        "XYZ Technological University"
    )

    assert result is not None

    assert (
        result["source"]
        == "pattern"
    )

    assert (
        result["canonical_name"]
        is None
    )


# ============================================================
# NON-UNIVERSITY SHOULD NOT MATCH
# ============================================================

def test_non_university_text():

    result = extract_university(
        "ABC College of Engineering"
    )

    assert result is None


# ============================================================
# VALIDATION RUNNER
# ============================================================

def run_university_abbreviation_validation():

    tests = [

        (
            "KTU abbreviation",
            test_ktu_abbreviation
        ),

        (
            "KTU lowercase",
            test_ktu_lowercase
        ),

        (
            "KTU dotted abbreviation",
            test_ktu_dotted
        ),

        (
            "KTU full name",
            test_ktu_full_name
        ),

        (
            "KTU full name + abbreviation",
            test_ktu_full_name_with_abbreviation
        ),

        (
            "APJAKTU abbreviation",
            test_apjaktu
        ),

        (
            "KTU inside education line",
            test_ktu_inside_line
        ),

        (
            "Original university value preservation",
            test_original_value_preserved
        ),

        (
            "Remove KTU from line",
            test_remove_ktu_from_line
        ),

        (
            "Unknown university fallback",
            test_unknown_university
        ),

        (
            "Non-university text",
            test_non_university_text
        ),
    ]

    print()
    print("=" * 80)
    print("UNIVERSITY ABBREVIATION VALIDATION")
    print("=" * 80)

    passed = 0
    failed = 0

    for name, test_function in tests:

        try:

            test_function()

            print(f"[PASS] {name}")

            passed += 1

        except AssertionError as exc:

            print(f"[FAIL] {name}")

            if str(exc):
                print(f"       {exc}")

            failed += 1

        except Exception as exc:

            print(f"[ERROR] {name}")
            print(f"        {type(exc).__name__}: {exc}")

            failed += 1

    print("-" * 80)
    print(f"Passed : {passed}")
    print(f"Failed : {failed}")
    print("-" * 80)

    if failed == 0:

        print(
            "[SUCCESS] University abbreviation validation passed."
        )

    else:

        print(
            "[FAILED] University abbreviation validation has failures."
        )

    print("=" * 80)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_university_abbreviation_validation()