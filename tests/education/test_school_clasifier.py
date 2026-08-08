from document_processing.resume.entity_extracter.education.school_degree_classifier import classify_school_degree

def test_classify_higher_secondary():
    block = [
        "2011-2012 All India Senior School Certificate Exam",
        "Kendriya Vidyalaya Kalpetta",
        "Central Board of Secondary Education",
    ]

    assert classify_school_degree(block) == "Higher Secondary"


def test_classify_secondary():
    block = [
        "2000-2010 All India Secondary School Examination",
        "Kendriya Vidyalaya Kalpetta",
        "Central Board of Secondary Education",
    ]

    assert classify_school_degree(block) == "Secondary"


def test_not_school_degree():
    block = [
        "Bachelor of Engineering",
        "PES Institute of Technology",
    ]

    assert classify_school_degree(block) is None