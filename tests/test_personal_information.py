from document_processing.resume.entity_extracter.personal_information.location_extractor import extract_location
from document_processing.resume.section_detector import detect_sections


def test_extract_location_skips_contact_line():
    text = (
        "ARJUN MENON\n"
        "Bengaluru, Karnataka, India | 91 98765 43210 | arjun.menon.dev@example.com | linkedin.com/in/arjunmenon | github.com/arjunmenon\n"
        "Senior Software Engineer"
    )

    assert extract_location(text) == "Bengaluru, Karnataka, India"


def test_extract_location_skips_title_header_and_keeps_city_location():
    text = (
        "ARUN KUMAR\n"
        "Junior Python Developer | Fresher\n"
        "Kochi, Kerala | +91 98765 43210\n"
        "arun.k.dev@example.com"
    )

    assert extract_location(text) == "Kochi, Kerala"


def test_detect_sections_supports_layout_variants():
    text = (
        "TECHNICAL SKILLS:\n"
        "Python, FastAPI, PostgreSQL\n"
        "\n"
        "EDUCATION DETAILS\n"
        "B.Tech in Computer Science\n"
        "\n"
        "WORK EXPERIENCE\n"
        "Python Developer at Tech Nova"
    )

    result = detect_sections(text, {"skills", "education", "experience"})

    assert "skills" in result
    assert "education" in result
    assert "experience" in result
