from document_processing.resume.entity_extracter.projects.project_name_extractor import extract_project_name


def test_project_name_first_line():
    block = [
        "AI Resume Screening System",
        "Developed an AI-based platform.",
        "Technologies: Python, FastAPI"
    ]

    result = extract_project_name(block)

    assert result == "AI Resume Screening System"


def test_project_name_ignores_date():
    block = [
        "2024 - 2025",
        "E-Commerce Platform",
        "Built a full-stack application."
    ]

    result = extract_project_name(block)

    assert result == "E-Commerce Platform"


def test_project_name_ignores_metadata():
    block = [
        "Technologies: Python, FastAPI",
        "Resume Screening System",
        "Developed a screening application."
    ]

    result = extract_project_name(block)

    assert result == "Resume Screening System"


def test_project_name_ignores_url():
    block = [
        "https://github.com/example/project",
        "Smart Attendance System",
        "Built an attendance application."
    ]

    result = extract_project_name(block)

    assert result == "Smart Attendance System"


def test_project_name_empty_block():
    result = extract_project_name([])

    assert result is None