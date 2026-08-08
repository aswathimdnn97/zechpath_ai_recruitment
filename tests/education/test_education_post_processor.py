from document_processing.resume.entity_extracter.education.education_post_processor import (
    post_process_education,
)


def test_merge_university_with_degree():

    education = [

        {
            "degree_type": "Bachelor of Engineering",
            "field_of_study": None,
            "institution":
                "P.E.S Institute of Technology",
            "university": None,
            "board": None,
            "graduation_year": "2016",
        },

        {
            "degree_type": None,
            "field_of_study": "Computer Science",
            "institution":
                "Visvesvaraya Technological University, Karnataka, India.",
            "university": None,
            "board": None,
            "graduation_year": None,
        },
    ]

    result = post_process_education(
        education
    )

    assert len(result) == 1

    assert result[0]["degree_type"] == \
        "Bachelor of Engineering"

    assert result[0]["field_of_study"] == \
        "Computer Science"

    assert result[0]["university"] == \
        "Visvesvaraya Technological University, Karnataka, India."


def test_board_not_field():

    education = [

        {
            "degree_type": None,
            "field_of_study":
                "Central Board of Secondary Education",
            "institution":
                "Kendriya Vidyalaya Kalpetta, Kerala, India.",
            "university": None,
            "board": None,
            "graduation_year": "2012",
        }

    ]

    result = post_process_education(
        education
    )

    assert result[0]["field_of_study"] is None

    assert result[0]["board"] == \
        "Central Board of Secondary Education"


def test_school_classification():

    education = [

        {
            "degree_type": None,
            "field_of_study": None,
            "institution":
                "All India Senior School Certificate Exam, "
                "Kendriya Vidyalaya Kalpetta, Kerala",
            "university": None,
            "board":
                "Central Board of Secondary Education",
            "graduation_year": "2012",
        }

    ]

    result = post_process_education(
        education
    )

    assert result[0]["degree_type"] == \
        "Higher Secondary"


def test_secondary_classification():

    education = [

        {
            "degree_type": None,
            "field_of_study": None,
            "institution":
                "All India Secondary School Examination, "
                "Kendriya Vidyalaya Kalpetta, Kerala",
            "university": None,
            "board":
                "Central Board of Secondary Education",
            "graduation_year": "2010",
        }

    ]

    result = post_process_education(
        education
    )

    assert result[0]["degree_type"] == \
        "Secondary"