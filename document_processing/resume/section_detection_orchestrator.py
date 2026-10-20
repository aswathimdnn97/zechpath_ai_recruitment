"""
Section-detection orchestration.

Order
-----
1. Deterministic heading detector on normalized text.
2. Deterministic detector on cleaned text if primary is empty.
3. Optional LLM line classifier when coverage is still weak.
4. Keep regex output unless the LLM result scores higher.

The LLM never becomes the default path for resumes with clear headings.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from document_processing.resume.headings import headings
from document_processing.resume.section_coverage import (
    coverage_score,
    needs_llm_section_fallback,
)
from document_processing.resume.section_detector import detect_sections
from llm.config import load_llm_settings
from llm.section_classifier import classify_resume_sections


logger = logging.getLogger(__name__)


def detect_resume_sections(
    normalized_text: str,
    cleaned_text: str | None = None,
    headings_override=None,
    classify_fn: Optional[Callable[..., dict]] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Run regex detection, then an optional grounded LLM fallback.

    Returns
    -------
    sections, metadata
    """

    active_headings = headings_override if headings_override is not None else headings

    sections = detect_sections(
        normalized_text,
        active_headings,
    )

    if not isinstance(sections, dict):
        sections = {}

    method = "regex"
    llm_reason = None
    llm_used = False

    if not sections or not any(sections.values()):
        fallback_text = cleaned_text if cleaned_text else normalized_text
        fallback_sections = detect_sections(
            fallback_text,
            active_headings,
        )

        if isinstance(fallback_sections, dict) and fallback_sections:
            sections = fallback_sections
            method = "regex_cleaned_fallback"

    source_text = normalized_text or cleaned_text or ""
    should_use_llm, llm_reason = needs_llm_section_fallback(
        sections,
        source_text,
    )

    metadata = {
        "method": method,
        "llm_used": False,
        "llm_reason": llm_reason if should_use_llm else None,
        "llm_model": None,
    }

    if not should_use_llm:
        return sections, metadata

    settings = load_llm_settings()

    if not settings.section_detection_enabled or not settings.is_ready():
        metadata["llm_reason"] = "llm_disabled_or_unconfigured"
        return sections, metadata

    classifier = classify_fn or classify_resume_sections

    try:
        llm_sections = classifier(
            source_text,
            settings=settings,
        )
    except TypeError:
        llm_sections = classifier(source_text)
    except Exception:
        logger.warning(
            "LLM section fallback raised; keeping regex sections."
        )
        metadata["llm_reason"] = "llm_error"
        return sections, metadata

    if not isinstance(llm_sections, dict) or not llm_sections:
        metadata["llm_reason"] = llm_reason
        metadata["llm_model"] = settings.model
        return sections, metadata

    if coverage_score(llm_sections) > coverage_score(sections):
        llm_used = True
        method = "llm_fallback"
        sections = llm_sections

    metadata = {
        "method": method,
        "llm_used": llm_used,
        "llm_reason": llm_reason,
        "llm_model": settings.model,
    }

    return sections, metadata
