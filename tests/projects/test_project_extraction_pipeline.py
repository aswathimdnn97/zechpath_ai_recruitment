from document_processing.resume.entity_extracter.projects.project_extraction_pipeline import extract_projects


def test_project_extraction_pipeline():
    section = [
        "AI Resume Screening System",
        "Developed an AI-based resume screening platform.",
        "The system extracts candidate skills and compares them "
        "against job descriptions.",
        "Technologies: Python, FastAPI, PostgreSQL",
        "GitHub: https://github.com/user/resume-screening",
        "",
        "E-Commerce Platform",
        "Built a full-stack e-commerce application.",
        "Implemented authentication and product management.",
        "Technologies: React, Node.js, MongoDB",
        "Demo: https://example.com/ecommerce",
    ]

    result = extract_projects(section)

    # --------------------------------------------------------
    # Number of projects
    # --------------------------------------------------------

    assert len(result) == 2

    # --------------------------------------------------------
    # First project
    # --------------------------------------------------------

    first_project = result[0]

    assert first_project["project_name"] == (
        "AI Resume Screening System"
    )

    assert first_project["description"] == (
        "Developed an AI-based resume screening platform. "
        "The system extracts candidate skills and compares them "
        "against job descriptions."
    )

    assert "Python" in first_project["technologies"]
    assert "FastAPI" in first_project["technologies"]
    assert "PostgreSQL" in first_project["technologies"]

    assert first_project["url"] == (
        "https://github.com/user/resume-screening"
    )

    # --------------------------------------------------------
    # Second project
    # --------------------------------------------------------

    second_project = result[1]

    assert second_project["project_name"] == (
        "E-Commerce Platform"
    )

    assert second_project["description"] == (
        "Built a full-stack e-commerce application. "
        "Implemented authentication and product management."
    )

    assert "React" in second_project["technologies"]
    assert "Node.js" in second_project["technologies"]
    assert "MongoDB" in second_project["technologies"]

    assert second_project["url"] == (
        "https://example.com/ecommerce"
    )


def test_project_pipeline_empty_section():

    result = extract_projects([])

    assert result == []


def test_project_pipeline_single_project():

    section = [
        "Weather Prediction System",
        "Developed a machine learning application "
        "for weather prediction.",
        "Technologies: Python, Scikit-learn",
        "GitHub: https://github.com/user/weather",
    ]

    result = extract_projects(section)

    assert len(result) == 1

    project = result[0]

    assert project["project_name"] == (
        "Weather Prediction System"
    )

    assert "machine learning application" in (
        project["description"]
    )

    assert "Python" in project["technologies"]

    assert project["url"] == (
        "https://github.com/user/weather"
    )


def test_project_pipeline_without_url():

    section = [
        "Face Recognition System",
        "Developed a face recognition application.",
        "Technologies: Python, OpenCV",
    ]

    result = extract_projects(section)

    assert len(result) == 1

    project = result[0]

    assert project["project_name"] == (
        "Face Recognition System"
    )

    assert project["description"] == (
        "Developed a face recognition application."
    )

    assert "Python" in project["technologies"]
    assert "OpenCV" in project["technologies"]

    assert project["url"] is None
    

from document_processing.resume.entity_extracter.projects.project_name_extractor import (
    extract_project_name,
)
from document_processing.resume.entity_extracter.projects.project_technologies_extractor import (
    extract_project_technologies,
)
from document_processing.resume.entity_extracter.projects.project_url_extractor import (
    extract_project_url,
)


def test_extract_project_name_from_inline_description():
    block = [
        "Student Records REST API - Developed a small backend service "
        "using Python, Django, and FastAPI practice endpoints"
    ]

    assert extract_project_name(block) == "Student Records REST API"


def test_extract_project_technologies_from_narrative():
    block = [
        "Student Records REST API - Developed a backend service "
        "using Python, Django, and FastAPI.",
        "Connected PostgreSQL for persistent records and used Git "
        "for version control.",
        "Validated endpoints with Postman.",
    ]

    technologies = extract_project_technologies(block)

    for expected in [
        "Python",
        "Django",
        "FastAPI",
        "PostgreSQL",
        "Git",
        "Postman",
    ]:
        assert expected in technologies


def test_extract_project_url_from_markdown_link():
    block = [
        "Student Records REST API",
        "GitHub: [Project](https://github.com/example/project)",
    ]

    assert extract_project_url(block) == (
        "https://github.com/example/project"
    )


def test_missing_project_url_returns_none():
    block = [
        "Student Records REST API",
        "Developed a backend service using Python.",
    ]

    assert extract_project_url(block) is None
