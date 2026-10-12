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
