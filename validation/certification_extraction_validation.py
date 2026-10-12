"""
certification_extraction_validation.py

End-to-end validation for certification extraction.

Validates:
    1. Single certification
    2. Multiple certifications
    3. Certification + organization
    4. Certification + issue date
    5. Certification + expiration date
    6. Certification + credential ID
    7. Date ranges
    8. Parenthesized dates
    9. Credly credential IDs
    10. Unknown certification names
    11. Status/completion handling
    12. Organization inference
    13. Metadata exclusion
    14. Training/certification separation
    15. Empty/invalid input
    16. Duplicate certification blocks
"""

from document_processing.resume.entity_extracter.certifications.certification_pipeline import (
    certification_pipeline,
)


# ============================================================
# TEST HELPERS
# ============================================================

passed = 0
failed = 0


def check(test_name, actual, expected):
    global passed, failed

    if actual == expected:
        print(f"[PASS] {test_name}")
        passed += 1
    else:
        print(f"[FAIL] {test_name}")
        print(f"       Expected: {expected}")
        print(f"       Actual  : {actual}")
        failed += 1


def run_pipeline(lines):
    try:
        return certification_pipeline(lines)
    except Exception as exc:
        print(f"[ERROR] Pipeline crashed: {exc}")
        return None


def first(result):
    if isinstance(result, list) and result:
        return result[0]
    return None


# ============================================================
# 1. BASIC CERTIFICATION
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
])

item = first(result)

check(
    "Basic certification extraction",
    item["certification_name"] if item else None,
    "AWS Certified Developer",
)


# ============================================================
# 2. CERTIFICATION + ORGANIZATION
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "Amazon Web Services",
])

item = first(result)

check(
    "Certification organization extraction",
    item["issuing_organization"] if item else None,
    "Amazon Web Services",
)


# ============================================================
# 3. CERTIFICATION + ISSUE DATE
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "Issued: March 2024",
])

item = first(result)

check(
    "Explicit issue date",
    item["issue_date"] if item else None,
    "March 2024",
)


# ============================================================
# 4. CERTIFICATION + EXPIRATION DATE
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "Issued: March 2024",
    "Expires: March 2027",
])

item = first(result)

check(
    "Explicit expiration date",
    item["expiration_date"] if item else None,
    "March 2027",
)


# ============================================================
# 5. CREDENTIAL ID
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "Credential ID: AWS-123456",
])

item = first(result)

check(
    "Credential ID extraction",
    item["credential_id"] if item else None,
    "AWS-123456",
)


# ============================================================
# 6. CERTIFICATION ID
# ============================================================

result = run_pipeline([
    "Microsoft Certified Azure Developer",
    "Certification ID: AZ-204-123456",
])

item = first(result)

check(
    "Certification ID extraction",
    item["credential_id"] if item else None,
    "AZ-204-123456",
)


# ============================================================
# 7. CERTIFICATE NUMBER
# ============================================================

result = run_pipeline([
    "Data Science Professional",
    "Certificate Number: 123456789",
])

item = first(result)

check(
    "Certificate number extraction",
    item["credential_id"] if item else None,
    "123456789",
)


# ============================================================
# 8. CREDLY URL
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "https://www.credly.com/badges/abc123xyz",
])

item = first(result)

check(
    "Credly credential extraction",
    item["credential_id"] if item else None,
    "abc123xyz",
)


# ============================================================
# 9. PARENTHESIZED SINGLE DATE
# ============================================================

result = run_pipeline([
    "Microsoft Certified: Azure Developer Associate",
    "Microsoft (2024)",
])

item = first(result)

check(
    "Parenthesized issue year",
    item["issue_date"] if item else None,
    "2024",
)

check(
    "Parenthesized organization",
    item["issuing_organization"] if item else None,
    "Microsoft",
)


# ============================================================
# 10. DATE RANGE
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "2024 - 2027",
])

item = first(result)

check(
    "Certification date-range issue date",
    item["issue_date"] if item else None,
    "2024",
)

check(
    "Certification date-range expiration date",
    item["expiration_date"] if item else None,
    "2027",
)


# ============================================================
# 11. PRESENT DATE RANGE
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "Amazon Web Services (2024 - Present)",
])

item = first(result)

check(
    "Present validity range issue date",
    item["issue_date"] if item else None,
    "2024",
)

check(
    "Present validity range expiration date",
    item["expiration_date"] if item else None,
    "Present",
)


# ============================================================
# 12. MULTIPLE CERTIFICATIONS
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "Amazon Web Services",
    "Issued: March 2024",
    "Microsoft Certified: Azure Fundamentals",
    "Microsoft",
    "Issued: 2023",
])

check(
    "Multiple certification count",
    len(result) if result is not None else None,
    2,
)


if result and len(result) >= 2:

    check(
        "First certification name",
        result[0]["certification_name"],
        "AWS Certified Developer",
    )

    check(
        "Second certification name",
        result[1]["certification_name"],
        "Microsoft Certified: Azure Fundamentals",
    )

    check(
        "First certification organization",
        result[0]["issuing_organization"],
        "Amazon Web Services",
    )

    check(
        "Second certification organization",
        result[1]["issuing_organization"],
        "Microsoft",
    )


# ============================================================
# 13. STATUS SHOULD NOT BECOME ORGANIZATION
# ============================================================

result = run_pipeline([
    "Professional Development Program",
    "Completed",
])

item = first(result)

check(
    "Completion status not organization",
    item["issuing_organization"] if item else None,
    None,
)


# ============================================================
# 14. STATUS SHOULD NOT BECOME CERTIFICATION NAME
# ============================================================

result = run_pipeline([
    "Python Certification Completed",
])

item = first(result)

check(
    "Status removed from certification name",
    item["certification_name"] if item else None,
    "Python Certification",
)


# ============================================================
# 15. CERTIFICATE WRAPPER
# ============================================================

result = run_pipeline([
    "Certificate: Python Basics",
])

item = first(result)

check(
    "Certificate wrapper removal",
    item["certification_name"] if item else None,
    "Python Basics",
)


# ============================================================
# 16. CERTIFICATION WITH SLASH
# ============================================================

result = run_pipeline([
    "Python / Domain Certification",
    "Completed",
])

item = first(result)

check(
    "Slash preserved in certification name",
    item["certification_name"] if item else None,
    "Python / Domain Certification",
)


# ============================================================
# 17. ORGANIZATION SUFFIX
# ============================================================

result = run_pipeline([
    "Python for Everybody - Coursera",
])

item = first(result)

check(
    "Organization suffix removed from name",
    item["certification_name"] if item else None,
    "Python for Everybody",
)


# ============================================================
# 18. ORGANIZATION INFERENCE
# ============================================================

result = run_pipeline([
    "AWS Certified Solutions Architect",
])

item = first(result)

check(
    "AWS organization inference",
    item["issuing_organization"] if item else None,
    "Amazon Web Services",
)


# ============================================================
# 19. MICROSOFT ORGANIZATION INFERENCE
# ============================================================

result = run_pipeline([
    "Microsoft Certified: Azure AI Fundamentals",
])

item = first(result)

check(
    "Microsoft organization inference",
    item["issuing_organization"] if item else None,
    "Microsoft",
)


# ============================================================
# 20. GOOGLE CLOUD ORGANIZATION INFERENCE
# ============================================================

result = run_pipeline([
    "Google Cloud Professional Data Engineer",
])

item = first(result)

check(
    "Google Cloud organization inference",
    item["issuing_organization"] if item else None,
    "Google Cloud",
)


# ============================================================
# 21. UNKNOWN CERTIFICATION
# ============================================================

result = run_pipeline([
    "Advanced Enterprise Python Architecture",
])

item = first(result)

check(
    "Unknown certification preserved",
    item["certification_name"] if item else None,
    "Advanced Enterprise Python Architecture",
)


# ============================================================
# 22. YEAR MUST NOT BECOME NAME
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "2024",
])

item = first(result)

check(
    "Year excluded from certification name",
    item["certification_name"] if item else None,
    "AWS Certified Developer",
)

check(
    "Standalone year extracted",
    item["issue_date"] if item else None,
    "2024",
)


# ============================================================
# 23. CREDENTIAL ID MUST NOT BECOME NAME
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "Credential ID: AWS123456",
])

item = first(result)

check(
    "Credential ID excluded from certification name",
    item["certification_name"] if item else None,
    "AWS Certified Developer",
)


# ============================================================
# 24. EXPIRATION YEAR MUST NOT BECOME ISSUE DATE
# ============================================================

result = run_pipeline([
    "AWS Certified Developer",
    "Expires: 2027",
])

item = first(result)

check(
    "Expiration date extraction",
    item["expiration_date"] if item else None,
    "2027",
)

check(
    "Expiration year not used as issue date",
    item["issue_date"] if item else None,
    None,
)


# ============================================================
# 25. EMPTY INPUT
# ============================================================

result = run_pipeline([])

check(
    "Empty input",
    result,
    [],
)


# ============================================================
# 26. NONE INPUT
# ============================================================

result = run_pipeline(None)

check(
    "None input",
    result,
    [],
)


# ============================================================
# 27. MULTIPLE REALISTIC CERTIFICATIONS
# ============================================================

result = run_pipeline([
    "Microsoft Certified: Azure Developer Associate",
    "Microsoft (2024)",
    "AWS Certified Developer",
    "Amazon Web Services",
    "Issued: March 2023",
    "Google Cloud Professional Data Engineer",
    "Google Cloud (2022)",
])

check(
    "Realistic multi-certification count",
    len(result) if result is not None else None,
    3,
)


# ============================================================
# FINAL REPORT
# ============================================================

total = passed + failed

print()
print("=" * 70)
print("CERTIFICATION EXTRACTION VALIDATION")
print("=" * 70)

print(f"Total tests : {total}")
print(f"Passed      : {passed}")
print(f"Failed      : {failed}")

if total:
    print(
        f"Pass rate   : {(passed / total) * 100:.2f}%"
    )

print("-" * 70)

if failed == 0:
    print("STATUS      : PASS")
else:
    print("STATUS      : FAIL")

print("=" * 70)