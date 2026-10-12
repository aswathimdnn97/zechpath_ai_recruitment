from parsers.pdf_reader import read_pdf
from parsers.docx_reader import read_docx
from document_processing.common.cleaner import clean_text
from document_processing.resume.resume_normalizer import normalize_text
from document_processing.common.handling_layout import fix_layout
from document_processing.resume.entity_extracter.experience.company_extractor import extract_companies
from document_processing.resume.entity_extracter.experience.duration_calculator import extract_duration
from document_processing.resume.entity_extracter.experience.experince_block_splitter import split_experience_blocks
from document_processing.resume.entity_extracter.experience.location_extractor import extract_location
from document_processing.resume.entity_extracter.experience.title_extractor import extract_titles
from document_processing.resume.entity_extracter.education.field_of_study_extractor import extract_field_of_study
from document_processing.resume.entity_extracter.certifications.certification_pipeline import certification_pipeline
from document_processing.resume.entity_extracter.skill.skill_list_splitter import split_skill_line
from document_processing.resume.entity_extracter.skill.master_skill_validator import validate_skills

file="data/resume/pdf/spzqwjxjttgn.pdf"
def test_resume_pipeline():
    file="data/resumes/RES_2E715359D71F.pdf"
    
    raw_text=read_pdf(file)
    
    cleaned_text=clean_text(raw_text)
    
    normalized_text=normalize_text(cleaned_text)
    
    handledlayout_text=fix_layout(normalized_text)
    
    assert raw_text is not None
    assert cleaned_text is not None
    assert normalized_text is not None
    assert handledlayout_text is not None


def test_backend_skill_line_is_split_and_validated():
    raw_skills = [[
        "Backend: Django, Django REST Framework, Fast API, Flask, REST APIs"
    ]]

    items = split_skill_line(raw_skills)
    assert items == [
        "Django",
        "Django REST Framework",
        "FastAPI",
        "Flask",
        "REST APIs",
    ]

    validated = validate_skills(items)
    assert any(skill["skill_id"] == "TECH012" for skill in validated)
    assert any(skill["skill_id"] == "TECH014" for skill in validated)
    assert any(skill["skill_id"] == "TECH013" for skill in validated)
    assert any(skill["skill_id"] == "TECH025" for skill in validated)
    assert all(skill["skill_id"] is not None for skill in validated if skill["skill"] != "Django REST Framework")


def test_whitespace_separated_skills_are_split_and_validated():
    raw_skills = "Python SQL MySQL JavaScript HTML CSS Git"

    items = split_skill_line(raw_skills)
    validated = validate_skills(items)

    assert [skill["skill"] for skill in validated] == [
        "Python",
        "SQL",
        "MySQL",
        "JavaScript",
        "HTML",
        "CSS",
        "Git",
    ]


def test_extract_companies_from_multi_company_experience():
    experience_block = [
        "Senior Software Engineer",
        "ABC Technologies, XYZ Solutions",
        "Jan 2020 - Present",
    ]

    companies = extract_companies(experience_block)

    assert companies == ["ABC Technologies", "XYZ Solutions"]


def test_action_sentence_is_not_treated_as_title():
    experience_block = [
        "Led Spring Boot micro service development and Kafka integrations.",
        "Enterprise Soft Chennai",
        "Jan 2021 - Present",
    ]

    titles = extract_titles(experience_block)

    assert titles == []


def test_city_state_is_not_treated_as_title():
    experience_block = [
        "Backend Trainee - Code Nest Academy",
        "Kochi, Kerala",
        "Jun 2025 - Dec 2025",
    ]

    titles = extract_titles(experience_block)

    assert titles == ["Backend Trainee"]


def test_inline_company_title_and_full_month_dates_split_experiences():
    lines = [
        "Zecser Business LLP, Kochi | Data Science Engineer Intern July 2026 \u2013 present",
        "Working on data science and Python-based projects as part of an internship.",
        "Sorice Solutions Private Limited, Palarivattom | Java Developer Trainee July 2022 \uFFFD July 2023",
    ]

    blocks = split_experience_blocks(lines)

    assert len(blocks) == 2
    assert [extract_titles(block)[0] for block in blocks] == [
        "Data Science Engineer Intern",
        "Java Developer Trainee",
    ]
    assert [extract_companies(block)[0] for block in blocks] == [
        "Zecser Business LLP",
        "Sorice Solutions Private Limited",
    ]
    assert [extract_location(block) for block in blocks] == [
        "Kochi",
        "Palarivattom",
    ]
    assert [extract_duration(block) for block in blocks] == [
        {"start_date": "July 2026", "end_date": "present"},
        {"start_date": "July 2022", "end_date": "July 2023"},
    ]


def test_description_sentence_is_not_treated_as_title_in_date_parser():
    from document_processing.resume.experience_parser import parse_experience_lines

    lines = [
        "Software Trainee - LearnCode Institute",
        "Aug 2025 - Mar 2026",
        "Prepared SQL queries and documented application workflows.",
    ]

    records = parse_experience_lines(lines)

    assert records and records[0]["title"] == "Software Trainee"
    assert records[0]["company"] is None
    assert records[0]["description"] == [
        "Prepared SQL queries and documented application workflows."
    ]


def test_title_company_line_is_not_rejected_as_company():
    experience_block = [
        "Software Trainee - LearnCode Institute Aug 2025 - Mar 2026",
        "Thiruvananthapuram, Kerala",
        "Prepared SQL queries and documented application workflows.",
    ]

    titles = extract_titles(experience_block)

    assert titles == ["Software Trainee"]


def test_field_of_study_extracted_from_degree_in_pattern():
    education_block = [
        "Bachelor of Engineering in Computer Science and Engineering",
        "Anna University, Chennai",
        "2016",
    ]

    field = extract_field_of_study(education_block)

    assert field == "Computer Science and Engineering"


def test_field_of_study_extracted_from_degree_without_in_keyword():
    education_block = [
        "Bachelor of Technology Computer Science and Engineering",
        "KTU",
        "2026",
    ]

    field = extract_field_of_study(education_block)

    assert field == "Computer Science and Engineering"


def test_template_agnostic_fallback_detects_sections_without_headings():
    from document_processing.resume.section_detector import detect_sections

    text = (
        "B.Tech in Computer Science and Engineering\n"
        "KTU\n"
        "2026\n"
        "Backend Trainee - LearnCode Institute\n"
        "Aug 2025 - Mar 2026\n"
        "Prepared SQL queries and documented application workflows.\n"
        "Python, SQL, JavaScript, HTML, CSS"
    )

    sections = detect_sections(text)

    assert "education" in sections
    assert "experience" in sections
    assert "skills" in sections


def test_certificate_entries_with_completed_status_are_extracted():
    certificate_lines = [
        "Python / Domain Certification",
        "Completed",
        "Professional Development Program",
        "Completed",
        "Workplace Communication",
        "Completed",
    ]

    certs = certification_pipeline(certificate_lines)

    assert [cert["certification_name"] for cert in certs] == [
        "Python Domain Certification",
        "Professional Development Program",
        "Workplace Communication",
    ]


def test_certificate_heading_is_detected_as_section():
    from document_processing.resume.section_detector import detect_sections

    text = "Certificate\nPython / Domain Certification Completed\nProfessional Development Program Completed\nWorkplace Communication Completed"

    sections = detect_sections(text)

    assert "certifications" in sections
    assert sections["certifications"]


def test_professional_certification_entry_is_not_treated_as_a_heading():
    from document_processing.resume.resume_normalizer import normalize_text
    from document_processing.resume.section_detector import detect_sections

    text = (
        "Certificate\n"
        "Professional Certification\n"
        "Completed\n"
        "Industry Skills Program\n"
        "Completed\n"
        "Advanced Workplace Training\n"
        "Completed"
    )

    sections = detect_sections(normalize_text(text))
    certifications = certification_pipeline(sections["certifications"])

    assert [
        certification["certification_name"]
        for certification in certifications
    ] == [
        "Professional Certification",
        "Industry Skills Program",
        "Advanced Workplace Training",
    ]

    standalone_heading = detect_sections(
        normalize_text(
            "Professional Certification\n"
            "AWS Certified Solutions Architect"
        )
    )

    assert standalone_heading["certifications"] == [
        ["AWS Certified Solutions Architect"]
    ]


def test_inline_certificate_line_with_completed_markers_is_split():
    certificate_lines = [
        "Certificate Python / Domain Certification Completed Professional Development Program Completed Workplace Communication Completed"
    ]

    certs = certification_pipeline(certificate_lines)

    assert [cert["certification_name"] for cert in certs] == [
        "Python Domain Certification",
        "Professional Development Program",
        "Workplace Communication",
    ]


def test_company_name_without_duration():
    from document_processing.resume.entity_extracter.experience.company_extractor import strip_dates_from_company
    
    assert strip_dates_from_company("Tech Nova Labs Jan 2026 - Apr 2026") == "Tech Nova Labs"
    assert strip_dates_from_company("ABC Corp Jan 2020 - Present") == "ABC Corp"
    assert strip_dates_from_company("XYZ Inc May 2023 - Jun 2024") == "XYZ Inc"
    assert strip_dates_from_company("Code Nest Academy Jun 2025 - Dec 2025") == "Code Nest Academy"


def test_location_is_excluded_from_description():
    from document_processing.resume.entity_extracter.experience.description_extraction import extract_description
    
    experience_block = [
        "Backend Trainee - Code Nest Academy",
        "Kochi, Kerala",
        "Developed a Django application for student records and authentication."
    ]
    
    desc = extract_description(experience_block)
    
    assert desc == ["Backend Trainee - Code Nest Academy", "Developed a Django application for student records and authentication."]
    assert "Kochi, Kerala" not in desc


def test_ktu_university_is_extracted():
    from document_processing.resume.entity_extracter.education.institution_extractor import extract_university

    education_block = [
        "Bachelor of Technology in Computer Science",
        "KTU",
        "2024"
    ]

    university = extract_university(education_block)

    assert university == "KTU"
    