
from document_processing.resume.entity_extracter.education.education_block_splitter import (
    split_education_blocks,
)


def test_split_degree_records():

    education = [
        "2012-2016 Bachelor of Engineering (B.E), "
        "P.E.S Institute of Technology, Bangalore South Campus, India.",
        "Visvesvaraya Technological University, "
        "Belgaum, Karnataka, India.",
        "Computer Science and Engineering",
        "Aggregate Score : 64.2",

        "2020-2022 Master of Computer Applications (MCA)",
        "University of Kerala",
    ]

    result = split_education_blocks(education)

    print("\nACTUAL BLOCKS:")
    for i, block in enumerate(result, 1):
        print(f"\nBlock {i}:")
        for line in block:
            print(repr(line))

    assert len(result) == 2


def test_split_school_records():

    education = [
        "2011-2012 All India Senior School Certificate Exam, "
        "Kendriya Vidyalaya Kalpetta, Kerala, India.",
        "Central Board of Secondary Education",
        "Marks Obtained - 85.5",

        "2000-2010 All India Secondary School Examination, "
        "Kendriya Vidyalaya Kalpetta, Kerala, India.",
        "Central Board of Secondary Education",
        "Marks Obtained - 9.4 CGPA",
    ]

    result = split_education_blocks(education)

    assert len(result) == 2

    assert any(
        "Senior School Certificate" in line
        for line in result[0]
    )

    assert any(
        "Secondary School Examination" in line
        for line in result[1]
    )


def test_empty_section():

    result = split_education_blocks([])

    assert result == []


def test_nested_education_section():

    education = [
        [
            "2012-2016 Bachelor of Engineering (B.E), "
            "P.E.S Institute of Technology",
            "Visvesvaraya Technological University",
            "Computer Science and Engineering",
        ]
    ]

    result = split_education_blocks(education)

    assert len(result) == 1

    assert len(result[0]) == 3 or len(result[0]) == 4

    assert any(
        "Bachelor of Engineering" in line
        for line in result[0]
    )

    assert any(
        "Visvesvaraya Technological University" in line
        for line in result[0]
    )

