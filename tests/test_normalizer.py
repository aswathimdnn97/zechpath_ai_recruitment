from document_processing.resume.resume_normalizer import normalize_text

def test_norrmalizer():
    
    text="""Aswathi Madanan
    Technical Skills
    * Python
    
    * Numpy
    * Java
    """
    
    normalized_text=normalize_text(text)
    print(normalized_text)
    assert "skill" in normalized_text
    assert "Technical Skills" not in normalized_text


def test_normalizer_canonicalizes_known_headings_with_extracted_icon_prefix():
    text = (
        "G Summary\n"
        "G Work Experience\n"
        "G Education\n"
        "G Skills\n"
        "G Language\n"
        "G Reference\n"
        "G skills are important for this role"
    )

    normalized_lines = normalize_text(text).splitlines()

    assert normalized_lines == [
        "summary",
        "experience",
        "education",
        "skills",
        "languages",
        "references",
        "G skills are important for this role",
    ]


def test_normalizer_does_not_strip_single_letter_content_prefix():
    text = "A Python developer with strong skills"

    assert normalize_text(text) == text


def test_prefixed_headings_keep_resume_sections_separate():
    from document_processing.resume.section_detector import detect_sections

    text = (
        "G Summary\n"
        "Experienced HR professional.\n"
        "G Work Experience\n"
        "Apr 2021 - Present\n"
        "Senior HR Executive\n"
        "PeopleSphere\n"
        "G Education\n"
        "MBA - Human Resources\n"
        "2018\n"
        "Bangalore University\n"
        "G Skills\n"
        "Recruitment\n"
        "Candidate Screening\n"
    )

    sections = detect_sections(normalize_text(text))

    assert sections["summary"] == [["Experienced HR professional."]]
    assert sections["experience"] == [[
        "Apr 2021 - Present",
        "Senior HR Executive",
        "PeopleSphere",
    ]]
    assert sections["education"] == [[
        "MBA - Human Resources",
        "2018",
        "Bangalore University",
    ]]
    assert sections["skills"] == [[
        "Recruitment",
        "Candidate Screening",
    ]]