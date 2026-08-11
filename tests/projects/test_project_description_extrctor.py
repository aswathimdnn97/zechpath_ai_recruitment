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