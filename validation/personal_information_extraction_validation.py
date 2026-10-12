"""
Personal Information Extraction Validation
-------------------------------------------

Validates the complete personal-information extraction pipeline.

Fields:
    - name
    - email
    - phone
    - location
    - linkedin
    - github
    - portfolio
"""

from document_processing.resume.entity_extracter.personal_information.personal_information_extractor import (
    extract_personal_information,
)


# ============================================================
# TEST RUNNER
# ============================================================

TOTAL = 0
PASSED = 0
FAILED = 0


def run_test(test_name, text, expected):
    global TOTAL, PASSED, FAILED

    TOTAL += 1

    try:
        result = extract_personal_information(text)

        success = True
        failures = []

        for field, expected_value in expected.items():
            actual_value = result.get(field)

            if expected_value is None:
                if actual_value is not None:
                    success = False
                    failures.append(
                        f"{field}: expected None, got {actual_value!r}"
                    )
            else:
                if actual_value != expected_value:
                    success = False
                    failures.append(
                        f"{field}: expected {expected_value!r}, "
                        f"got {actual_value!r}"
                    )

        if success:
            PASSED += 1
            print(f"[PASS] {test_name}")
        else:
            FAILED += 1
            print(f"[FAIL] {test_name}")

            for failure in failures:
                print(f"       {failure}")

            print(f"       RESULT: {result}")

    except Exception as exc:
        FAILED += 1
        print(f"[FAIL] {test_name}")
        print(f"       Exception: {type(exc).__name__}: {exc}")


# ============================================================
# 1. COMPLETE STANDARD PROFILE
# ============================================================

run_test(
    "Complete standard profile",
    """
    John Doe
    john.doe@gmail.com
    +91 98765 43210
    Kozhikode, Kerala, India
    https://linkedin.com/in/johndoe
    https://github.com/johndoe
    https://johndoe.dev
    """,
    {
        "name": "John Doe",
        "email": "john.doe@gmail.com",
        "phone": "+91 98765 43210",
        "location": "Kozhikode, Kerala, India",
        "linkedin": "https://linkedin.com/in/johndoe",
        "github": "https://github.com/johndoe",
        "portfolio": "https://johndoe.dev",
    },
)


# ============================================================
# 2. NAME EXTRACTION
# ============================================================

run_test(
    "Name extraction - two words",
    """
    John Doe
    Software Engineer
    john@example.com
    """,
    {
        "name": "John Doe",
    },
)


run_test(
    "Name extraction - three words",
    """
    John Michael Doe
    Python Developer
    john@example.com
    """,
    {
        "name": "John Michael Doe",
    },
)


run_test(
    "Name extraction - four words",
    """
    John Michael Thomas Doe
    Software Engineer
    """,
    {
        "name": "John Michael Thomas Doe",
    },
)


run_test(
    "Name should not be email",
    """
    john.doe@gmail.com
    Python Developer
    """,
    {
        "name": None,
    },
)


run_test(
    "Name should not be phone",
    """
    +91 98765 43210
    Python Developer
    """,
    {
        "name": None,
    },
)


# ============================================================
# 3. EMAIL
# ============================================================

run_test(
    "Standard email",
    """
    John Doe
    john@example.com
    """,
    {
        "email": "john@example.com",
    },
)


run_test(
    "Email with dot",
    """
    John Doe
    john.doe@example.com
    """,
    {
        "email": "john.doe@example.com",
    },
)


run_test(
    "Email with underscore",
    """
    John Doe
    john_doe@example.co.in
    """,
    {
        "email": "john_doe@example.co.in",
    },
)


run_test(
    "Email with plus",
    """
    John Doe
    john-doe+work@example.org
    """,
    {
        "email": "john-doe+work@example.org",
    },
)


run_test(
    "Email punctuation cleanup",
    """
    John Doe
    john@example.com.
    """,
    {
        "email": "john@example.com",
    },
)


# ============================================================
# 4. PHONE
# ============================================================

run_test(
    "Indian phone - plain",
    """
    John Doe
    9876543210
    """,
    {
        "phone": "9876543210",
    },
)


run_test(
    "Indian phone - space separated",
    """
    John Doe
    98765 43210
    """,
    {
        "phone": "98765 43210",
    },
)


run_test(
    "Indian phone - hyphen separated",
    """
    John Doe
    98765-43210
    """,
    {
        "phone": "98765-43210",
    },
)


run_test(
    "Indian phone - country code",
    """
    John Doe
    +91 98765 43210
    """,
    {
        "phone": "+91 98765 43210",
    },
)


run_test(
    "Indian phone - country code hyphen",
    """
    John Doe
    +91-98765-43210
    """,
    {
        "phone": "+91-98765-43210",
    },
)


# ============================================================
# 5. LOCATION
# ============================================================

run_test(
    "Location - city state country",
    """
    John Doe
    Kozhikode, Kerala, India
    """,
    {
        "location": "Kozhikode, Kerala, India",
    },
)


run_test(
    "Location - city state",
    """
    John Doe
    Bengaluru, Karnataka
    """,
    {
        "location": "Bengaluru, Karnataka",
    },
)


run_test(
    "Location - known Kerala location",
    """
    John Doe
    Kochi, Kerala
    """,
    {
        "location": "Kochi, Kerala",
    },
)


run_test(
    "Location should not be LinkedIn",
    """
    John Doe
    linkedin.com/in/johndoe
    """,
    {
        "location": None,
    },
)


run_test(
    "Location should not be GitHub",
    """
    John Doe
    github.com/johndoe
    """,
    {
        "location": None,
    },
)


# ============================================================
# 6. LINKEDIN
# ============================================================

run_test(
    "LinkedIn full URL",
    """
    John Doe
    https://www.linkedin.com/in/johndoe
    """,
    {
        "linkedin": "https://www.linkedin.com/in/johndoe",
    },
)


run_test(
    "LinkedIn without protocol",
    """
    John Doe
    linkedin.com/in/johndoe
    """,
    {
        "linkedin": "linkedin.com/in/johndoe",
    },
)


# ============================================================
# 7. GITHUB
# ============================================================

run_test(
    "GitHub full URL",
    """
    John Doe
    https://www.github.com/johndoe
    """,
    {
        "github": "https://www.github.com/johndoe",
    },
)


run_test(
    "GitHub without protocol",
    """
    John Doe
    github.com/johndoe
    """,
    {
        "github": "github.com/johndoe",
    },
)


# ============================================================
# 8. PORTFOLIO
# ============================================================

run_test(
    "Portfolio URL",
    """
    John Doe
    https://johndoe.dev
    """,
    {
        "portfolio": "https://johndoe.dev",
    },
)


run_test(
    "Portfolio should skip GitHub",
    """
    John Doe
    https://github.com/johndoe
    https://johndoe.dev
    """,
    {
        "portfolio": "https://johndoe.dev",
    },
)


run_test(
    "Portfolio should skip LinkedIn",
    """
    John Doe
    https://linkedin.com/in/johndoe
    https://johndoe.dev
    """,
    {
        "portfolio": "https://johndoe.dev",
    },
)


# ============================================================
# 9. MULTIPLE CONTACT DETAILS
# ============================================================

run_test(
    "Complete contact header",
    """
    Jane Mary Doe
    jane.doe@example.co.in | +91 98765 43210
    Kozhikode, Kerala, India
    linkedin.com/in/janedoe | github.com/janedoe
    https://janedoe.dev
    """,
    {
        "name": "Jane Mary Doe",
        "email": "jane.doe@example.co.in",
        "phone": "+91 98765 43210",
        "location": "Kozhikode, Kerala, India",
        "linkedin": "linkedin.com/in/janedoe",
        "github": "github.com/janedoe",
        "portfolio": "https://janedoe.dev",
    },
)


# ============================================================
# 10. MISSING OPTIONAL FIELDS
# ============================================================

run_test(
    "Name and email only",
    """
    John Doe
    john@example.com
    """,
    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": None,
        "location": None,
        "linkedin": None,
        "github": None,
        "portfolio": None,
    },
)


# ============================================================
# 11. EMPTY INPUT
# ============================================================

run_test(
    "Empty input",
    "",
    {
        "name": None,
        "email": None,
        "phone": None,
        "location": None,
        "linkedin": None,
        "github": None,
        "portfolio": None,
    },
)


# ============================================================
# 12. NONE INPUT
# ============================================================

run_test(
    "None input",
    None,
    {
        "name": None,
        "email": None,
        "phone": None,
        "location": None,
        "linkedin": None,
        "github": None,
        "portfolio": None,
    },
)


# ============================================================
# 13. FALSE POSITIVE PROTECTION
# ============================================================

run_test(
    "Job title should not become name",
    """
    Software Engineer
    john@example.com
    """,
    {
        "name": None,
    },
)


run_test(
    "Section heading should not become name",
    """
    PROFESSIONAL SUMMARY
    Python Developer
    john@example.com
    """,
    {
        "name": None,
    },
)


run_test(
    "Skills should not become name",
    """
    Python Django React
    john@example.com
    """,
    {
        "name": None,
    },
)


# ============================================================
# FINAL REPORT
# ============================================================

print()
print("=" * 70)
print("PERSONAL INFORMATION EXTRACTION VALIDATION")
print("=" * 70)
print(f"Total tests : {TOTAL}")
print(f"Passed      : {PASSED}")
print(f"Failed      : {FAILED}")

if TOTAL:
    pass_rate = (PASSED / TOTAL) * 100
else:
    pass_rate = 0.0

print(f"Pass rate   : {pass_rate:.2f}%")
print("-" * 70)

if FAILED == 0:
    print("STATUS      : PASS")
else:
    print("STATUS      : FAIL")

print("=" * 70)