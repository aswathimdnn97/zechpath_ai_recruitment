from document_processing.resume.entity_extracter.projects.project_block_splitter import split_project_blocks


def test_multiple_projects():

    section = [
        "AI Resume Screening System",
        "Developed an AI-based screening platform.",
        "Technologies: Python, FastAPI",
        "",
        "E-Commerce Platform",
        "Built a full-stack shopping application.",
        "Technologies: React, Node.js, MongoDB",
    ]

    result = split_project_blocks(section)

    assert len(result) == 2
    assert result[0][0] == "AI Resume Screening System"
    assert result[1][0] == "E-Commerce Platform"


def test_explicit_project_labels():

    section = [
        "Project: AI Resume Screening System",
        "Developed an AI-based platform.",
        "Technologies: Python, FastAPI",
        "",
        "Project: E-Commerce Platform",
        "Built an online shopping application.",
    ]

    result = split_project_blocks(section)

    assert len(result) == 2
    assert result[0][0] == "AI Resume Screening System"
    assert result[1][0] == "E-Commerce Platform"


def test_empty_section():

    result = split_project_blocks([])

    assert result == []


def test_string_input():

    section = """
    AI Resume Screening System
    Developed an AI-based screening platform.

    E-Commerce Platform
    Built a shopping application.
    """

    result = split_project_blocks(section)

    assert len(result) == 2
    
    

from document_processing.resume.entity_extracter.projects.project_block_splitter import (
    split_project_blocks,
)


def test_split_inline_project_title_and_description():
    section = [
        "Student Records REST API - Developed a small backend service "
        "using Python, Django, and FastAPI practice endpoints; "
        "connected PostgreSQL for persistent records and used Git "
        "for version control. Validated endpoints with Postman, "
        "including successful and invalid requests."
    ]

    blocks = split_project_blocks(section)

    assert len(blocks) == 1
    assert blocks[0][0] == "Student Records REST API"
    assert blocks[0][1].startswith("Developed a small backend service")
    assert "connected PostgreSQL" in blocks[0][1]


def test_split_multiple_projects():
    section = [
        "Student Records REST API",
        "Developed an API using Python and Django.",
        "Technologies: Python, Django, PostgreSQL",
        "Online Shopping Platform",
        "Built a shopping website using React and FastAPI.",
        "Technologies: React, FastAPI",
    ]

    blocks = split_project_blocks(section)

    assert len(blocks) == 2
    assert blocks[0][0] == "Student Records REST API"
    assert blocks[1][0] == "Online Shopping Platform"


def test_metadata_does_not_start_new_project():
    section = [
        "Student Records REST API",
        "Developed an API for student records.",
        "Technologies: Python, Django",
        "GitHub: https://github.com/example/project",
    ]

    blocks = split_project_blocks(section)

    assert len(blocks) == 1
    assert any(
        line.startswith("Technologies:")
        for line in blocks[0]
    )


def test_explicit_project_label():
    section = [
        "Project: Student Records REST API",
        "Developed an API using Django.",
        "Project: Online Shopping Platform",
        "Built a shopping application.",
    ]

    blocks = split_project_blocks(section)

    assert len(blocks) == 2
    assert blocks[0][0] == "Student Records REST API"
    assert blocks[1][0] == "Online Shopping Platform"


def test_inline_description_with_unicode_dash():
    section = [
        "Student Records REST API — Developed an API using Django."
    ]

    blocks = split_project_blocks(section)

    assert len(blocks) == 1
    assert blocks[0][0] == "Student Records REST API"
    assert blocks[0][1] == "Developed an API using Django."
