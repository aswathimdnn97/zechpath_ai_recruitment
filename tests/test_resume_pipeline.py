from parsers.pdf_reader import read_pdf
from parsers.docx_reader import read_docx
from document_processing.common.cleaner import clean_text
from document_processing.resume.resume_normalizer import normalize_text
from document_processing.common.handling_layout import fix_layout
from document_processing.resume.entity_extracter.experience.company_extractor import extract_companies
from document_processing.resume.entity_extracter.skill.skill_list_splitter import split_skill_line
from document_processing.resume.entity_extracter.skill.master_skill_validator import validate_skills

file="data/resume/pdf/spzqwjxjttgn.pdf"
def test_resume_pipeline():
    file="data/resume/pdf/spzqwjxjttgn.pdf"
    
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


def test_extract_companies_from_multi_company_experience():
    experience_block = [
        "Senior Software Engineer",
        "ABC Technologies, XYZ Solutions",
        "Jan 2020 - Present",
    ]

    companies = extract_companies(experience_block)

    assert companies == ["ABC Technologies", "XYZ Solutions"]
    