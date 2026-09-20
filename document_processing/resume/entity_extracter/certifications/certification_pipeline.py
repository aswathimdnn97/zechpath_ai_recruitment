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
    "certified",
    "passed",
    "earned",
    "obtained",
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
    print("\n================ CERTIFICATION DEBUG ================")
    print("INPUT TYPE:", type(lines))
    print("INPUT:")
    print(repr(lines))

    blocks = split_certification_blocks(lines)

    print("\nBLOCKS:")
    print(repr(blocks))
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

        # ====================================================
        # CERTIFICATION NAME
        # ====================================================

        try:
            name = extract_certification_name(block)
        except Exception:
            name = None

        if not _has_meaningful_text(name):
            continue

        name = str(name).strip()

        # ============================================================
        # ISSUING ORGANIZATION
        # ============================================================

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

            # --------------------------------------------------------
            # Prevent completion/status words from being treated
            # as issuing organizations.
            #
            # Example:
            #
            # "Professional Development Program Completed"
            #
            # Current extraction:
            #   name         = "Professional Development Program"
            #   organization = "Completed"
            #
            # Correct:
            #   name         = "Professional Development Program"
            #   organization = None
            # --------------------------------------------------------

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

