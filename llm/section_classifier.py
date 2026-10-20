"""
LLM resume section classifier.

The model only proposes line-to-section assignments. Content is always
taken from the original resume lines so the model cannot invent text.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from document_processing.resume.headings import headings
from llm.client import LLMClientError, complete_json
from llm.config import LLMSettings, load_llm_settings


logger = logging.getLogger(__name__)

ALLOWED_SECTIONS = frozenset(headings)

SYSTEM_PROMPT = """You classify resume lines into canonical sections.

Return JSON only, with this shape:
{"assignments": [{"line_index": 0, "section": "experience"}]}

Rules:
- Use only these section names: summary, skills, education, experience, projects, certifications, achievements, languages, interests, references, activities, declaration, publications.
- line_index must be an integer copied from the numbered input. Do not invent indices.
- Assign a line to at most one section.
- Do not rewrite line text.
- Skip contact/header lines (name, email, phone, LinkedIn, address) by omitting them.
- Skill subsection labels such as Backend or Languages that appear under a skills list belong to skills.
- If unsure, omit the line.
"""


def _split_non_empty_lines(text: str) -> list[str]:
    if not isinstance(text, str):
        return []

    return [
        line.strip()
        for line in text.splitlines()
        if isinstance(line, str) and line.strip()
    ]


def _build_user_prompt(lines: list[str]) -> str:
    numbered = [
        f"{index}: {line}"
        for index, line in enumerate(lines)
    ]
    return "Classify these resume lines:\n" + "\n".join(numbered)


def _normalize_section_name(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None

    normalized = " ".join(value.strip().lower().split())

    if normalized in ALLOWED_SECTIONS:
        return normalized

    aliases = {
        "work experience": "experience",
        "professional experience": "experience",
        "employment": "experience",
        "skill": "skills",
        "technical skills": "skills",
        "education and qualifications": "education",
        "certificate": "certifications",
        "certification": "certifications",
        "project": "projects",
        "objective": "summary",
        "profile": "summary",
    }

    return aliases.get(normalized)


def parse_assignments(
    payload: dict[str, Any],
    line_count: int,
) -> dict[int, str]:
    """
    Convert model JSON into {line_index: canonical_section}.

    Invalid indices and unknown sections are dropped.
    """

    assignments: dict[int, str] = {}

    raw_assignments = payload.get("assignments")

    if not isinstance(raw_assignments, list):
        return assignments

    for item in raw_assignments:
        if not isinstance(item, dict):
            continue

        index = item.get("line_index", item.get("index"))

        try:
            index = int(index)
        except (TypeError, ValueError):
            continue

        if index < 0 or index >= line_count:
            continue

        section = _normalize_section_name(item.get("section"))

        if not section:
            continue

        assignments[index] = section

    return assignments


def assignments_to_sections(
    lines: list[str],
    assignments: dict[int, str],
) -> dict[str, list[list[str]]]:
    """
    Rebuild detector-shaped sections from original lines.

    Non-contiguous runs of the same section start a new block,
    matching the regex detector's block list format.
    """

    sections: dict[str, list[list[str]]] = {}
    current_section = None

    for index, line in enumerate(lines):
        section = assignments.get(index)

        if not section:
            continue

        if section != current_section:
            sections.setdefault(section, []).append([])
            current_section = section

        sections[section][-1].append(line)

    return sections


def classify_resume_sections(
    text: str,
    settings: Optional[LLMSettings] = None,
    completer: Optional[Callable[..., dict[str, Any]]] = None,
) -> dict[str, list[list[str]]]:
    """
    Ask the LLM to label lines, then rebuild sections from source text.

    Returns {} when the model is unavailable or produces nothing valid.
    """

    resolved = settings or load_llm_settings()

    if not resolved.section_detection_enabled or not resolved.is_ready():
        return {}

    lines = _split_non_empty_lines(text)

    if not lines:
        return {}

    if len(lines) > resolved.max_section_lines:
        lines = lines[: resolved.max_section_lines]

    request_fn = completer or complete_json

    try:
        payload = request_fn(
            SYSTEM_PROMPT,
            _build_user_prompt(lines),
            resolved,
        )
    except TypeError:
        payload = request_fn(
            SYSTEM_PROMPT,
            _build_user_prompt(lines),
        )
    except LLMClientError:
        logger.warning("LLM section classification failed; keeping regex sections.")
        return {}
    except Exception:
        logger.warning("Unexpected LLM section classification error.")
        return {}

    if not isinstance(payload, dict):
        return {}

    assignments = parse_assignments(payload, len(lines))

    if not assignments:
        return {}

    return assignments_to_sections(lines, assignments)
