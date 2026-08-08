from document_processing.resume.entity_extracter.education.education_pipeline import education_pipeline

def test_full_education_pipeline():

    education = [

        "2012-2016 Bachelor of Engineering (B.E), "
        "P.E.S Institute of Technology, "
        "Bangalore South Campus, India.",

        "Visvesvaraya Technological University, "
        "Belgaum, Karnataka, India.",

        "Computer Science and Engineering",

        "Aggregate Score : 64.2",

        "2011-2012 All India Senior School Certificate Exam, "
        "Kendriya Vidyalaya Kalpetta, Kerala, India.",

        "Central Board of Secondary Education",

        "Marks Obtained - 85.5",

        "2000-2010 All India Secondary School Examination, "
        "Kendriya Vidyalaya Kalpetta, Kerala, India.",

        "Central Board of Secondary Education",

        "Marks Obtained - 9.4 CGPA",
    ]

    result = education_pipeline(education)
    print(result)

    # =====================================================
    # Basic validation
    # =====================================================

    assert isinstance(result, list)
    assert len(result) == 3

    # =====================================================
    # Education 1 - Engineering
    # =====================================================

    engineering = result[0]

    assert engineering["degree_type"] == \
        "Bachelor of Engineering"

    assert engineering["field_of_study"] == \
        "Computer Science"

    assert engineering["graduation_year"] == \
        "2016"

    assert engineering["institution"] is not None

    assert engineering["university"] == \
        "Visvesvaraya Technological University, " \
        "Belgaum, Karnataka, India"

    assert engineering["board"] is None

    # =====================================================
    # Education 2 - Higher Secondary
    # =====================================================

    higher_secondary = result[1]

    assert higher_secondary["degree_type"] == \
        "Higher Secondary"

    assert higher_secondary["field_of_study"] is None

    assert higher_secondary["institution"] == \
        "Kendriya Vidyalaya Kalpetta, Kerala, India"

    assert higher_secondary["university"] is None

    assert higher_secondary["board"] == \
        "Central Board of Secondary Education"

    assert higher_secondary["graduation_year"] == \
        "2012"

    # =====================================================
    # Education 3 - Secondary
    # =====================================================

    secondary = result[2]

    assert secondary["degree_type"] == \
        "Secondary"

    assert secondary["field_of_study"] is None

    assert secondary["institution"] == \
        "Kendriya Vidyalaya Kalpetta, Kerala, India"

    assert secondary["university"] is None

    assert secondary["board"] == \
        "Central Board of Secondary Education"

    assert secondary["graduation_year"] == \
        "2010"

