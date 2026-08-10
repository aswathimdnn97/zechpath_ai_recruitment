from document_processing.resume.entity_extracter.certifications.organization_extractor import (
    extract_issuing_organization,
)


def test_microsoft_organization():

    block = [
        "Microsoft Certified: Azure Developer Associate",
        "Microsoft",
        "Issued: 2024",
    ]

    result = extract_issuing_organization(block)

    assert result == "Microsoft"


def test_aws_organization():

    block = [
        "AWS Certified Developer - Associate",
        "Amazon Web Services",
        "Issued: 2024",
    ]

    result = extract_issuing_organization(block)

    assert result == "Amazon Web Services"


def test_google_cloud_organization():

    block = [
        "Google Cloud Professional Data Engineer",
        "Google Cloud",
        "Issued: 2023",
    ]

    result = extract_issuing_organization(block)

    assert result == "Google Cloud"


def test_coursera_multiple_organizations():

    block = [
        "Machine Learning Specialization",
        "Coursera / Deep Learning.AI (2022)",
    ]

    result = extract_issuing_organization(block)

    assert result == "Coursera / Deep Learning.AI"


def test_tensorflow_organization():

    block = [
        "TensorFlow Developer Certificate",
        "TensorFlow (2022)",
    ]

    result = extract_issuing_organization(block)

    assert result == "TensorFlow"


def test_ibm_organization():

    block = [
        "Python for Data Science",
        "IBM (2021)",
    ]

    result = extract_issuing_organization(block)

    assert result == "IBM"


def test_organization_without_date():

    block = [
        "Microsoft Certified: Azure Fundamentals",
        "Microsoft",
    ]

    result = extract_issuing_organization(block)

    assert result == "Microsoft"


def test_no_organization():

    block = [
        "Google Cloud Professional Data Engineer",
    ]

    result = extract_issuing_organization(block)

    assert result is None


def test_empty_block():

    result = extract_issuing_organization([])

    assert result is None


def test_none_block():

    result = extract_issuing_organization(None)

    assert result is None
