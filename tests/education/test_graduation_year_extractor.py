from document_processing.resume.entity_extracter.education.graduation_year_extractor import (
    extract_graduation_year,
)


def test_extract_end_year():

    block = [
        "2012-2016 Bachelor of Engineering",
        "PES Institute of Technology",
    ]

    result = extract_graduation_year(block)

    assert result == "2016"


def test_extract_school_year():

    block = [
        "2011-2012 All India Senior School Certificate Exam",
        "Kendriya Vidyalaya Kalpetta",
    ]

    result = extract_graduation_year(block)

    assert result == "2012"


def test_extract_single_year():

    block = [
        "Bachelor of Engineering",
        "Graduated 2016",
    ]

    result = extract_graduation_year(block)

    assert result == "2016"


def test_present_degree():

    block = [
        "Master of Computer Applications",
        "September 2022 - Present",
    ]

    result = extract_graduation_year(block)

    assert result == "2022"