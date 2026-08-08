from document_processing.resume.entity_extracter.education.field_aliase_resolver import (
    resolve_field_alias,
)


def test_resolve_cse():

    result = resolve_field_alias(
        "CSE"
    )

    assert result == "Computer Science"


def test_resolve_cs():

    result = resolve_field_alias(
        "CS"
    )

    assert result == "Computer Science"


def test_resolve_computer_science():

    result = resolve_field_alias(
        "Computer Science"
    )

    assert result == "Computer Science"