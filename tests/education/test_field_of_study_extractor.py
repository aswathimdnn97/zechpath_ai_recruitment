from document_processing.resume.entity_extracter.education.field_of_study_extractor import (
    extract_field_of_study,
)


def test_extract_computer_science():

    block = [
        "Bachelor of Engineering",
        "PES Institute of Technology",
        "Computer Science and Engineering",
        "2012-2016",
    ]

    result = extract_field_of_study(block)

    assert result is not None
    assert "Computer Science" in result


def test_extract_computer_application():

    block = [
        "Bachelor of Computer Applications",
        "Computer Applications",
        "SGN Khalsa PG College",
    ]

    result = extract_field_of_study(block)

    assert result is not None


def test_no_field():

    block = [
        "Bachelor of Engineering",
        "PES Institute of Technology",
        "2012-2016",
    ]

    result = extract_field_of_study(block)

    assert result is None