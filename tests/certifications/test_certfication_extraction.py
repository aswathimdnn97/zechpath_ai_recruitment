"""
test_certification_extraction.py

Tests for certification extraction.

Run:

    pytest -v

or:

    python -m pytest -v
"""

import pytest

from document_processing.resume.entity_extracter.certifications.certification_date_extraction import (
    extract_certification_date,
)
from document_processing.resume.entity_extracter.certifications.creditiel_id_extractor import extract_credential_id



# ============================================================
# DATE EXTRACTION TESTS
# ============================================================


def test_certification_issue_year():
    """
    Microsoft (2024)

    Expected:
        issue_date = 2024
    """

    block = [
        "Microsoft Certified: Azure Developer Associate",
        "Microsoft (2024)",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] == "2024"
    assert result["expiration_date"] is None


def test_certification_issue_year_2023():
    """
    Microsoft (2023)
    """

    block = [
        "Microsoft Certified: Azure AI Fundamentals",
        "Microsoft (2023)",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] == "2023"
    assert result["expiration_date"] is None


def test_certification_without_date():
    """
    Certification with no date.

    Expected:
        issue_date = None
        expiration_date = None
    """

    block = [
        "Google Cloud Professional Data Engineer",
        "Google Cloud",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] is None
    assert result["expiration_date"] is None


def test_certification_issue_year_after_details():
    """
    Year appears after certification details.

    Example:

        AWS Certified Developer
        Amazon Web Services
        2024
    """

    block = [
        "AWS Certified Developer",
        "Amazon Web Services",
        "2024",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] == "2024"


def test_certification_issue_year_before_details():
    """
    Year appears before certification details.

    Example:

        2024
        AWS Certified Developer
        Amazon Web Services
    """

    block = [
        "2024",
        "AWS Certified Developer",
        "Amazon Web Services",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] == "2024"


def test_certification_explicit_issue_date():
    """
    Issued: March 2024
    """

    block = [
        "AWS Certified Developer",
        "Issued: March 2024",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] == "March 2024"


def test_certification_explicit_expiration_date():
    """
    Expires: March 2027
    """

    block = [
        "AWS Certified Developer",
        "Expires: March 2027",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["expiration_date"] == "March 2027"


def test_certification_issue_and_expiration():
    """
    Issued: March 2024
    Expires: March 2027
    """

    block = [
        "AWS Certified Developer",
        "Issued: March 2024",
        "Expires: March 2027",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] == "March 2024"
    assert result["expiration_date"] == "March 2027"


def test_certification_year_range():
    """
    2024 - 2027

    Certification range means:

        issue_date = 2024
        expiration_date = 2027
    """

    block = [
        "AWS Certified Developer",
        "2024 - 2027",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] == "2024"
    assert result["expiration_date"] == "2027"

    assert result["course_start_date"] is None
    assert result["course_end_date"] is None


def test_certification_parenthesized_range():
    """
    Amazon Web Services (2024 - 2027)
    """

    block = [
        "AWS Certified Developer",
        "Amazon Web Services (2024 - 2027)",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] == "2024"
    assert result["expiration_date"] == "2027"

    assert result["course_start_date"] is None
    assert result["course_end_date"] is None


def test_certification_parenthesized_present_range():
    """
    Amazon Web Services (2024 - Present)
    """

    block = [
        "AWS Certified Developer",
        "Amazon Web Services (2024 - Present)",
    ]

    result = extract_certification_date(
        block,
        record_type="certification",
    )

    assert result["issue_date"] == "2024"
    assert result["expiration_date"] == "Present"


# ============================================================
# TRAINING DATE TESTS
# ============================================================


def test_training_date_range():
    """
    Training:

        May 2022 - July 2022

    Must NOT become:

        issue_date
        expiration_date
    """

    block = [
        "Java With SpringBoot",
        "ROGERSOFT Technology Private Limited",
        "May 2022 - July 2022",
    ]

    result = extract_certification_date(
        block,
        record_type="training",
    )

    assert result["course_start_date"] == "May 2022"
    assert result["course_end_date"] == "July 2022"

    assert result["issue_date"] is None
    assert result["expiration_date"] is None


def test_training_present():
    """
    May 2026 - Present
    """

    block = [
        "Python Full-Stack Development",
        "ROGERSOFT Technology Private Limited",
        "May 2026 - Present",
    ]

    result = extract_certification_date(
        block,
        record_type="training",
    )

    assert result["course_start_date"] == "May 2026"
    assert result["course_end_date"] == "Present"

    assert result["issue_date"] is None
    assert result["expiration_date"] is None


# ============================================================
# CREDENTIAL ID TESTS
# ============================================================


def test_no_credential_id():
    """
    Normal certification without credential ID.

    Must return None.
    """

    block = [
        "Microsoft Certified: Azure Developer Associate",
        "Microsoft (2024)",
    ]

    result = extract_credential_id(block)

    assert result is None


def test_no_false_credential_from_certified():
    """
    Important regression test.

    'Certified' must NOT become:

        ified
    """

    block = [
        "Microsoft Certified: Azure Developer Associate",
        "Microsoft (2024)",
    ]

    result = extract_credential_id(block)

    assert result is None


def test_no_false_credential_from_certificate():
    """
    Certificate is a certification title, not an ID.
    """

    block = [
        "TensorFlow Developer Certificate",
        "TensorFlow (2022)",
    ]

    result = extract_credential_id(block)

    assert result is None


def test_credential_id():
    """
    Credential ID: AWS-123456
    """

    block = [
        "AWS Certified Developer",
        "Credential ID: AWS-123456",
    ]

    result = extract_credential_id(block)

    assert result == "AWS-123456"


def test_certification_id():
    """
    Certification ID: AZ-204-123456
    """

    block = [
        "Microsoft Certified Azure Developer",
        "Certification ID: AZ-204-123456",
    ]

    result = extract_credential_id(block)

    assert result == "AZ-204-123456"


def test_certificate_id():
    """
    Certificate ID: CERT-2024-001
    """

    block = [
        "Python for Data Science",
        "Certificate ID: CERT-2024-001",
    ]

    result = extract_credential_id(block)

    assert result == "CERT-2024-001"


def test_credential_number():
    """
    Credential Number: CRED-123456
    """

    block = [
        "AWS Certified Developer",
        "Credential Number: CRED-123456",
    ]

    result = extract_credential_id(block)

    assert result == "CRED-123456"


def test_certificate_number():
    """
    Certificate Number: 123456789
    """

    block = [
        "Data Science Professional",
        "Certificate Number: 123456789",
    ]

    result = extract_credential_id(block)

    assert result == "123456789"


def test_credly_url():
    """
    Credly URL should return the badge identifier.
    """

    block = [
        "AWS Certified Developer",
        "https://www.credly.com/badges/abc123xyz",
    ]

    result = extract_credential_id(block)

    assert result == "abc123xyz"


# ============================================================
# NEGATIVE CREDENTIAL TESTS
# ============================================================


def test_year_is_not_credential_id():
    """
    2024 must not be considered a credential ID.
    """

    block = [
        "AWS Certified Developer",
        "2024",
    ]

    result = extract_credential_id(block)

    assert result is None


def test_date_range_is_not_credential_id():
    """
    2024-2027 must not be credential ID.
    """

    block = [
        "AWS Certified Developer",
        "2024 - 2027",
    ]

    result = extract_credential_id(block)

    assert result is None


def test_empty_block():
    """
    Empty block should return None.
    """

    result = extract_credential_id([])

    assert result is None


def test_none_block():
    """
    None input should return None.
    """

    result = extract_credential_id(None)

    assert result is None


# ============================================================
# COMBINED DATE + CREDENTIAL TEST
# ============================================================


def test_certification_with_all_metadata():
    """
    Full certification block:

        AWS Certified Developer
        Amazon Web Services
        Issued: March 2024
        Expires: March 2027
        Credential ID: AWS-123456
    """

    block = [
        "AWS Certified Developer",
        "Amazon Web Services",
        "Issued: March 2024",
        "Expires: March 2027",
        "Credential ID: AWS-123456",
    ]

    date_result = extract_certification_date(
        block,
        record_type="certification",
    )

    credential_result = extract_credential_id(
        block
    )

    assert date_result["issue_date"] == "March 2024"
    assert date_result["expiration_date"] == "March 2027"

    assert credential_result == "AWS-123456"
