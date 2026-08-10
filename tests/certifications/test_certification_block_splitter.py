from document_processing.resume.entity_extracter.certifications.certification_block_splitter import (
    split_certification_blocks,is_certification_start
)


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