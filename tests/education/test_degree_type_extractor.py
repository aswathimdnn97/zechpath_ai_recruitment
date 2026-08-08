from document_processing.resume.entity_extracter.education.degree_type_extractor import (
    extract_degree_type,
)


def test_extract_bachelor_of_engineering():

    block = [
        "2012-2016 Bachelor of Engineering (B.E)",
        "P.E.S Institute of Technology",
    ]

    result = extract_degree_type(block)

    assert result == "Bachelor of Engineering"


def test_extract_mca():

    block = [
        "Master of Computer Applications (MCA)",
        "University of Kerala",
    ]

    result = extract_degree_type(block)

    assert result == "Master of Computer Applications"


def test_no_degree():

    block = [
        "PES Institute of Technology",
        "Computer Science",
    ]

    result = extract_degree_type(block)

    assert result is None