from document_processing.resume.entity_extracter.certifications.creditiel_id_extractor import (
    extract_credential_id,
)


def test_credential_id_with_label():

    block = [
        "Microsoft Certified: Azure Developer Associate",
        "Microsoft",
        "Issued: 2024",
        "Credential ID: AZ-123456",
    ]

    result = extract_credential_id(block)

    assert result == "AZ-123456"


def test_credential_id_without_spaces():

    block = [
        "AWS Certified Developer",
        "Amazon Web Services",
        "Credential ID: AWS123456",
    ]

    result = extract_credential_id(block)

    assert result == "AWS123456"


def test_credential_id_with_credential_number():

    block = [
        "Google Cloud Professional Data Engineer",
        "Google Cloud",
        "Credential Number: GCP-987654",
    ]

    result = extract_credential_id(block)

    assert result == "GCP-987654"


def test_no_credential_id():

    block = [
        "Microsoft Certified: Azure AI Fundamentals",
        "Microsoft",
        "Issued: 2023",
    ]

    result = extract_credential_id(block)

    assert result is None


def test_empty_block():

    result = extract_credential_id([])

    assert result is None


def test_none_block():

    result = extract_credential_id(None)

    assert result is None


def test_credential_id_not_certification_keyword():

    block = [
        "Microsoft Certified: Azure Developer Associate",
        "Microsoft",
        "Issued: 2024",
    ]

    result = extract_credential_id(block)

    assert result is None


def test_multiple_metadata_lines():

    block = [
        "AWS Certified Developer - Associate",
        "Amazon Web Services",
        "Issued: March 2024",
        "Expiration: March 2027",
        "Credential ID: AWS-DEV-12345",
    ]

    result = extract_credential_id(block)

    assert result == "AWS-DEV-12345"
