
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


def test_merge_education_block_with_institution_followed_by_qualification():

    education = [
        "Shri Khushal Das University Hanumangarh, Rajasthan",
        "Master of Computer Applications(MCA) (Semester 1st SGPA/ of 6.93) September 2022 - Present",
        "SGN Khalsa PG College Sri Ganganagar, Rajasthan",
        "Bachelors’s in Computer Application(BCA) (CGPA/ of 70.66 ) September 2021",
        "Jain Pvt. Industrial Training Institute Gumjal, Punjab",
        "Computer Operator and Programming Assistant(COPA) (CGPA/ of 85.75 ) July 2017",
        "BHOPALWALA A SR SS Sri Ganganagar, Rajasthan",
        "Agriculture (Intermediate(XII) (CGPA/ of 55.80 ) July 2014",
    ]

    result = split_education_blocks(education)

    assert len(result) == 4
    assert result[0][0] == "Shri Khushal Das University Hanumangarh, Rajasthan"
    assert result[0][1].startswith("Master of Computer Applications")
    assert result[1][0] == "SGN Khalsa PG College Sri Ganganagar, Rajasthan"
    assert result[1][1].startswith("Bachelors’s in Computer Application")
    assert result[2][0] == "Jain Pvt. Industrial Training Institute Gumjal, Punjab"
    assert result[2][1].startswith("Computer Operator and Programming Assistant(COPA)")
    assert result[3][0] == "BHOPALWALA A SR SS Sri Ganganagar, Rajasthan"
    assert result[3][1].startswith("Agriculture (Intermediate(XII)")

