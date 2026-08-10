from document_processing.resume.entity_extracter.personal_information.location_extractor import extract_location


def test_extract_location_skips_contact_line():
    text = (
        "ARJUN MENON\n"
        "Bengaluru, Karnataka, India | 91 98765 43210 | arjun.menon.dev@example.com | linkedin.com/in/arjunmenon | github.com/arjunmenon\n"
        "Senior Software Engineer"
    )

    assert extract_location(text) == "Bengaluru, Karnataka, India"
