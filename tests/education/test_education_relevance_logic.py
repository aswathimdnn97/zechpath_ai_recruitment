from document_processing.resume.entity_extracter.education.education_relevence_logic import (
    filter_education_blocks,
)


def test_keep_degree_block():

    blocks = [
        [
            "Bachelor of Engineering",
            "PES Institute of Technology",
            "2012 - 2016",
        ]
    ]

    result = filter_education_blocks(blocks)

    assert len(result) == 1
    assert result[0] == blocks[0]


def test_keep_school_block():

    blocks = [
        [
            "All India Senior School Certificate Exam",
            "Kendriya Vidyalaya",
            "2011 - 2012",
        ]
    ]

    result = filter_education_blocks(blocks)

    assert len(result) == 1
    assert result[0] == blocks[0]


def test_remove_irrelevant_block():

    blocks = [
        [
            "Python Developer",
            "5 years experience",
        ]
    ]

    result = filter_education_blocks(blocks)

    assert len(result) == 0


def test_mixed_education_blocks():

    blocks = [
        [
            "Bachelor of Engineering",
            "PES Institute of Technology",
            "2012 - 2016",
        ],
        [
            "Python Developer",
            "5 years experience",
        ],
        [
            "All India Senior School Certificate Exam",
            "Kendriya Vidyalaya",
            "2011 - 2012",
        ],
    ]

    result = filter_education_blocks(blocks)

    assert len(result) == 2

    assert result[0] == blocks[0]
    assert result[1] == blocks[2]


def test_empty_blocks():

    result = filter_education_blocks([])

    assert result == []
