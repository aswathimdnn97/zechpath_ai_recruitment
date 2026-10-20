"""
Decide when regex section detection is too weak for downstream extractors.

The LLM fallback must not run on every resume. Clear headings stay on
the deterministic detector.
"""

from __future__ import annotations

from typing import Any


CORE_SECTIONS = (
    "experience",
    "education",
    "skills",
)


def _flatten_lines(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []

    if isinstance(value, dict):
        lines = []
        for nested in value.values():
            lines.extend(_flatten_lines(nested))
        return lines

    if isinstance(value, (list, tuple)):
        lines = []
        for nested in value:
            lines.extend(_flatten_lines(nested))
        return lines

    return []


def section_has_content(sections: dict, name: str) -> bool:
    if not isinstance(sections, dict):
        return False

    return bool(_flatten_lines(sections.get(name)))


def count_assigned_lines(sections: dict) -> int:
    if not isinstance(sections, dict):
        return 0

    return len(_flatten_lines(sections))


def count_source_lines(text: str) -> int:
    if not isinstance(text, str):
        return 0

    return sum(1 for line in text.splitlines() if line.strip())


def core_section_count(sections: dict) -> int:
    return sum(
        1
        for name in CORE_SECTIONS
        if section_has_content(sections, name)
    )


def coverage_score(sections: dict) -> tuple[int, int]:
    """
    Compare two detections.

    Higher core-section count wins. Assigned-line count is the tie-break
    so a slightly richer valid parse can replace a weaker one.
    """

    return (
        core_section_count(sections),
        count_assigned_lines(sections),
    )


def needs_llm_section_fallback(
    sections: dict,
    text: str,
) -> tuple[bool, str]:
    """
    Return (should_call_llm, reason).

    Trigger only when regex/inference missed most of the resume body.
    """

    if not isinstance(sections, dict) or not any(
        _flatten_lines(value) for value in sections.values()
    ):
        return True, "empty_sections"

    core_found = core_section_count(sections)

    if core_found >= 2:
        return False, "sufficient_regex"

    source_lines = count_source_lines(text)
    assigned_lines = count_assigned_lines(sections)

    if source_lines >= 8 and assigned_lines * 3 < source_lines:
        return True, "low_line_coverage"

    if core_found <= 1:
        return True, "missing_core_sections"

    return False, "sufficient_regex"
