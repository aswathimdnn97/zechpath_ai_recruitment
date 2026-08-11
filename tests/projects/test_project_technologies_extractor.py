from document_processing.resume.entity_extracter.projects.project_technologies_extractor import (
    extract_project_technologies
)


def test_comma_separated_technologies():

    block = [
        "AI Resume Screening System",
        "Technologies: Python, FastAPI, PostgreSQL"
    ]

    result = extract_project_technologies(block)

    assert result == [
        "Python",
        "FastAPI",
        "PostgreSQL"
    ]


def test_pipe_separated_technologies():

    block = [
        "E-Commerce Platform",
        "Tech Stack: React | Node.js | Express | MongoDB"
    ]

    result = extract_project_technologies(block)

    assert result == [
        "React",
        "Node.js",
        "Express",
        "MongoDB"
    ]


def test_semicolon_separated_technologies():

    block = [
        "Attendance System",
        "Tools: Python; OpenCV; MySQL"
    ]

    result = extract_project_technologies(block)

    assert result == [
        "Python",
        "OpenCV",
        "MySQL"
    ]


def test_multiple_technology_lines():

    block = [
        "Cloud Application",
        "Technologies: Python, Django",
        "Tools: Docker, AWS, Git"
    ]

    result = extract_project_technologies(block)

    assert result == [
        "Python",
        "Django",
        "Docker",
        "AWS",
        "Git"
    ]


def test_duplicate_technologies():

    block = [
        "AI Application",
        "Technologies: Python, FastAPI, Python"
    ]

    result = extract_project_technologies(block)

    assert result == [
        "Python",
        "FastAPI"
    ]


def test_no_technology():

    block = [
        "Portfolio Website",
        "Created a responsive portfolio website.",
        "GitHub: https://github.com/example/portfolio"
    ]

    result = extract_project_technologies(block)

    assert result == []


def test_empty_block():

    result = extract_project_technologies([])

    assert result == []