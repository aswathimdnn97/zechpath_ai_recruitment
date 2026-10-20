import pytest

from document_processing.resume.entity_extracter.experience import (
    experinece_pipeline as pipeline,
)


# ============================================================
# TEST HELPERS
# ============================================================

def configure_deterministic_pipeline(monkeypatch):
    """Configure predictable deterministic extractor results."""

    monkeypatch.setattr(
        pipeline,
        "split_experience_blocks",
        lambda section: section if isinstance(section, list) else [section],
    )

    monkeypatch.setattr(
        pipeline,
        "extract_titles",
        lambda block: ["Software Developer"],
    )
    monkeypatch.setattr(
        pipeline,
        "resolve_title_alias",
        lambda title: title,
    )
    monkeypatch.setattr(
        pipeline,
        "validate_title",
        lambda title: title,
    )

    monkeypatch.setattr(
        pipeline,
        "extract_companies",
        lambda block: ["TechNova"],
    )
    monkeypatch.setattr(
        pipeline,
        "resolve_company_aliases",
        lambda companies: companies,
    )
    monkeypatch.setattr(
        pipeline,
        "validate_companies",
        lambda companies: companies,
    )

    monkeypatch.setattr(
        pipeline,
        "extract_duration",
        lambda block: "January 2022 - December 2023",
    )
    monkeypatch.setattr(
        pipeline,
        "calculate_experience",
        lambda duration: 2.0,
    )

    monkeypatch.setattr(
        pipeline,
        "extract_description",
        lambda block, **kwargs: "Developed web applications.",
    )
    monkeypatch.setattr(
        pipeline,
        "extract_location",
        lambda block: "Kochi",
    )
    monkeypatch.setattr(
        pipeline,
        "extract_employment_type",
        lambda block: "Full-time",
    )
    monkeypatch.setattr(
        pipeline,
        "extract_department",
        lambda block: "Engineering",
    )

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {},
    )


def empty_deterministic_fields(monkeypatch):
    """Make all LLM-supported deterministic fields missing."""

    monkeypatch.setattr(pipeline, "extract_titles", lambda block: [])
    monkeypatch.setattr(pipeline, "extract_companies", lambda block: [])
    monkeypatch.setattr(pipeline, "extract_location", lambda block: None)
    monkeypatch.setattr(pipeline, "extract_employment_type", lambda block: None)
    monkeypatch.setattr(pipeline, "extract_department", lambda block: None)
    monkeypatch.setattr(
        pipeline,
        "extract_description",
        lambda block, **kwargs: None,
    )


# ============================================================
# BASIC INPUT TESTS
# ============================================================

def test_empty_experience_section_returns_empty_list():
    assert pipeline.experience_extractor(None, profile=False) == []
    assert pipeline.experience_extractor("", profile=False) == []
    assert pipeline.experience_extractor([], profile=False) == []


def test_no_experience_blocks_returns_empty_list(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "split_experience_blocks",
        lambda section: [],
    )

    assert pipeline.experience_extractor(
        "Some resume text",
        profile=False,
    ) == []


def test_empty_blocks_are_skipped(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)

    result = pipeline.experience_extractor(
        ["", "Software Developer at TechNova"],
        profile=False,
    )

    assert len(result) == 1
    assert result[0]["title"] == "Software Developer"


# ============================================================
# DETERMINISTIC EXTRACTION TESTS
# ============================================================

def test_deterministic_extraction_returns_expected_fields(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)

    result = pipeline.experience_extractor(
        ["Software Developer at TechNova"],
        profile=False,
    )

    assert len(result) == 1

    experience = result[0]

    assert experience["title"] == "Software Developer"
    assert experience["company"] == "TechNova"
    assert experience["duration"] == "January 2022 - December 2023"
    assert experience["total_experience"] == 2.0
    assert experience["location"] == "Kochi"
    assert experience["employment_type"] == "Full-time"
    assert experience["department"] == "Engineering"
    assert experience["description"] == "Developed web applications."


def test_deterministic_results_bypass_llm(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)

    def fail_if_called(block):
        pytest.fail("LLM fallback should not run when all fields exist")

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        fail_if_called,
    )

    result = pipeline.experience_extractor(
        ["Software Developer at TechNova"],
        profile=False,
    )

    assert result[0]["company"] == "TechNova"


def test_missing_title_is_handled_without_crashing(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)

    monkeypatch.setattr(pipeline, "extract_titles", lambda block: [])
    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {},
    )

    result = pipeline.experience_extractor(
        ["Worked on web applications"],
        profile=False,
    )

    assert len(result) == 1
    assert result[0]["title"] is None


def test_missing_company_is_handled_without_crashing(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)

    monkeypatch.setattr(pipeline, "extract_companies", lambda block: [])
    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {},
    )

    result = pipeline.experience_extractor(
        ["Software Developer"],
        profile=False,
    )

    assert len(result) == 1
    assert result[0]["company"] is None


# ============================================================
# LLM FALLBACK TESTS
# ============================================================

def test_llm_fallback_recovers_missing_fields(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)
    empty_deterministic_fields(monkeypatch)

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {
            "title": "Backend Developer",
            "company": "TechNova",
            "location": "Kochi",
            "employment_type": "Full-time",
            "department": "Engineering",
            "description": "Developed REST APIs.",
        },
    )

    result = pipeline.experience_extractor(
        ["Backend Developer at TechNova, Kochi"],
        profile=False,
    )

    experience = result[0]

    assert experience["title"] == "Backend Developer"
    assert experience["company"] == "TechNova"
    assert experience["location"] == "Kochi"
    assert experience["employment_type"] == "Full-time"
    assert experience["department"] == "Engineering"
    assert experience["description"] == "Developed REST APIs."


def test_llm_fallback_does_not_overwrite_existing_fields(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)

    monkeypatch.setattr(
        pipeline,
        "extract_location",
        lambda block: None,
    )

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {
            "title": "Incorrect Title",
            "company": "Incorrect Company",
            "location": "Chennai",
            "employment_type": "Contract",
            "department": "Sales",
            "description": "Different description",
        },
    )

    result = pipeline.experience_extractor(
        ["Software Developer at TechNova"],
        profile=False,
    )

    experience = result[0]

    assert experience["title"] == "Software Developer"
    assert experience["company"] == "TechNova"
    assert experience["location"] == "Chennai"
    assert experience["employment_type"] == "Full-time"
    assert experience["department"] == "Engineering"
    assert experience["description"] == "Developed web applications."


def test_llm_fallback_empty_response_preserves_missing_values(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)
    empty_deterministic_fields(monkeypatch)

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {},
    )

    result = pipeline.experience_extractor(
        ["Unstructured employment text"],
        profile=False,
    )

    experience = result[0]

    assert experience["title"] is None
    assert experience["company"] is None
    assert experience["location"] is None
    assert experience["employment_type"] is None
    assert experience["department"] is None
    assert experience["description"] is None


def test_llm_fallback_is_not_called_when_only_duration_is_missing(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)

    monkeypatch.setattr(
        pipeline,
        "extract_duration",
        lambda block: None,
    )

    def fail_if_called(block):
        pytest.fail("Missing duration alone should not trigger this fallback")

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        fail_if_called,
    )

    result = pipeline.experience_extractor(
        ["Software Developer at TechNova"],
        profile=False,
    )

    assert len(result) == 1
    assert result[0]["duration"] is None


# ============================================================
# TITLE AND COMPANY VALIDATION TESTS
# ============================================================

def test_llm_title_is_validated(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)
    monkeypatch.setattr(pipeline, "extract_titles", lambda block: [])

    monkeypatch.setattr(
        pipeline,
        "resolve_title_alias",
        lambda title: f"RESOLVED:{title}",
    )
    monkeypatch.setattr(
        pipeline,
        "validate_title",
        lambda title: title if title == "RESOLVED:Backend Developer" else None,
    )

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {"title": "Backend Developer"},
    )

    result = pipeline.experience_extractor(
        ["Backend Developer"],
        profile=False,
    )

    assert result[0]["title"] == "RESOLVED:Backend Developer"


def test_invalid_llm_title_is_rejected(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)
    monkeypatch.setattr(pipeline, "extract_titles", lambda block: [])

    monkeypatch.setattr(
        pipeline,
        "validate_title",
        lambda title: None,
    )

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {"title": "Unverified Role"},
    )

    result = pipeline.experience_extractor(
        ["Unverified Role"],
        profile=False,
    )

    assert result[0]["title"] is None


def test_llm_company_is_validated(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)
    monkeypatch.setattr(pipeline, "extract_companies", lambda block: [])

    monkeypatch.setattr(
        pipeline,
        "resolve_company_aliases",
        lambda companies: companies,
    )
    monkeypatch.setattr(
        pipeline,
        "validate_companies",
        lambda companies: (
            ["TechNova Ltd"]
            if companies == ["TechNova"]
            else []
        ),
    )

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {"company": "TechNova"},
    )

    result = pipeline.experience_extractor(
        ["Worked at TechNova"],
        profile=False,
    )

    assert result[0]["company"] == "TechNova Ltd"


def test_invalid_llm_company_is_rejected(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)
    monkeypatch.setattr(pipeline, "extract_companies", lambda block: [])

    monkeypatch.setattr(
        pipeline,
        "validate_companies",
        lambda companies: [],
    )

    monkeypatch.setattr(
        pipeline,
        "_llm_experience_fallback",
        lambda block: {"company": "Unknown Company"},
    )

    result = pipeline.experience_extractor(
        ["Worked somewhere"],
        profile=False,
    )

    assert result[0]["company"] is None


# ============================================================
# SHARED LLM SERVICE TESTS
# ============================================================

def test_llm_fallback_returns_cleaned_response(monkeypatch):
    monkeypatch.setattr(
        pipeline.llm_fallback_service,
        "extract_json",
        lambda **kwargs: {
            "title": " Backend Developer ",
            "company": " TechNova ",
            "location": " Kochi ",
            "employment_type": "Full-time",
            "department": "Engineering",
            "description": " Built APIs. ",
        },
    )

    result = pipeline._llm_experience_fallback(
        "Backend Developer at TechNova"
    )

    assert result["title"] == "Backend Developer"
    assert result["company"] == "TechNova"
    assert result["location"] == "Kochi"
    assert result["description"] == "Built APIs."


def test_llm_fallback_handles_service_exception(monkeypatch):
    def raise_error(**kwargs):
        raise ConnectionError("Ollama unavailable")

    monkeypatch.setattr(
        pipeline.llm_fallback_service,
        "extract_json",
        raise_error,
    )

    result = pipeline._llm_experience_fallback(
        "Backend Developer at TechNova"
    )

    assert result == {}


def test_llm_fallback_rejects_non_dictionary_response(monkeypatch):
    monkeypatch.setattr(
        pipeline.llm_fallback_service,
        "extract_json",
        lambda **kwargs: ["Backend Developer"],
    )

    result = pipeline._llm_experience_fallback(
        "Backend Developer at TechNova"
    )

    assert result == {}


def test_llm_fallback_handles_missing_fields(monkeypatch):
    monkeypatch.setattr(
        pipeline.llm_fallback_service,
        "extract_json",
        lambda **kwargs: {
            "title": "Backend Developer",
        },
    )

    result = pipeline._llm_experience_fallback(
        "Backend Developer at TechNova"
    )

    assert result["title"] == "Backend Developer"
    assert result["company"] is None
    assert result["location"] is None


def test_llm_fallback_handles_empty_block():
    assert pipeline._llm_experience_fallback("") == {}


def test_llm_fallback_handles_placeholder_values(monkeypatch):
    monkeypatch.setattr(
        pipeline.llm_fallback_service,
        "extract_json",
        lambda **kwargs: {
            "title": "unknown",
            "company": "None",
            "location": " n/a ",
            "employment_type": "",
            "department": "Engineering",
            "description": "Not specified",
        },
    )

    result = pipeline._llm_experience_fallback(
        "Some employment text"
    )

    assert result["title"] is None
    assert result["company"] is None
    assert result["location"] is None
    assert result["employment_type"] is None
    assert result["department"] == "Engineering"
    assert result["description"] is None


# ============================================================
# MULTIPLE BLOCKS AND PROFILING
# ============================================================

def test_multiple_experience_blocks_are_processed(monkeypatch):
    configure_deterministic_pipeline(monkeypatch)

    result = pipeline.experience_extractor(
        [
            "Software Developer at TechNova",
            "Python Developer at DataWorks",
        ],
        profile=False,
    )

    assert len(result) == 2
    assert result[0]["title"] == "Software Developer"
    assert result[1]["title"] == "Software Developer"


def test_profile_false_does_not_print(monkeypatch, capsys):
    configure_deterministic_pipeline(monkeypatch)

    pipeline.experience_extractor(
        ["Software Developer at TechNova"],
        profile=False,
    )

    captured = capsys.readouterr()

    assert captured.out == ""


def test_profile_true_prints_summary(monkeypatch, capsys):
    configure_deterministic_pipeline(monkeypatch)

    pipeline.experience_extractor(
        ["Software Developer at TechNova"],
        profile=True,
    )

    captured = capsys.readouterr()

    assert "EXPERIENCE PIPELINE PROFILE" in captured.out
    assert "Total time" in captured.out
    assert "llm_fallback" in captured.out



from document_processing.resume.entity_extracter.experience.description_extraction import (
    extract_description,
    clean_experience_description,
)


def test_removes_combined_header_from_description():
    block = [
        (
            "Backend Development Trainee - ByteBridge Learning Hub "
            "Remote Created a Django application with basic authentication "
            "and CRUD operations."
        ),
        (
            "Practiced PostgreSQL integration, Git workflows, "
            "and API testing for backend features."
        ),
    ]

    result = extract_description(
        block,
        title="Backend Development Trainee",
        company="ByteBridge Learning Hub",
        location="Remote",
    )

    assert result == [
        "Created a Django application with basic authentication and CRUD operations.",
        "Practiced PostgreSQL integration, Git workflows, and API testing for backend features.",
    ]


def test_preserves_company_name_in_responsibility():
    result = clean_experience_description(
        "Developed an integration for ByteBridge Learning Hub applications.",
        title="Backend Development Trainee",
        company="ByteBridge Learning Hub",
        location="Remote",
    )

    assert result == (
        "Developed an integration for ByteBridge Learning Hub applications."
    )


def test_removes_header_without_responsibility():
    result = clean_experience_description(
        "Backend Development Trainee - ByteBridge Learning Hub Remote",
        title="Backend Development Trainee",
        company="ByteBridge Learning Hub",
        location="Remote",
    )

    assert result == ""
