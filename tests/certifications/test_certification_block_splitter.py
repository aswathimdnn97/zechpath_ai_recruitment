from document_processing.resume.entity_extracter.certifications.certification_block_splitter import (
    split_certification_blocks,is_certification_start,
    split_certification_blocks,
        is_document_noise,
)

import pytest




def test_rejects_resume_evaluation_title():
    line = (
        "ZechPath ATS evaluation resume - RES_EVAL_002 - "
        "Fictional test data for eligibility API validation"
    )

    assert is_document_noise(line) is True

    result = split_certification_blocks([line])

    assert result == []


def test_preserves_valid_certification_blocks():
    section = [
        "AWS Certified Solutions Architect - Associate",
        "Amazon Web Services",
        "Issued: March 2024",
        "Credential ID: AWS123",
        "Microsoft Certified: Azure Fundamentals",
        "Microsoft",
        "Issued: 2023",
    ]

    result = split_certification_blocks(section)

    assert len(result) == 2

    assert result[0][0] == (
        "AWS Certified Solutions Architect - Associate"
    )

    assert result[1][0] == (
        "Microsoft Certified: Azure Fundamentals"
    )


@pytest.mark.parametrize(
    "name",
    [
        "Python Programming Fundamentals",
        "Backend API Development and Testing",
        "Python / Domain Certification",
        "Professional Development Program",
    ],
)
def test_preserves_legitimate_certification_names(name):
    result = split_certification_blocks([name])

    assert result == [[name]]


def test_removes_noise_without_removing_valid_certifications():
    section = [
        "Python Programming Fundamentals",
        (
            "ZechPath ATS evaluation resume - RES_EVAL_002 - "
            "Fictional test data for eligibility API validation"
        ),
        "Backend API Development and Testing",
    ]

    result = split_certification_blocks(section)

    assert result == [
        ["Python Programming Fundamentals"],
        ["Backend API Development and Testing"],
    ]

def test_split_multiple_certifications():

    section = [
        "AWS Certified Solutions Architect - Associate",
        "Amazon Web Services",
        "Issued: March 2024",
        "Credential ID: AWS123",
        "Microsoft Certified: Azure Fundamentals",
        "Microsoft",
        "Issued: 2023",
    ]

    result = split_certification_blocks(
        section
    )

    assert len(result) == 2


def test_first_certification_block():

    section = [
        "AWS Certified Solutions Architect - Associate",
        "Amazon Web Services",
        "Issued: March 2024",
        "Credential ID: AWS123",
        "Microsoft Certified: Azure Fundamentals",
    ]

    print("\nINPUT:")
    print(section)

    result = split_certification_blocks(section)

    print("\nRESULT:")
    print(result)

    assert len(result) == 2
    assert result[0] == [
        "AWS Certified Solutions Architect - Associate",
        "Amazon Web Services",
        "Issued: March 2024",
        "Credential ID: AWS123",
    ]
    assert result[1] == [
        "Microsoft Certified: Azure Fundamentals",
    ]
    
    
def test_single_certification():

    section = [
        "AWS Certified Developer - Associate",
        "Amazon Web Services",
        "2024",
    ]

    result = split_certification_blocks(
        section
    )

    assert len(result) == 1


def test_empty_section():

    result = split_certification_blocks([])

    assert result == []


def test_raw_text_input():

    section = """
    AWS Certified Solutions Architect - Associate
    Amazon Web Services
    Issued: 2024

    Microsoft Certified: Azure Fundamentals
    Microsoft
    Issued: 2023
    """

    result = split_certification_blocks(
        section
    )

    assert len(result) == 2
    
def test_certification_start_detection():

    assert is_certification_start(
        "AWS Certified Solutions Architect - Associate"
    ) is True

    assert is_certification_start(
        "Microsoft Certified: Azure Fundamentals"
    ) is True

    assert is_certification_start(
        "Issued: March 2024"
    ) is False

    assert is_certification_start(
        "Credential ID: AWS123"
    ) is False