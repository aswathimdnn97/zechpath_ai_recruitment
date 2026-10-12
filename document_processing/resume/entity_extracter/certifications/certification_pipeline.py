"""
certification_pipeline.py

Certification extraction pipeline.

Flow:

    certification section
            ↓
    split_certification_blocks()
            ↓
    certification_name_extractor
    organization_extractor
    certification_date_extraction
    credential_id_extractor
            ↓
    normalized certification objects
"""

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
# HELPERS
# ============================================================

def _has_meaningful_text(value):
    """
    Check whether an extracted value contains meaningful text.
    """

    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    return bool(str(value).strip())


def _normalize_certification_name(name):
    """
    Normalize a certification name without changing its meaning.

    Examples:

        Python / Domain Certification
            -> Python Domain Certification

        Python  /  Domain Certification
            -> Python Domain Certification

    The slash is treated as a visual separator, not part of the
    certification name.
    """

    if name is None:
        return None

    name = str(name).strip()

    if not name:
        return None

    # Normalize slash separators to spaces.
    name = re.sub(
        r"\s*/\s*",
        " ",
        name,
    )

    # Remove repeated whitespace.
    name = re.sub(
        r"\s+",
        " ",
        name,
    )

    return name.strip()


def _remove_certificate_heading(text):
    """
    Remove a leading certification section heading when it has
    been merged into the same physical line.

    Example:

        Certificate Python / Domain Certification Completed

    becomes:

        Python / Domain Certification Completed
    """

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


def _split_completion_marked_lines(lines):
    """
    Split certification records using completion/status markers.

    Supports both:

        [
            "Python / Domain Certification",
            "Completed",
            "Professional Development Program",
            "Completed"
        ]

    and:

        [
            "Certificate Python / Domain Certification Completed "
            "Professional Development Program Completed"
        ]

    Returns a list of logical certification blocks.

    This function is deliberately used only when completion
    markers are present, so normal certification layouts continue
    through split_certification_blocks().
    """

    if not lines:
        return []

    # Flatten nested input.
    flattened = []

    def flatten(value):
        if isinstance(value, (list, tuple)):
            for item in value:
                flatten(item)
        elif isinstance(value, str):
            value = value.strip()
            if value:
                flattened.append(value)

    flatten(lines)

    if not flattened:
        return []

    blocks = []

    for line in flattened:

        line = _remove_certificate_heading(line)

        if not line:
            continue

        # Split immediately before/after completion markers.
        #
        # Example:
        #
        # Python Certification Completed
        # Professional Development Program Completed
        #
        # becomes:
        #
        # Python Certification
        # Professional Development Program
        #
        parts = re.split(
            r"\s+\b(?:completed|complete|passed|earned|obtained|"
            r"attained|received|achieved)\b\s*",
            line,
            flags=re.IGNORECASE,
        )

        for part in parts:

            part = part.strip()

            if not part:
                continue

            # A completion marker may be followed by another
            # certification on the same physical line.
            part = _remove_certificate_heading(part)

            if part:
                blocks.append([part])

    return blocks


def _contains_completion_marker(lines):
    """
    Return True when the input contains a completion/status marker.
    """

    if not lines:
        return False

    text_parts = []

    def flatten(value):
        if isinstance(value, (list, tuple)):
            for item in value:
                flatten(item)
        elif isinstance(value, str):
            text_parts.append(value)

    flatten(lines)

    combined = " ".join(text_parts)

    return bool(
        re.search(
            r"\b(?:completed|complete|passed|earned|obtained|"
            r"attained|received|achieved)\b",
            combined,
            flags=re.IGNORECASE,
        )
    )

def _is_certification_metadata_line(line):
    """
    Return True when a line contains certification metadata
    that belongs to the current certification record.
    """

    if not isinstance(line, str):
        return False

    normalized = line.strip().lower()

    return bool(
        re.match(
            r"^(issued|issue date|issued on|expiration|expires|expiry|"
            r"expiry date|credential id|credential|certificate id)\s*:",
            normalized,
        )
    )


def _is_flat_string_list(lines):
    """
    Return True when the input is a simple list of strings.

    Example:
        [
            "AWS Certified Solutions Architect",
            "Amazon Web Services",
            "Issued: March 2024",
            "Credential ID: AWS123",
        ]

    Nested certification blocks are intentionally excluded.
    """

    return (
        isinstance(lines, list)
        and bool(lines)
        and all(isinstance(item, str) for item in lines)
    )


def _prepare_standard_certification_blocks(lines):
    """
    Preserve a standard single-certification layout as one block.

    This handles layouts such as:

        AWS Certified Solutions Architect
        Amazon Web Services
        Issued: March 2024
        Credential ID: AWS123

    The presence of certification metadata indicates that the
    preceding lines belong to the same certification record.

    Returns None when the input does not clearly match this
    standard layout, allowing the normal splitter to handle it.
    """

    if not _is_flat_string_list(lines):
        return None

    cleaned = [
        line.strip()
        for line in lines
        if isinstance(line, str) and line.strip()
    ]

    if not cleaned:
        return None

    metadata_indices = [
        index
        for index, line in enumerate(cleaned)
        if _is_certification_metadata_line(line)
    ]

    # No metadata -> let the normal splitter handle the input.
    if not metadata_indices:
        return None

    # For this layout, all metadata belongs to the same
    # immediately preceding certification record.
    #
    # Keep the complete sequence together rather than allowing
    # individual lines to become separate certification blocks.
    return [cleaned]


def _safe_date_extraction(block):
    """
    Safely extract certification dates.

    Keeps the pipeline from crashing when a certification
    does not contain a date.
    """

    try:
        result = extract_certification_date(block)
    except Exception:
        return {
            "issue_date": None,
            "expiration_date": None,
        }

    if not isinstance(result, dict):
        return {
            "issue_date": None,
            "expiration_date": None,
        }

    return {
        "issue_date": result.get("issue_date"),
        "expiration_date": result.get("expiration_date"),
    }


def _safe_credential_extraction(block):
    """
    Safely extract credential ID.
    """

    try:
        return extract_credential_id(block)
    except Exception:
        return None


# ============================================================
# MAIN PIPELINE
# ============================================================

def certification_pipeline(lines):
    """
    Extract certifications from a detected certification section.

    Input examples:

        [
            [
                "AWS Certified Solutions Architect - Associate",
                "Amazon Web Services",
                "Issued: March 2024",
                "Credential ID: AWS123"
            ]
        ]

    or:

        [
            "AWS Certified Solutions Architect - Associate",
            "Amazon Web Services",
            "Issued: March 2024"
        ]

    Returns:

        [
            {
                "certification_name": "...",
                "issuing_organization": "...",
                "issue_date": "...",
                "expiration_date": "...",
                "credential_id": "..."
            }
        ]
    """

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    if not lines:
        return []

    # ========================================================
    # STEP 1
    # Split certification section into logical blocks
    # ========================================================

    try:
        # ------------------------------------------------------------
        # Completion-marked certifications
        # ------------------------------------------------------------

        if _contains_completion_marker(lines):

            blocks = _split_completion_marked_lines(lines)

        else:

            # --------------------------------------------------------
            # Standard metadata-based certification layout
            # --------------------------------------------------------
            #
            # Example:
            #
            # AWS Certified Solutions Architect
            # Amazon Web Services
            # Issued: March 2024
            # Credential ID: AWS123
            #
            # Keep this entire record together.
            # --------------------------------------------------------

            prepared_blocks = _prepare_standard_certification_blocks(
                lines
            )

            if prepared_blocks is not None:
                blocks = prepared_blocks
            else:
                blocks = split_certification_blocks(lines)

    except Exception:
        return []

    if not blocks:
        return []

    certifications = []

    # ========================================================
    # STEP 2
    # Process every certification block
    # ========================================================

    for block in blocks:

        if not block:
            continue

        # ----------------------------------------------------
        # Ensure block is a list
        # ----------------------------------------------------

        if isinstance(block, str):
            block = [block]

        if not isinstance(block, list):
            continue

        # ----------------------------------------------------
        # Remove empty values
        # ----------------------------------------------------

        block = [
            line.strip()
            for line in block
            if isinstance(line, str)
            and line.strip()
        ]

        if not block:
            continue

        # ----------------------------------------------------
        # Remove accidental section heading from block
        # ----------------------------------------------------

        block = [
            _remove_certificate_heading(line)
            for line in block
        ]

        block = [
            line
            for line in block
            if line
        ]

        if not block:
            continue

        # ====================================================
        # CERTIFICATION NAME
        # ====================================================

        try:
            name = extract_certification_name(block)
        except Exception:
            name = None

        if not _has_meaningful_text(name):
            continue

        name = _normalize_certification_name(name)

        if not _has_meaningful_text(name):
            continue

        # ====================================================
        # ISSUING ORGANIZATION
        # ====================================================

        try:
            organization = extract_issuing_organization(
                block
            )
        except Exception:
            organization = None

        if organization is not None:

            organization = str(
                organization
            ).strip()

            if not organization:
                organization = None

            # Prevent completion/status words from being treated
            # as issuing organizations.
            if (
                organization
                and organization.lower() in COMPLETION_WORDS
            ):
                organization = None

        # ====================================================
        # DATE
        # ====================================================

        date = _safe_date_extraction(block)

        issue_date = date.get(
            "issue_date"
        )

        expiration_date = date.get(
            "expiration_date"
        )

        # ====================================================
        # CREDENTIAL ID
        # ====================================================

        credential_id = _safe_credential_extraction(
            block
        )

        if credential_id is not None:

            credential_id = str(
                credential_id
            ).strip()

            if not credential_id:
                credential_id = None

        # ====================================================
        # BUILD CERTIFICATION
        # ====================================================

        certification = {
            "certification_name": name,
            "issuing_organization": organization,
            "issue_date": issue_date,
            "expiration_date": expiration_date,
            "credential_id": credential_id,
        }

        certifications.append(
            certification
        )

    return certifications


# ============================================================
# BACKWARD-COMPATIBLE ALIAS
# ============================================================

extract_certifications = certification_pipeline