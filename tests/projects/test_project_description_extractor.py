from document_processing.resume.entity_extracter.projects.project_description_extractor import (
    extract_project_description
)


def test_extract_description():

    block = [
        "AI Resume Screening System",
        "Developed an AI-based resume screening platform.",
        "The system extracts candidate skills.",
        "Technologies: Python, FastAPI",
    ]

    result = extract_project_description(block)

    assert (
        result
        == "Developed an AI-based resume screening platform. "
           "The system extracts candidate skills."
    )


def test_description_multiple_lines():

    block = [
        "E-Commerce Platform",
        "Built a full-stack e-commerce application.",
        "Implemented authentication and product management.",
        "Integrated payment processing.",
    ]

    result = extract_project_description(block)

    assert (
        result
        == "Built a full-stack e-commerce application. "
           "Implemented authentication and product management. "
           "Integrated payment processing."
    )


def test_ignore_technologies():

    block = [
        "E-Commerce Platform",
        "Built an online shopping application.",
        "Technologies: React, Node.js, MongoDB",
    ]

    result = extract_project_description(block)

    assert result == "Built an online shopping application."


def test_ignore_url():

    block = [
        "Portfolio Website",
        "Created a responsive portfolio website.",
        "GitHub: https://github.com/example/portfolio",
    ]

    result = extract_project_description(block)

    assert result == "Created a responsive portfolio website."


def test_no_description():

    block = [
        "Resume Screening System",
        "Technologies: Python, FastAPI",
        "GitHub: https://github.com/example/project",
    ]

    result = extract_project_description(block)

    assert result is None


def test_empty_block():

    result = extract_project_description([])

    assert result is None
    



def test_extract_description_from_inline_project_title():
    block = [
        "Student Records REST API - Developed a small backend service "
        "using Python, Django, and FastAPI practice endpoints; "
        "connected PostgreSQL for persistent records and used Git "
        "for version control. Validated endpoints with Postman, "
        "including successful and invalid requests."
    ]

    description = extract_project_description(block)

    assert description is not None
    assert description.startswith("Developed a small backend service")
    assert "connected PostgreSQL" in description
    assert "used Git for version control" in description
    assert "Validated endpoints with Postman" in description


def test_extract_description_from_multiple_lines():
    block = [
        "Student Records REST API",
        "Developed a backend service using Python and Django.",
        "Connected PostgreSQL for persistent records.",
        "Validated endpoints using Postman.",
    ]

    description = extract_project_description(block)

    assert description is not None
    assert "Developed a backend service" in description
    assert "Connected PostgreSQL" in description
    assert "Validated endpoints using Postman" in description


def test_extract_narrative_from_technology_line():
    block = [
        "Student Records REST API",
        "Technologies: Python, Django. Developed a REST API "
        "for managing student records.",
    ]

    description = extract_project_description(block)

    assert description is not None
    assert "Developed a REST API" in description


def test_metadata_and_url_are_not_in_description():
    block = [
        "Student Records REST API",
        "Technologies: Python, Django",
        "GitHub: https://github.com/example/project",
        "Developed a service for managing student records.",
    ]

    description = extract_project_description(block)

    assert description is not None
    assert "Developed a service" in description
    assert "Technologies:" not in description
    assert "github.com" not in description


def test_description_missing_returns_none():
    block = [
        "Student Records REST API",
        "Technologies: Python, Django",
        "GitHub: https://github.com/example/project",
    ]

    assert extract_project_description(block) is None


def test_empty_block_returns_none():
    assert extract_project_description([]) is None
    assert extract_project_description("") is None


def test_string_input_with_inline_description():
    block = (
        "Student Records REST API - Developed a backend service "
        "using Django and PostgreSQL."
    )

    description = extract_project_description(block)

    assert description is not None
    assert description.startswith("Developed a backend service")
