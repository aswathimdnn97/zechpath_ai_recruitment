from pathlib import Path
import hashlib
import json
import logging
import re
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


BASE_DIR = Path(__file__).resolve().parents[2]

CANDIDATE_STORAGE_DIR = (
    BASE_DIR
    / "data"
    / "candidates"
    / "candidate_profile"
)


# ============================================================
# HASH
# ============================================================

def calculate_resume_hash(resume_path: Path) -> str:
    """
    Calculate SHA-256 hash of the complete resume file.

    Used for exact-file duplicate detection.
    """
    sha256 = hashlib.sha256()

    with resume_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip().lower(),
    )


def _normalize_email(value: Any) -> str:
    return _normalize_text(value)


def _normalize_phone(value: Any) -> str:
    """
    Keep digits only so formatting differences do not prevent
    duplicate detection.

    Example:
        +91 98765 43210
        +91-98765-43210

    become the same normalized value.
    """
    if value is None:
        return ""

    return re.sub(r"\D", "", str(value))


def _normalize_linkedin(value: Any) -> str:
    value = _normalize_text(value)

    value = re.sub(
        r"^https?://",
        "",
        value,
    )

    value = re.sub(
        r"^www\.",
        "",
        value,
    )

    return value.rstrip("/")


# ============================================================
# VALUE EXTRACTION
# ============================================================

def _find_value(
    data: Any,
    keys: set[str],
) -> Optional[Any]:
    """
    Recursively search a parsed candidate dictionary for a
    value whose key matches one of the supplied keys.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            normalized_key = (
                str(key).strip().lower().replace("-", "_").replace(" ", "_")
            )

            if normalized_key in keys and value not in (None, "", []):
                return value

            result = _find_value(value, keys)

            if result not in (None, "", []):
                return result

    elif isinstance(data, list):
        for item in data:
            result = _find_value(item, keys)

            if result not in (None, "", []):
                return result

    return None


def extract_identity_fields(
    candidate_data: Dict[str, Any],
) -> Dict[str, str]:
    """
    Extract identity fields from the structured candidate profile.

    The extraction is recursive so it works with nested structures
    such as:

        personal_information:
            email
            phone
            linkedin
    """

    email = _find_value(
        candidate_data,
        {
            "email",
            "email_address",
            "email_id",
        },
    )

    phone = _find_value(
        candidate_data,
        {
            "phone",
            "phone_number",
            "mobile",
            "mobile_number",
            "contact_number",
        },
    )

    linkedin = _find_value(
        candidate_data,
        {
            "linkedin",
            "linkedin_url",
            "linkedin_profile",
            "linkedin_profile_url",
        },
    )

    return {
        "email": _normalize_email(email),
        "phone": _normalize_phone(phone),
        "linkedin": _normalize_linkedin(linkedin),
    }


# ============================================================
# CANDIDATE PROFILE ITERATION
# ============================================================

def _iter_candidate_profiles():
    if not CANDIDATE_STORAGE_DIR.exists():
        return

    for candidate_file in CANDIDATE_STORAGE_DIR.glob("*.json"):
        try:
            with candidate_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                candidate_data = json.load(file)

            if isinstance(candidate_data, dict):
                yield candidate_file, candidate_data

        except Exception:
            logger.exception(
                "Failed to read candidate profile: path=%s",
                candidate_file,
            )


# ============================================================
# EXACT HASH DUPLICATE
# ============================================================

def find_duplicate_by_hash(
    resume_hash: str,
) -> Optional[Dict[str, Any]]:
    """
    Search candidate profiles for an exact resume hash.

    Returns:
        {
            "candidate_id": "...",
            "candidate_file": "...",
            "match_type": "EXACT_HASH"
        }

    or None when no match exists.
    """
    if not resume_hash:
        return None

    for candidate_file, candidate_data in _iter_candidate_profiles():
        stored_hash = _normalize_text(
            candidate_data.get("resume_hash")
        )

        if stored_hash and stored_hash == resume_hash.lower():
            candidate_id = candidate_data.get("candidate_id")

            if candidate_id:
                return {
                    "candidate_id": candidate_id,
                    "candidate_file": str(candidate_file),
                    "match_type": "EXACT_HASH",
                }

    return None


# ============================================================
# IDENTITY DUPLICATE
# ============================================================

def find_duplicate_by_identity(
    candidate_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Find an existing candidate using identity fields.

    Matching policy:
      - Email is the strongest identifier.
      - LinkedIn is a strong identifier.
      - Phone is a strong identifier.
      - A duplicate is returned when at least one strong,
        non-empty identity field matches an existing candidate.

    Name alone is intentionally NOT used because names can collide.
    """

    identity = extract_identity_fields(candidate_data)

    if not any(identity.values()):
        logger.info(
            "No usable identity fields found for duplicate check."
        )
        return None

    for candidate_file, existing_candidate in _iter_candidate_profiles():
        existing_identity = extract_identity_fields(
            existing_candidate
        )

        matched_fields = []

        if (
            identity["email"]
            and existing_identity["email"]
            and identity["email"] == existing_identity["email"]
        ):
            matched_fields.append("email")

        if (
            identity["phone"]
            and existing_identity["phone"]
            and identity["phone"] == existing_identity["phone"]
        ):
            matched_fields.append("phone")

        if (
            identity["linkedin"]
            and existing_identity["linkedin"]
            and identity["linkedin"] == existing_identity["linkedin"]
        ):
            matched_fields.append("linkedin")

        if matched_fields:
            candidate_id = existing_candidate.get("candidate_id")

            if candidate_id:
                return {
                    "candidate_id": candidate_id,
                    "candidate_file": str(candidate_file),
                    "match_type": "IDENTITY",
                    "matched_fields": matched_fields,
                }

    return None


# ============================================================
# COMBINED DUPLICATE CHECK
# ============================================================

def find_duplicate_candidate(
    resume_hash: str,
    candidate_data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Perform duplicate detection in the correct order:

        1. Exact file hash
        2. Identity fields

    This allows an unchanged resume and a modified resume from
    the same candidate to resolve to the same candidate_id.
    """

    hash_match = find_duplicate_by_hash(resume_hash)

    if hash_match:
        logger.info(
            "Exact resume duplicate found: candidate_id=%s",
            hash_match["candidate_id"],
        )
        return hash_match

    if candidate_data:
        identity_match = find_duplicate_by_identity(
            candidate_data
        )

        if identity_match:
            logger.info(
                "Modified resume duplicate found: "
                "candidate_id=%s matched_fields=%s",
                identity_match["candidate_id"],
                identity_match["matched_fields"],
            )
            return identity_match

    return None
