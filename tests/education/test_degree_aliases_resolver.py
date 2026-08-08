from document_processing.resume.entity_extracter.education.degree_aliases_resolver import (
    resolve_degree_alias,
)


def test_resolve_be():

    result = resolve_degree_alias("B.E")

    assert result == "Bachelor of Engineering"


def test_resolve_btech():

    result = resolve_degree_alias("B.Tech")

    assert result == "Bachelor of Technology"


def test_resolve_mca():

    result = resolve_degree_alias("MCA")

    assert result == "Master of Computer Applications"


def test_unknown_degree():

    result = resolve_degree_alias("Unknown Degree")

    assert result == "Unknown Degree"