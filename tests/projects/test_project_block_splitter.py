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