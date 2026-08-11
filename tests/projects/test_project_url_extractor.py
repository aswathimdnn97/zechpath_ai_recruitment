from document_processing.resume.entity_extracter.projects.project_url_extractor import extract_project_url


def test_github_url():

    block = [
        "AI Resume Screening System",
        "Technologies: Python, FastAPI",
        "GitHub: https://github.com/user/resume-screening"
    ]

    result = extract_project_url(block)

    assert result == "https://github.com/user/resume-screening"


def test_github_without_protocol():

    block = [
        "Portfolio Website",
        "github.com/user/portfolio"
    ]

    result = extract_project_url(block)

    assert result == "https://github.com/user/portfolio"


def test_demo_url():

    block = [
        "E-Commerce Platform",
        "Built a shopping application.",
        "Demo: https://example.com/shop"
    ]

    result = extract_project_url(block)

    assert result == "https://example.com/shop"


def test_gitlab_url():

    block = [
        "Machine Learning Project",
        "GitLab: https://gitlab.com/user/ml-project"
    ]

    result = extract_project_url(block)

    assert result == "https://gitlab.com/user/ml-project"


def test_url_with_trailing_punctuation():

    block = [
        "Portfolio Website",
        "GitHub: https://github.com/user/portfolio."
    ]

    result = extract_project_url(block)

    assert result == "https://github.com/user/portfolio"


def test_no_url():

    block = [
        "Attendance System",
        "Technologies: Python, OpenCV",
        "Developed an attendance application."
    ]

    result = extract_project_url(block)

    assert result is None


def test_empty_block():

    result = extract_project_url([])

    assert result is None