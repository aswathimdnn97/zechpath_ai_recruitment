from document_processing.resume.section_coverage import (
    needs_llm_section_fallback,
)
from document_processing.resume.section_detection_orchestrator import (
    detect_resume_sections,
)
from llm.section_classifier import (
    assignments_to_sections,
    classify_resume_sections,
    parse_assignments,
)


CLEAR_HEADING_RESUME = """
Summary
Python backend developer.

Skills
Python, FastAPI, PostgreSQL

Experience
Python Developer
CodeNest Technologies
Jan 2023 - Present
Built REST APIs.

Education
B.Tech in Computer Science
Kerala Institute of Technology
2020 - 2024
"""


HEADINGLESS_RESUME = """
Ananya Rao
ananya@example.com
Built REST APIs with FastAPI and PostgreSQL for an ATS product.
Python Developer at CodeNest Technologies from Jan 2023 to Present.
B.Tech Computer Science, Kerala Institute of Technology, 2020-2024.
Python, FastAPI, Django, SQL, Git, Docker
Recruitment matching service using resume parsing.
"""


def test_parse_assignments_drops_invalid_indices_and_sections():
    payload = {
        "assignments": [
            {"line_index": 0, "section": "experience"},
            {"line_index": 99, "section": "skills"},
            {"line_index": 1, "section": "hobbies"},
            {"section": "education"},
            {"line_index": 2, "section": "Work Experience"},
        ]
    }

    assignments = parse_assignments(payload, line_count=3)

    assert assignments == {
        0: "experience",
        2: "experience",
    }


def test_assignments_rebuild_from_original_lines_not_model_text():
    lines = [
        "Python Developer",
        "CodeNest Technologies",
        "Python, FastAPI",
    ]
    assignments = {
        0: "experience",
        1: "experience",
        2: "skills",
    }

    sections = assignments_to_sections(lines, assignments)

    assert sections["experience"] == [[
        "Python Developer",
        "CodeNest Technologies",
    ]]
    assert sections["skills"] == [["Python, FastAPI"]]


def test_classify_does_not_keep_invented_line_text():
    def fake_completer(system_prompt, user_prompt, settings=None):
        return {
            "assignments": [
                {"line_index": 0, "section": "experience"},
                {"line_index": 1, "section": "skills"},
            ]
        }

    text = "Python Developer\nPython, FastAPI\n"

    sections = classify_resume_sections(
        text,
        completer=fake_completer,
        settings=_enabled_settings(),
    )

    assert sections["experience"][0][0] == "Python Developer"
    assert "invented" not in str(sections)


def test_needs_llm_when_sections_are_empty():
    should_run, reason = needs_llm_section_fallback({}, "line one\nline two")
    assert should_run is True
    assert reason == "empty_sections"


def test_skips_llm_when_core_sections_are_present():
    sections = {
        "experience": [["Python Developer"]],
        "education": [["B.Tech"]],
        "skills": [["Python"]],
    }

    should_run, reason = needs_llm_section_fallback(
        sections,
        CLEAR_HEADING_RESUME,
    )

    assert should_run is False
    assert reason == "sufficient_regex"


def test_orchestrator_keeps_regex_for_clear_headings(monkeypatch):
    called = {"value": False}

    def fake_classify(text, settings=None):
        called["value"] = True
        return {"experience": [["should not replace"]]}

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_SECTION_DETECTION_ENABLED", "true")

    sections, meta = detect_resume_sections(
        CLEAR_HEADING_RESUME,
        classify_fn=fake_classify,
    )

    assert called["value"] is False
    assert meta["llm_used"] is False
    assert "experience" in sections
    assert "education" in sections
    assert "skills" in sections


def test_orchestrator_uses_llm_when_coverage_is_weak(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_SECTION_DETECTION_ENABLED", "true")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    monkeypatch.setattr(
        "document_processing.resume.section_detection_orchestrator.detect_sections",
        lambda text, headings_override=None: {
            "summary": [["Ananya Rao"]],
        },
    )

    def fake_classify(text, settings=None):
        return {
            "experience": [[
                "Built REST APIs with FastAPI and PostgreSQL for an ATS product.",
                "Python Developer at CodeNest Technologies from Jan 2023 to Present.",
            ]],
            "education": [[
                "B.Tech Computer Science, Kerala Institute of Technology, 2020-2024.",
            ]],
            "skills": [["Python, FastAPI, Django, SQL, Git, Docker"]],
            "projects": [[
                "Recruitment matching service using resume parsing.",
            ]],
        }

    sections, meta = detect_resume_sections(
        HEADINGLESS_RESUME,
        classify_fn=fake_classify,
    )

    assert meta["llm_used"] is True
    assert meta["method"] == "llm_fallback"
    assert meta["llm_model"] == "test-model"
    assert sections["skills"][0][0] == "Python, FastAPI, Django, SQL, Git, Docker"


def test_orchestrator_keeps_regex_when_llm_is_weaker(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_SECTION_DETECTION_ENABLED", "true")

    def fake_classify(text, settings=None):
        return {"summary": [["Ananya Rao"]]}

    sections, meta = detect_resume_sections(
        HEADINGLESS_RESUME,
        classify_fn=fake_classify,
    )

    assert meta["llm_used"] is False
    assert sections != {"summary": [["Ananya Rao"]]}


def _enabled_settings():
    from llm.config import LLMSettings

    return LLMSettings(
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        model="test-model",
        timeout_seconds=5,
        section_detection_enabled=True,
        max_section_lines=250,
    )
