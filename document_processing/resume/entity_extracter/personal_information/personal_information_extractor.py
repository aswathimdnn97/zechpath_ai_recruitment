
import re
from urllib.parse import urlparse

from document_processing.resume.entity_extracter.personal_information.name_extractor import (
    extract_name,
)
from document_processing.resume.entity_extracter.personal_information.email_extractor import (
    extract_email,
)
from document_processing.resume.entity_extracter.personal_information.phone_extractor import (
    extract_phone,
)
from document_processing.resume.entity_extracter.personal_information.location_extractor import (
    extract_location,
)
from document_processing.resume.entity_extracter.personal_information.linkedin_extractor import (
    extract_linkedin,
)
from document_processing.resume.entity_extracter.personal_information.github_extractor import (
    extract_github,
)
from document_processing.resume.entity_extracter.personal_information.portfolio_extractor import (
    extract_portfolio,
)

from document_processing.common.llm_fallback_service import llm_fallback_service


PERSONAL_INFORMATION_LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "location": {"type": "string"},
        "linkedin": {"type": "string"},
        "github": {"type": "string"},
        "portfolio": {"type": "string"},
    },
    "required": [
        "name",
        "email",
        "phone",
        "location",
        "linkedin",
        "github",
        "portfolio",
    ],
    "additionalProperties": False,
}

PERSONAL_INFORMATION_FIELDS = (
    "name",
    "email",
    "phone",
    "location",
    "linkedin",
    "github",
    "portfolio",
)


def _clean_value(value):
    """Convert a valid non-empty string into a clean string."""

    if not isinstance(value, str):
        return None

    value = " ".join(value.split()).strip()

    if value.casefold() in {
        "",
        "none",
        "null",
        "n/a",
        "na",
        "not available",
        "unknown",
        "not provided",
    }:
        return None

    return value


def _safe_extract(extractor, text):
    """Prevent individual extractor errors from stopping the pipeline."""

    try:
        return _clean_value(extractor(text))
    except Exception:
        return None


def _is_valid_email(value):
    """Perform basic email validation."""

    if not value:
        return False

    return bool(
        re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
            r"@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+",
            value,
        )
    )


def _is_valid_phone(value):
    """Accept phone numbers containing 7 to 15 digits."""

    if not value:
        return False

    digits = re.sub(r"\D", "", value)

    return 7 <= len(digits) <= 15


def _normalize_url(value):
    """Normalize a URL for validation without inventing a domain."""

    value = _clean_value(value)

    if not value:
        return None

    candidate = value

    # Allow bare domains such as github.com/user.
    if not re.match(r"^https?://", candidate, re.IGNORECASE):
        candidate = f"https://{candidate}"

    try:
        parsed = urlparse(candidate)

        if parsed.scheme not in {"http", "https"}:
            return None

        if not parsed.hostname or "." not in parsed.hostname:
            return None

        if any(char.isspace() for char in candidate):
            return None

        return candidate

    except (ValueError, TypeError):
        return None


def _validate_field(field, value):
    """Apply field-specific validation to deterministic and LLM values."""

    value = _clean_value(value)

    if not value:
        return None

    if field == "email":
        return value if _is_valid_email(value) else None

    if field == "phone":
        return value if _is_valid_phone(value) else None

    if field in {"linkedin", "github", "portfolio"}:
        url = _normalize_url(value)

        if not url:
            return None

        hostname = urlparse(url).hostname or ""
        hostname = hostname.casefold().removeprefix("www.")

        if field == "linkedin" and not (
            hostname == "linkedin.com"
            or hostname.endswith(".linkedin.com")
        ):
            return None

        if field == "github" and not (
            hostname == "github.com"
            or hostname.endswith(".github.com")
        ):
            return None

        return url

    return value


def _llm_personal_information_fallback(text):
    """
    Ask the shared LLM service to recover missing personal fields.

    The LLM must only return information explicitly present in
    the supplied resume text. Failures return an empty dictionary.
    """

    if not isinstance(text, str) or not text.strip():
        return {}

    prompt = (
        "Extract personal contact information from the resume text.\n"
        "Only return information explicitly present in the text.\n"
        "Do not guess, infer, or invent a person's name, email, phone, "
        "location, LinkedIn URL, GitHub URL, or portfolio URL.\n"
        "Return empty strings for fields that are not present.\n"
        "Return profile links only when supported by the source text.\n\n"
        f"Resume text:\n{text}"
    )

    try:
        result = llm_fallback_service.extract_json(
            entity_name="personal_information",
            text=prompt,
            output_schema=PERSONAL_INFORMATION_LLM_SCHEMA,
        )

        if not isinstance(result, dict):
            return {}

        return {
            field: _validate_field(field, result.get(field))
            for field in PERSONAL_INFORMATION_FIELDS
        }

    except Exception:
        # LLM failure must not interrupt resume parsing.
        return {}


def extract_personal_information(text):
    """
    Extract personal information using deterministic extractors first,
    with an LLM fallback for missing or invalid fields.

    Returns the existing seven-field dictionary structure.
    """

    empty_result = {
        field: None
        for field in PERSONAL_INFORMATION_FIELDS
    }

    if not isinstance(text, str) or not text.strip():
        return empty_result

    # Step 1: Run existing deterministic extractors.
    extractors = {
        "name": extract_name,
        "email": extract_email,
        "phone": extract_phone,
        "location": extract_location,
        "linkedin": extract_linkedin,
        "github": extract_github,
        "portfolio": extract_portfolio,
    }

    result = {
        field: _validate_field(
            field,
            _safe_extract(extractor, text),
        )
        for field, extractor in extractors.items()
    }

    # Step 2: Identify missing fields.
    missing_fields = [
        field
        for field, value in result.items()
        if value is None
    ]

    # Step 3: Use LLM only if something is missing.
    if missing_fields:
        llm_result = _llm_personal_information_fallback(text)

        # Step 4: Fill missing fields only.
        for field in missing_fields:
            if result[field] is None:
                result[field] = _validate_field(
                    field,
                    llm_result.get(field),
                )

    # Step 5: Preserve the existing output contract.
    return result
