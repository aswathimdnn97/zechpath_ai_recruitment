"""
Tests for the ZechPath skill extraction orchestrator.

Run:
    pytest -q tests/test_skill_extractor.py
"""

import pytest

from document_processing.resume.entity_extracter.skill import (
    skill_extractor as skill_module,
)


# ============================================================
# TEST HELPERS
# ============================================================

def make_candidate(
    skill,
    source_section="skills",
    source_text=None,
    skill_id=None,
):
    """Build a representative skill candidate."""

    candidate = {
        "skill": skill,
        "source_section": source_section,
        "source_text": source_text or skill,
        "extraction_method": "test",
        "sources": [
            {
                "source_section": source_section,
                "source_text": source_text or skill,
                "source_skill": skill,
            }
        ],
    }

    if skill_id is not None:
        candidate["skill_id"] = skill_id

    return candidate


def configure_deterministic_pipeline(
    monkeypatch,
    candidates=None,
    validated=None,
    expanded=None,
):
    """Mock deterministic dependencies for isolated orchestrator tests."""

    candidates = candidates if candidates is not None else []
    validated = validated if validated is not None else candidates
    expanded = expanded if expanded is not None else validated

    monkeypatch.setattr(
        skill_module,
        "_collect_candidates",
        lambda sections, profile=False: candidates,
    )

    monkeypatch.setattr(
        skill_module,
        "resolve_spelling",
        lambda items: items,
    )

    monkeypatch.setattr(
        skill_module,
        "resolve_synonyms",
        lambda items: items,
    )

    monkeypatch.setattr(
        skill_module,
        "validate_skills",
        lambda items: validated,
    )

    monkeypatch.setattr(
        skill_module,
        "expand_skill_stacks",
        lambda items: expanded,
    )

def configure_llm_fallback_pipeline(monkeypatch):
    """Keep deterministic extraction empty but allow LLM results through."""

    configure_deterministic_pipeline(
        monkeypatch,
        candidates=[],
    )

    # Allow LLM candidates to pass through the resolver stages.
    monkeypatch.setattr(
        skill_module,
        "resolve_spelling",
        lambda items: items,
    )

    monkeypatch.setattr(
        skill_module,
        "resolve_synonyms",
        lambda items: items,
    )

    monkeypatch.setattr(
        skill_module,
        "expand_skill_stacks",
        lambda items: items,
    )

    # Default to accepting candidates in this test.
    monkeypatch.setattr(
        skill_module,
        "validate_skills",
        lambda items: items,
    )
# ============================================================
# INPUT VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "sections",
    [
        None,
        "",
        [],
        (),
        123,
    ],
)
def test_invalid_sections_return_empty_list(sections):
    assert skill_module.extract_skill(sections) == []


def test_empty_sections_return_empty_list():
    assert skill_module.extract_skill({}) == []


# ============================================================
# SECTION COLLECTION
# ============================================================

def test_collect_candidates_from_skills_section(monkeypatch):
    """Dedicated Skills section uses the skill line splitter."""

    monkeypatch.setattr(
        skill_module,
        "split_skill_line",
        lambda lines: ["Python", "Django", "PostgreSQL"],
    )

    sections = {
        "skills": "Python, Django, PostgreSQL",
    }

    candidates = skill_module._collect_candidates(sections)

    assert [item["skill"] for item in candidates] == [
        "Python",
        "Django",
        "PostgreSQL",
    ]

    assert all(
        item["source_section"] == "skills"
        for item in candidates
    )


def test_collect_candidates_from_prose_sections(monkeypatch):
    """Summary, Experience, and Projects use prose extraction."""

    def fake_extract(section_name, section_block):
        return [
            {
                "skill": "Python",
                "source_text": section_block,
            }
        ]

    monkeypatch.setattr(
        skill_module,
        "extract_skills_from_section",
        fake_extract,
    )

    sections = {
        "summary": "Experienced in Python",
        "experience": "Developed Python applications",
        "projects": "Built a Python project",
    }

    candidates = skill_module._collect_candidates(sections)

    assert len(candidates) == 3

    assert {
        item["source_section"]
        for item in candidates
    } == {
        "summary",
        "experience",
        "projects",
    }


def test_ignored_sections_are_not_processed(monkeypatch):
    """Personal and nontechnical sections must not generate skills."""

    def unexpected_extraction(**kwargs):
        pytest.fail("Ignored section reached prose extraction")

    monkeypatch.setattr(
        skill_module,
        "extract_skills_from_section",
        unexpected_extraction,
    )

    sections = {
        "personal_information": "Python",
        "languages": "Python",
        "interests": "Python",
        "references": "Python",
        "declaration": "Python",
    }

    candidates = skill_module._collect_candidates(sections)

    assert candidates == []


def test_unknown_section_is_ignored(monkeypatch):
    monkeypatch.setattr(
        skill_module,
        "extract_skills_from_section",
        lambda **kwargs: pytest.fail(
            "Unknown section should not be processed"
        ),
    )

    candidates = skill_module._collect_candidates(
        {"hobbies": "Python"}
    )

    assert candidates == []


# ============================================================
# RAW CANDIDATE DEDUPLICATION
# ============================================================

def test_raw_candidates_are_deduplicated_case_insensitively():
    candidates = [
        make_candidate(
            "Python",
            source_section="skills",
            source_text="Python",
        ),
        make_candidate(
            "python",
            source_section="experience",
            source_text="Used python in a project",
        ),
        make_candidate(
            "PYTHON",
            source_section="projects",
            source_text="Python project",
        ),
    ]

    result = skill_module._deduplicate_candidates(candidates)

    assert len(result) == 1
    assert result[0]["skill"] == "Python"

    assert set(result[0]["source_sections"]) == {
        "skills",
        "experience",
        "projects",
    }

    assert len(result[0]["sources"]) == 3


def test_invalid_raw_candidates_are_skipped():
    candidates = [
        None,
        {},
        {"skill": None},
        {"skill": ""},
        {"skill": 123},
        make_candidate("Python"),
    ]

    result = skill_module._deduplicate_candidates(candidates)

    assert len(result) == 1
    assert result[0]["skill"] == "Python"


# ============================================================
# FINAL SKILL DEDUPLICATION
# ============================================================

def test_final_skills_are_deduplicated_by_name():
    skills = [
        make_candidate("Python"),
        make_candidate("python", source_section="experience"),
    ]

    result = skill_module._deduplicate_final_skills(skills)

    assert len(result) == 1
    assert result[0]["skill"] == "Python"


def test_final_skills_are_deduplicated_by_skill_id():
    skills = [
        {
            "skill": "Python",
            "skill_id": "TECH001",
            "sources": [],
        },
        {
            "skill": "Python Programming",
            "skill_id": "TECH001",
            "sources": [],
        },
    ]

    result = skill_module._deduplicate_final_skills(skills)

    assert len(result) == 1


# ============================================================
# DETERMINISTIC EXTRACTION PIPELINE
# ============================================================

def test_deterministic_pipeline_returns_validated_skills(monkeypatch):
    """Valid deterministic results should bypass the LLM."""

    candidates = [
        make_candidate("Python"),
        make_candidate("Django"),
    ]

    configure_deterministic_pipeline(
        monkeypatch,
        candidates=candidates,
    )

    def unexpected_llm_call(**kwargs):
        pytest.fail("LLM must not run when deterministic extraction succeeds")

    monkeypatch.setattr(
        skill_module.llm_fallback_service,
        "extract_json",
        unexpected_llm_call,
    )

    result = skill_module.extract_skill(
        {"skills": "Python, Django"}
    )

    assert {item["skill"] for item in result} == {
        "Python",
        "Django",
    }


def test_spelling_and_synonym_resolvers_are_called(monkeypatch):
    candidates = [make_candidate("pyhton")]
    calls = []

    monkeypatch.setattr(
        skill_module,
        "_collect_candidates",
        lambda sections, profile=False: candidates,
    )

    def spelling(items):
        calls.append("spelling")
        return items

    def synonyms(items):
        calls.append("synonyms")
        return items

    monkeypatch.setattr(skill_module, "resolve_spelling", spelling)
    monkeypatch.setattr(skill_module, "resolve_synonyms", synonyms)
    monkeypatch.setattr(
        skill_module,
        "validate_skills",
        lambda items: items,
    )
    monkeypatch.setattr(
        skill_module,
        "expand_skill_stacks",
        lambda items: items,
    )

    skill_module.extract_skill({"skills": "pyhton"})

    assert calls == ["spelling", "synonyms"]


def test_master_validation_rejects_all_candidates(monkeypatch):
    """No validated skills should trigger the LLM fallback."""

    configure_deterministic_pipeline(
        monkeypatch,
        candidates=[make_candidate("UnrecognizedSkill")],
        validated=[],
        expanded=[],
    )

    monkeypatch.setattr(
        skill_module.llm_fallback_service,
        "extract_json",
        lambda **kwargs: {"skills": []},
    )

    result = skill_module.extract_skill(
        {"skills": "UnrecognizedSkill"}
    )

    assert result == []


# ============================================================
# LLM FALLBACK
# ============================================================

def test_llm_fallback_runs_when_no_raw_candidates(monkeypatch):
    """Fallback should run when deterministic extraction finds nothing."""

    configure_llm_fallback_pipeline(monkeypatch)

    monkeypatch.setattr(
        skill_module.llm_fallback_service,
        "extract_json",
        lambda **kwargs: {
            "skills": ["Python", "Django"]
        },
    )

    result = skill_module.extract_skill(
        {
            "summary": "Worked on web applications using Python",
        }
    )

    assert {item["skill"] for item in result} == {
        "Python",
        "Django",
    }


def test_llm_fallback_suggestions_are_validated(monkeypatch):
    """LLM suggestions must pass the master skill validator."""

    configure_deterministic_pipeline(monkeypatch, candidates=[])

    monkeypatch.setattr(
        skill_module.llm_fallback_service,
        "extract_json",
        lambda **kwargs: {
            "skills": ["Python", "UnknownTechnology"]
        },
    )

    monkeypatch.setattr(
        skill_module,
        "validate_skills",
        lambda items: [
            item
            for item in items
            if item["skill"] == "Python"
        ],
    )

    result = skill_module.extract_skill(
        {"summary": "Python and an unknown technology"}
    )

    assert [item["skill"] for item in result] == ["Python"]


def test_llm_fallback_rejects_malformed_skills_response(monkeypatch):
    configure_deterministic_pipeline(monkeypatch, candidates=[])

    monkeypatch.setattr(
        skill_module.llm_fallback_service,
        "extract_json",
        lambda **kwargs: {"skills": "Python"},
    )

    result = skill_module.extract_skill(
        {"summary": "Python developer"}
    )

    assert result == []


@pytest.mark.parametrize(
    "llm_result",
    [
        None,
        {},
        {"unexpected": ["Python"]},
        {"skills": None},
        {"skills": [None, 123, "", "   "]},
    ],
)
def test_invalid_llm_results_return_empty_list(
    monkeypatch,
    llm_result,
):
    configure_deterministic_pipeline(monkeypatch, candidates=[])

    monkeypatch.setattr(
        skill_module.llm_fallback_service,
        "extract_json",
        lambda **kwargs: llm_result,
    )

    result = skill_module.extract_skill(
        {"summary": "Python developer"}
    )

    assert result == []


def test_llm_fallback_exception_from_validator_is_handled(monkeypatch):
    """An LLM suggestion processing error should not crash extraction."""

    configure_deterministic_pipeline(monkeypatch, candidates=[])

    monkeypatch.setattr(
        skill_module.llm_fallback_service,
        "extract_json",
        lambda **kwargs: {"skills": ["Python"]},
    )

    def failing_validator(items):
        raise ValueError("Simulated validator failure")

    monkeypatch.setattr(
        skill_module,
        "validate_skills",
        failing_validator,
    )

    result = skill_module.extract_skill(
        {"summary": "Python developer"}
    )

    assert result == []


# ============================================================
# PROFILING
# ============================================================

def test_profile_flag_does_not_change_extraction_result(monkeypatch):
    candidates = [make_candidate("Python")]

    configure_deterministic_pipeline(
        monkeypatch,
        candidates=candidates,
    )

    normal_result = skill_module.extract_skill(
        {"skills": "Python"},
        profile=False,
    )

    profile_result = skill_module.extract_skill(
        {"skills": "Python"},
        profile=True,
    )

    assert [item["skill"] for item in normal_result] == [
        item["skill"] for item in profile_result
    ]
