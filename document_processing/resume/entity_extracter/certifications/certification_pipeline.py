"""
certification_pipeline.py

Certification extraction pipeline with optional local LLM fallback.

Flow:
    certification section
            |
    split certification blocks
            |
    deterministic extraction
            |
    LLM fallback for missing fields
            |
    normalized certification objects

Existing deterministic values are preserved.
LLM failures never crash certification extraction.
"""

import logging
import re

from document_processing.resume.entity_extracter.certifications.certification_block_splitter import (
    split_certification_blocks,
)

from document_processing.resume.entity_extracter.certifications.certification_name_extractor import (
    extract_certification_name,
)

from document_processing.resume.entity_extracter.certifications.organization_extractor import (
    extract_issuing_organization,
)

from document_processing.resume.entity_extracter.certifications.certification_date_extraction import (
    extract_certification_date,
)

from document_processing.resume.entity_extracter.certifications.creditiel_id_extractor import (
    extract_credential_id,
)

from document_processing.common.llm_fallback_service import llm_fallback_service


logger = logging.getLogger(__name__)


COMPLETION_WORDS = {
    "completed",
    "complete",
    "passed",
    "earned",
    "obtained",
    "attained",
    "received",
    "achieved",
}


# ============================================================
# LLM RESPONSE SCHEMA
# ============================================================

CERTIFICATION_LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "certification_name": {"type": "string"},
        "issuing_organization": {"type": "string"},
        "issue_date": {"type": "string"},
        "expiration_date": {"type": "string"},
        "credential_id": {"type": "string"},
    },
    "required": [
        "certification_name",
        "issuing_organization",
        "issue_date",
        "expiration_date",
        "credential_id",
    ],
    "additionalProperties": False,
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def _has_meaningful_text(value):
    """Return True when a value contains meaningful text."""

    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    return bool(str(value).strip())


def _clean_llm_value(value):
    """Convert a valid, non-empty LLM string into a clean value."""

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    if value.casefold() in {
        "unknown",
        "not available",
        "not specified",
        "not provided",
        "n/a",
        "na",
        "null",
        "none",
        "unknown organization",
    }:
        return None

    return value


def _normalize_certification_name(name):
    """Normalize whitespace and slash separators in a name."""

    if name is None:
        return None

    name = str(name).strip()

    if not name:
        return None

    name = re.sub(r"\s*/\s*", " ", name)
    name = re.sub(r"\s+", " ", name)

    return name.strip() or None


def _remove_certificate_heading(text):
    """Remove a leading certification heading from a text line."""

    if not isinstance(text, str):
        return text

    text = text.strip()

    text = re.sub(
        r"^\s*certificate\s*[:\-]?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^\s*certifications?\s*[:\-]?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


def _is_completion_only_line(line):
    """Identify lines containing only a completion/status marker."""

    if not isinstance(line, str):
        return False

    return line.strip().casefold() in COMPLETION_WORDS


def _flatten_lines(value):
    """Flatten nested lists and tuples into non-empty strings."""

    flattened = []

    if isinstance(value, (list, tuple)):
        for item in value:
            flattened.extend(_flatten_lines(item))

    elif isinstance(value, str):
        value = value.strip()

        if value:
            flattened.append(value)

    return flattened


# ============================================================
# COMPLETION-MARKED BLOCK SPLITTING
# ============================================================

def _contains_completion_marker(lines):
    """Check whether the input contains a completion/status marker."""

    combined = " ".join(_flatten_lines(lines))

    return bool(
        re.search(
            r"\b(?:completed|complete|passed|earned|obtained|"
            r"attained|received|achieved)\b",
            combined,
            flags=re.IGNORECASE,
        )
    )


def _split_completion_marked_lines(lines):
    """
    Split certification records using completion markers.

    Handles completion words on separate lines and records that
    appear consecutively on the same physical line.
    """

    flattened = _flatten_lines(lines)

    if not flattened:
        return []

    blocks = []

    for line in flattened:
        line = _remove_certificate_heading(line)

        if not line or _is_completion_only_line(line):
            continue

        parts = re.split(
            r"\s+\b(?:completed|complete|passed|earned|obtained|"
            r"attained|received|achieved)\b\s*",
            line,
            flags=re.IGNORECASE,
        )

        for part in parts:
            part = _remove_certificate_heading(part)

            if not part or _is_completion_only_line(part):
                continue

            blocks.append([part])

    return blocks


# ============================================================
# METADATA-BASED BLOCK PREPARATION
# ============================================================

def _is_certification_metadata_line(line):
    """Identify a line containing certification metadata."""

    if not isinstance(line, str):
        return False

    return bool(
        re.match(
            r"^\s*(?:issued|issue date|issued on|expiration|expires|"
            r"expiry|expiry date|credential id|credential|"
            r"certificate id)\s*:",
            line,
            flags=re.IGNORECASE,
        )
    )


def _is_flat_string_list(lines):
    """Check whether input is a flat list of strings."""

    return (
        isinstance(lines, list)
        and bool(lines)
        and all(isinstance(item, str) for item in lines)
    )


def _prepare_standard_certification_blocks(lines):
    """
    Keep a single metadata-based certification record together.

    Returns None when the input should use the normal splitter.
    """

    if not _is_flat_string_list(lines):
        return None

    cleaned = [
        line.strip()
        for line in lines
        if line.strip()
    ]

    if not cleaned:
        return None

    has_metadata = any(
        _is_certification_metadata_line(line)
        for line in cleaned
    )

    if not has_metadata:
        return None

    return [cleaned]


# ============================================================
# SAFE DETERMINISTIC EXTRACTORS
# ============================================================

def _safe_date_extraction(block):
    """Extract certification dates without crashing the pipeline."""

    empty_result = {
        "issue_date": None,
        "expiration_date": None,
    }

    try:
        result = extract_certification_date(block)

    except Exception:
        logger.debug(
            "Deterministic certification date extraction failed.",
            exc_info=True,
        )
        return empty_result

    if not isinstance(result, dict):
        return empty_result

    return {
        "issue_date": result.get("issue_date"),
        "expiration_date": result.get("expiration_date"),
    }


def _safe_credential_extraction(block):
    """Extract a credential ID without crashing the pipeline."""

    try:
        return extract_credential_id(block)

    except Exception:
        logger.debug(
            "Deterministic credential ID extraction failed.",
            exc_info=True,
        )
        return None


# ============================================================
# LLM FALLBACK
# ============================================================

def _llm_certification_fallback(block):
    """
    Recover missing certification fields using the shared LLM service.

    The LLM must extract only information supported by the supplied
    text. Missing fields should be returned as empty strings.

    Returns a dictionary containing cleaned suggestions or an empty
    dictionary if the service fails or returns an invalid response.
    """

    block_text = "\n".join(_flatten_lines(block)).strip()

    if not block_text:
        return {}

    prompt_text = (
        "Extract certification information from the supplied resume "
        "text. Use only details explicitly supported by the text. "
        "Do not invent certification names, organizations, dates, "
        "or credential IDs. If a field is absent, return an empty "
        "string for that field. Preserve date wording as written "
        "in the source.\n\n"
        f"CERTIFICATION TEXT:\n{block_text}"
    )

    try:
        response = llm_fallback_service.extract_json(
            entity_name="certification",
            text=prompt_text,
            output_schema=CERTIFICATION_LLM_SCHEMA,
        )

        if not isinstance(response, dict):
            return {}

        return {
            field: _clean_llm_value(response.get(field))
            for field in CERTIFICATION_LLM_SCHEMA["properties"]
        }

    except Exception:
        logger.warning(
            "LLM certification fallback failed; preserving "
            "deterministic extraction results.",
            exc_info=True,
        )
        return {}


# ============================================================
# MAIN PIPELINE
# ============================================================

def certification_pipeline(lines):
    """
    Extract and normalize certifications from a detected resume section.

    Returns:
        [
            {
                "certification_name": str,
                "issuing_organization": str | None,
                "issue_date": str | None,
                "expiration_date": str | None,
                "credential_id": str | None,
            }
        ]
    """

    if not lines:
        return []

    # --------------------------------------------------------
    # STEP 1: SPLIT INTO LOGICAL CERTIFICATION BLOCKS
    # --------------------------------------------------------

    try:
        if _contains_completion_marker(lines):
            blocks = _split_completion_marked_lines(lines)

        else:
            prepared_blocks = _prepare_standard_certification_blocks(
                lines
            )

            if prepared_blocks is not None:
                blocks = prepared_blocks
            else:
                blocks = split_certification_blocks(lines)

    except Exception:
        logger.warning(
            "Certification block splitting failed.",
            exc_info=True,
        )
        return []

    if not blocks:
        return []

    certifications = []

    # --------------------------------------------------------
    # STEP 2: PROCESS EACH BLOCK
    # --------------------------------------------------------

    for block in blocks:
        if not block:
            continue

        if isinstance(block, str):
            block = [block]

        if not isinstance(block, (list, tuple)):
            continue

        block = [
            _remove_certificate_heading(line.strip())
            for line in block
            if isinstance(line, str) and line.strip()
        ]

        block = [
            line
            for line in block
            if line and not _is_completion_only_line(line)
        ]

        if not block:
            continue

        # ----------------------------------------------------
        # CERTIFICATION NAME - DETERMINISTIC FIRST
        # ----------------------------------------------------

        try:
            name = extract_certification_name(block)

        except Exception:
            logger.debug(
                "Deterministic certification name extraction failed.",
                exc_info=True,
            )
            name = None

        name = (
            _normalize_certification_name(name)
            if _has_meaningful_text(name)
            else None
        )

        # ----------------------------------------------------
        # ISSUING ORGANIZATION - DETERMINISTIC FIRST
        # ----------------------------------------------------

        try:
            organization = extract_issuing_organization(block)

        except Exception:
            logger.debug(
                "Deterministic issuing organization extraction failed.",
                exc_info=True,
            )
            organization = None

        organization = _clean_llm_value(
            organization
        ) if isinstance(organization, str) else organization

        if (
            isinstance(organization, str)
            and organization.casefold() in COMPLETION_WORDS
        ):
            organization = None

        # ----------------------------------------------------
        # DATES - DETERMINISTIC FIRST
        # ----------------------------------------------------

        dates = _safe_date_extraction(block)

        issue_date = dates["issue_date"]
        expiration_date = dates["expiration_date"]

        # ----------------------------------------------------
        # CREDENTIAL ID - DETERMINISTIC FIRST
        # ----------------------------------------------------

        credential_id = _safe_credential_extraction(block)

        if isinstance(credential_id, str):
            credential_id = credential_id.strip() or None

        # ----------------------------------------------------
        # STEP 3: CALL LLM ONLY IF A FIELD IS MISSING
        # ----------------------------------------------------

        missing_fields = (
            not _has_meaningful_text(name)
            or not _has_meaningful_text(organization)
            or not _has_meaningful_text(issue_date)
            or not _has_meaningful_text(expiration_date)
            or not _has_meaningful_text(credential_id)
        )

        if missing_fields:
            suggestions = _llm_certification_fallback(block)

            # Fill only missing values. Preserve deterministic results.
            if not _has_meaningful_text(name):
                name = _normalize_certification_name(
                    suggestions.get("certification_name")
                )

            if not _has_meaningful_text(organization):
                organization = suggestions.get("issuing_organization")

            if not _has_meaningful_text(issue_date):
                issue_date = suggestions.get("issue_date")

            if not _has_meaningful_text(expiration_date):
                expiration_date = suggestions.get("expiration_date")

            if not _has_meaningful_text(credential_id):
                credential_id = suggestions.get("credential_id")

        # ----------------------------------------------------
        # STEP 4: SKIP ONLY IF NAME REMAINS MISSING
        # ----------------------------------------------------

        if not _has_meaningful_text(name):
            logger.debug(
                "Skipping certification block because its name "
                "could not be extracted: %r",
                block,
            )
            continue

        # ----------------------------------------------------
        # STEP 5: BUILD NORMALIZED CERTIFICATION OBJECT
        # ----------------------------------------------------

        certifications.append({
            "certification_name": name,
            "issuing_organization": organization,
            "issue_date": issue_date,
            "expiration_date": expiration_date,
            "credential_id": credential_id,
        })

    return certifications


# ============================================================
# BACKWARD-COMPATIBLE ALIAS
# ============================================================

extract_certifications = certification_pipeline
