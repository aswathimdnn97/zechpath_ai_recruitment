import pytest

from document_processing.resume.entity_extracter.education.institution_extractor import (
    extract_university_from_block,
)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("MG University - MBA", "MG University"),
        ("MG University - B.Com", "MG University"),
        ("KTU - B.Tech", "KTU"),
        (
            "Visvesvaraya Technological University, "
            "Belgaum, Karnataka, India",
            "Visvesvaraya Technological University, "
            "Belgaum, Karnataka, India",
        ),
        (
            "Visvesvaraya Technological University, "
            "Belgaum, B.Tech",
            "Visvesvaraya Technological University, Belgaum",
        ),
    ],
)
def test_university_suffix_excludes_degree_but_keeps_location(line, expected):
    result = extract_university_from_block([line])

    assert result is not None
    assert result["value"] == expected
    
    
from document_processing.resume.entity_extracter.education.university_extractor import (
    extract_university,
    remove_university_content,
    remove_years_from_university_remainder,
)


def test_remove_year_from_university_remainder():
    result = remove_years_from_university_remainder(
        ", 2025"
    )

    assert result == ""


def test_remove_year_and_separator():
    result = remove_years_from_university_remainder(
        " - 2025"
    )

    assert result == ""


def test_remove_multiple_years():
    result = remove_years_from_university_remainder(
        ", 2020 - 2025"
    )

    assert result == ""


def test_university_extraction_preserves_original_name():
    text = "University of Calicut, 2025"

    result = extract_university(text)

    assert result is not None
    assert result["value"] == "University of Calicut"


def test_remove_university_content():
    text = "University of Calicut, 2025"

    result = extract_university(text)

    cleaned = remove_university_content(
        text,
        result,
    )

    assert "University of Calicut" not in cleaned
