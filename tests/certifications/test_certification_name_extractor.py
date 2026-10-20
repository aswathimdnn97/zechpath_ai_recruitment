from document_processing.resume.entity_extracter.certifications.certification_name_extractor import extract_certification_name
import pytest

def test_rejects_resume_title_as_certification():
    block = [
        (
            "ZechPath ATS evaluation resume - RES_EVAL_002 "
            "- Fictional test data for eligibility API validation"
        )
    ]

    assert extract_certification_name(block) is None


def test_accepts_python_programming_fundamentals():
    assert extract_certification_name([
        "Python Programming Fundamentals"
    ]) == "Python Programming Fundamentals"


def test_accepts_backend_api_development_and_testing():
    assert extract_certification_name([
        "Backend API Development and Testing"
    ]) == "Backend API Development and Testing"


def test_preserves_domain_certification():
    assert extract_certification_name([
        "Python / Domain Certification",
        "Completed",
    ]) == "Python / Domain Certification"