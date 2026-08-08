from document_processing.resume.entity_extracter.education.institution_extractor import (
    extract_institution,
)


def test_extract_college():

    block = [
        "2012-2016 Bachelor of Engineering (B.E)",
        "P.E.S Institute of Technology, Bangalore South Campus, India.",
    ]

    result = extract_institution(block)

    assert result is not None
    assert "P.E.S Institute of Technology" in result


def test_extract_school():

    block = [
        "2011-2012 All India Senior School Certificate Exam",
        "Kendriya Vidyalaya Kalpetta, Kerala, India.",
    ]

    result = extract_institution(block)

    assert result is not None
    assert "Kendriya Vidyalaya Kalpetta" in result


def test_no_institution():

    block = [
        "Bachelor of Engineering",
        "Computer Science",
    ]

    result = extract_institution(block)

    assert result is None