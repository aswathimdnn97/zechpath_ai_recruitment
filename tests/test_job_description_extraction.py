from document_processing.common.parser import parse_document
from document_processing.job_description.heading import JD_HEADINGS
from document_processing.job_description.jd_entity_extractor import extract_entities
from document_processing.job_description.job_description_normalizer import normalize_jd


def test_modern_jd_layout_extracts_title_company_and_skills():
    text = """Position Title: Python Developer
Company Name: ZechPath Labs
Location: Kochi, Kerala
Employment Type: Full-time

Responsibilities:
- Build backend services
- Develop REST APIs

Required Skills: Python, FastAPI, PostgreSQL, Git
"""

    normalized = normalize_jd(text)
    parsed = parse_document(normalized, JD_HEADINGS)
    entities = extract_entities(parsed)

    assert entities["job_title"] == "Python Developer"
    assert entities["company"] == "ZechPath Labs"
    assert "Python" in entities["required_skills"]
    assert "FastAPI" in entities["required_skills"]
    assert "PostgreSQL" in entities["required_skills"]


def test_skill_cleaner_splits_unpunctuated_technology_pairs():
    from document_processing.common.skill_cleaner import clean_skills

    skills = clean_skills([
        "Python FastAPI or Django REST APIs PostgreSQL or MySQL Git",
        "Object-Oriented Programming",
    ])

    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Django" in skills
    assert "REST APIs" in skills
    assert "PostgreSQL" in skills
    assert "MySQL" in skills
    assert "Git" in skills
    assert "Object-Oriented Programming" in skills
