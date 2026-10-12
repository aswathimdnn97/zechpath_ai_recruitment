from functools import lru_cache
from typing import Any, Dict, List
import re


# ============================================================
# Configuration: Structured Bias-Sensitive Fields
# ============================================================

BIAS_FIELD_NAMES = {
    "age": {
        "age",
        "date_of_birth",
        "date-of-birth",
        "dob",
        "birth_date",
        "birthdate",
    },
    "gender": {
        "gender",
        "sex",
    },
    "religion": {
        "religion",
        "faith",
    },
    "marital_status": {
        "marital_status",
        "marital-status",
        "marital status",
    },
    "nationality": {
        "nationality",
        "citizenship",
    },
    "photograph": {
        "photo",
        "photograph",
        "profile_photo",
        "profile-photo",
        "profile photo",
        "passport_photo",
        "passport-photo",
        "passport photo",
    },
    "full_address": {
        "full_address",
        "full-address",
        "full address",
        "home_address",
        "home-address",
        "home address",
        "residential_address",
        "residential-address",
        "residential address",
        "permanent_address",
        "permanent-address",
        "permanent address",
    },
}


# ============================================================
# Text-Based Bias Indicators
# ============================================================

BIAS_INDICATORS = {
    "age": {
        "patterns": [
            r"\bage\s*[:\-]?\s*\d{1,3}\b",
            r"\b\d{1,2}\s*(?:years?|yrs?)\s*old\b",
            r"\bdate[\s_\-]*of[\s_\-]*birth\b",
            r"\bdob\b",
        ],
        "severity": "high",
        "recommendation": (
            "Exclude age and date-of-birth information "
            "from candidate scoring."
        ),
    },
    "gender": {
        "patterns": [
            r"\bgender\b",
            r"\bsex\b",
            r"\bmale\b",
            r"\bfemale\b",
        ],
        "severity": "high",
        "recommendation": (
            "Exclude gender information from candidate scoring."
        ),
    },
    "religion": {
        "patterns": [
            r"\breligion\b",
            r"\bfaith\b",
        ],
        "severity": "high",
        "recommendation": (
            "Exclude religion-related information "
            "from candidate scoring."
        ),
    },
    "marital_status": {
        "patterns": [
            r"\bmarital[\s_\-]+status\b",
            r"\bmarried\b",
            r"\bsingle\b",
            r"\bdivorced\b",
            r"\bwidowed\b",
        ],
        "severity": "high",
        "recommendation": (
            "Exclude marital-status information "
            "from candidate scoring."
        ),
    },
    "nationality": {
        "patterns": [
            r"\bnationality\b",
            r"\bcitizenship\b",
        ],
        "severity": "high",
        "recommendation": (
            "Exclude nationality and citizenship "
            "information from candidate scoring."
        ),
    },
    "photograph": {
        "patterns": [
            r"\bphoto\b",
            r"\bphotograph\b",
            r"\bprofile[\s_\-]+photo\b",
            r"\bpassport[\s_\-]+photo\b",
        ],
        "severity": "medium",
        "recommendation": (
            "Exclude photographs from candidate scoring."
        ),
    },
    "full_address": {
        "patterns": [
            r"\bfull[\s_\-]+address\b",
            r"\bhome[\s_\-]+address\b",
            r"\bresidential[\s_\-]+address\b",
            r"\bpermanent[\s_\-]+address\b",
        ],
        "severity": "medium",
        "recommendation": (
            "Exclude detailed residential address "
            "information from candidate scoring."
        ),
    },
}


# ============================================================
# Field Name Normalization
# ============================================================

def _normalize_field_name(field_name: Any) -> str:
    """
    Normalize structured JSON field names.

    Examples:
        date_of_birth -> date_of_birth
        date-of-birth -> date_of_birth
        date of birth -> date_of_birth
    """
    if not isinstance(field_name, str):
        return ""

    value = field_name.strip().lower()
    value = value.replace("-", "_")
    value = value.replace(" ", "_")

    return value


# Precompute normalized field names once at module import.
NORMALIZED_BIAS_FIELD_NAMES = {
    indicator_name: frozenset(
        _normalize_field_name(field_name)
        for field_name in field_names
    )
    for indicator_name, field_names in BIAS_FIELD_NAMES.items()
}


# ============================================================
# Structured Field Detection
# ============================================================

def _find_bias_fields(
    profile: Any,
) -> Dict[str, List[str]]:
    """
    Find bias-sensitive fields inside nested dictionaries and lists.
    """
    found: Dict[str, List[str]] = {}

    if not isinstance(profile, dict):
        return found

    def walk(data: Any) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                normalized_key = _normalize_field_name(key)

                for indicator_name, normalized_fields in (
                    NORMALIZED_BIAS_FIELD_NAMES.items()
                ):
                    if normalized_key in normalized_fields:
                        found.setdefault(
                            indicator_name, []
                        ).append(str(key))

                walk(value)

        elif isinstance(data, list):
            for item in data:
                walk(item)

    walk(profile)

    return found


# ============================================================
# Profile -> Searchable Text
# ============================================================

def _profile_to_text(profile: Any) -> str:
    """
    Convert a structured profile into searchable text.
    """
    if not isinstance(profile, dict):
        return ""

    parts: List[str] = []

    def walk(data: Any) -> None:
        if isinstance(data, dict):
            for key, value in data.items():
                parts.append(str(key))

                if isinstance(value, (str, int, float)):
                    parts.append(str(value))
                else:
                    walk(value)

        elif isinstance(data, list):
            for item in data:
                walk(item)

        elif isinstance(data, (str, int, float)):
            parts.append(str(data))

    walk(profile)

    return " ".join(parts).lower()


# ============================================================
# Cached Regex Compilation
# ============================================================

@lru_cache(maxsize=128)
def _compile_pattern(pattern: str):
    """
    Compile a regular expression once and reuse it.

    Invalid patterns return None, matching the previous behavior
    of skipping regex errors.
    """
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return None


# ============================================================
# Regex Matching
# ============================================================

def _find_matches(
    text: str,
    patterns: List[str],
) -> List[str]:
    """
    Find regex-based bias indicators using cached patterns.
    """
    if not text:
        return []

    matches: List[str] = []

    for pattern in patterns:
        compiled_pattern = _compile_pattern(pattern)

        if compiled_pattern is None:
            continue

        found = compiled_pattern.findall(text)

        for match in found:
            if isinstance(match, tuple):
                match = " ".join(
                    str(value)
                    for value in match
                    if value
                )

            match = str(match).strip()

            if match:
                matches.append(match)

    return list(dict.fromkeys(matches))


# ============================================================
# Main Bias Detector
# ============================================================

def detect_bias_indicators(
    profile: Any,
) -> Dict[str, Any]:
    """
    Detect potentially bias-sensitive personal attributes.

    This function reports potential indicators; it does not change
    candidate scores. Candidate ID is intentionally ignored as a
    scoring attribute.
    """
    if not isinstance(profile, dict) or not profile:
        return {
            "bias_detected": False,
            "risk_level": "none",
            "indicator_count": 0,
            "indicators": [],
            "status": "no_data",
        }

    # Structured field detection.
    field_matches = _find_bias_fields(profile)

    # Text-based detection.
    text = _profile_to_text(profile)

    indicators: List[Dict[str, Any]] = []

    for indicator_name, configuration in BIAS_INDICATORS.items():
        regex_matches = _find_matches(
            text,
            configuration["patterns"],
        )

        structured_matches = field_matches.get(
            indicator_name, []
        )

        all_matches = list(
            dict.fromkeys(regex_matches + structured_matches)
        )

        if not all_matches:
            continue

        indicators.append(
            {
                "indicator": indicator_name,
                "severity": configuration["severity"],
                "matches": all_matches,
                "recommendation": configuration["recommendation"],
            }
        )

    if not indicators:
        return {
            "bias_detected": False,
            "risk_level": "none",
            "indicator_count": 0,
            "indicators": [],
            "status": "clear",
        }

    severities = {
        item["severity"]
        for item in indicators
    }

    if "high" in severities:
        risk_level = "high"
    elif "medium" in severities:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "bias_detected": True,
        "risk_level": risk_level,
        "indicator_count": len(indicators),
        "indicators": indicators,
        "status": "detected",
    }
