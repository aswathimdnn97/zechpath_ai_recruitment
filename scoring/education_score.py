import re
from typing import Any, Dict, List


DEGREE_ALIASES = {
    "bachelor of technology": "bachelor",
    "bachelor of engineering": "bachelor",
    "master of computer applications": "master",
    "master of science": "master",

    "b.tech": "bachelor",
    "btech": "bachelor",
    "b.e": "bachelor",
    "be": "bachelor",

    "mca": "master",
    "m.sc": "master",
    "msc": "master",

    "bachelor": "bachelor",
    "bachelor's": "bachelor",
    "master": "master",
}


FIELD_ALIASES = {
    "computer science": [
        "computer science",
        "computer science and engineering",
        "cse",
    ],
    "information technology": [
        "information technology",
        "it",
    ],
    "electronics": [
        "electronics",
        "electronics and communication",
        "electronics and communication engineering",
        "ece",
    ],
    "electrical": [
        "electrical",
        "electrical engineering",
    ],
    "software engineering": [
        "software engineering",
    ],
    "information systems": [
        "information systems",
    ],
}


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = value.lower()
    value = re.sub(r"[^\w\s.]", " ", value)

    return " ".join(value.split())


def _contains_term(text: str, term: str) -> bool:
    """
    Avoid substring false positives for short aliases
    such as 'it'.

    Multi-word aliases use phrase matching.
    Single-word aliases use token matching.
    """

    text = normalize_text(text)
    term = normalize_text(term)

    if not text or not term:
        return False

    if " " in term:
        return term in text

    return term in set(text.split())


def detect_degree_level(text: str) -> str:
    text = normalize_text(text)

    # Check longer/specific aliases first.
    for alias in sorted(
        DEGREE_ALIASES,
        key=len,
        reverse=True,
    ):
        if _contains_term(text, alias):
            return DEGREE_ALIASES[alias]

    return ""


def _extract_candidate_education(
    candidate_profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extract candidate education from either:

        {
            "education": [...]
        }

    or:

        {
            "resume_text": {
                "education": [...]
            }
        }
    """

    if not isinstance(candidate_profile, dict):
        return []

    # First try the top-level structure.
    education = candidate_profile.get("education")

    if isinstance(education, list):
        return education

    # Then support the actual profile structure used
    # by the scoring tests.
    resume_text = candidate_profile.get("resume_text")

    if isinstance(resume_text, dict):
        education = resume_text.get("education")

        if isinstance(education, list):
            return education

    return []


def _extract_jd_education(
    jd_profile: Dict[str, Any],
) -> List[str]:
    """
    Extract JD education from either:

        {
            "education": [...]
        }

    or:

        {
            "resume_text": {
                "education": [...]
            }
        }
    """

    if not isinstance(jd_profile, dict):
        return []

    resume_text = jd_profile.get("resume_text")

    if isinstance(resume_text, dict):
        education = resume_text.get("education")

        if isinstance(education, list):
            return education

    education = jd_profile.get("education")

    if isinstance(education, list):
        return education

    return []


def _education_to_text(
    education: Dict[str, Any],
) -> str:

    if not isinstance(education, dict):
        return ""

    values = []

    for value in education.values():

        if value is None:
            continue

        if isinstance(value, (list, tuple)):
            values.extend(
                str(item)
                for item in value
            )

        elif isinstance(value, dict):
            values.extend(
                str(item)
                for item in value.values()
            )

        else:
            values.append(str(value))

    return " ".join(values)


def calculate_degree_score(
    candidate_education: str,
    jd_education: List[str],
) -> float:

    # No education requirement in JD.
    if not jd_education:
        return 100.0

    candidate_level = detect_degree_level(
        candidate_education
    )

    if not candidate_level:
        return 0.0

    required_levels = set()

    for requirement in jd_education:

        level = detect_degree_level(
            requirement
        )

        if level:
            required_levels.add(level)

    # JD education text exists but no recognizable
    # degree level was found.
    if not required_levels:
        return 100.0

    if candidate_level in required_levels:
        return 100.0

    # Candidate has a degree, but degree level
    # does not match the JD.
    return 40.0


def calculate_field_score(
    candidate_education: str,
    jd_education: List[str],
) -> float:

    # No education requirement in JD.
    if not jd_education:
        return 100.0

    if not candidate_education:
        return 0.0

    for canonical_field, aliases in FIELD_ALIASES.items():

        candidate_has_field = any(
            _contains_term(
                candidate_education,
                alias,
            )
            for alias in aliases
        )

        if not candidate_has_field:
            continue

        for requirement in jd_education:

            requirement_has_field = any(
                _contains_term(
                    requirement,
                    alias,
                )
                for alias in aliases
            )

            if requirement_has_field:
                return 100.0

    # Candidate has an education record but
    # field does not match.
    return 40.0


def calculate_education_score(
    candidate_profile: Dict[str, Any],
    jd_profile: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(candidate_profile, dict):
        candidate_profile = {}

    if not isinstance(jd_profile, dict):
        jd_profile = {}

    # --------------------------------------------------------
    # Extract candidate education
    # --------------------------------------------------------

    candidate_education_records = (
        _extract_candidate_education(
            candidate_profile
        )
    )

    # --------------------------------------------------------
    # Extract JD education
    # --------------------------------------------------------

    jd_education = _extract_jd_education(
        jd_profile
    )

    # --------------------------------------------------------
    # Candidate has no education
    # --------------------------------------------------------

    if not candidate_education_records:
        return {
            "score": 0.0,
            "weight": 0.10,
            "degree_score": 0.0,
            "field_score": 0.0,
            "candidate_education": [],
            "required_education": jd_education,
            "status": (
                "not_required"
                if not jd_education
                else "no_data"
            ),
        }

    # --------------------------------------------------------
    # Evaluate every candidate education record
    # --------------------------------------------------------

    education_results = []

    for education in candidate_education_records:

        if not isinstance(education, dict):
            continue

        education_text = _education_to_text(
            education
        )

        degree_score = calculate_degree_score(
            education_text,
            jd_education,
        )

        field_score = calculate_field_score(
            education_text,
            jd_education,
        )

        final_score = (
            degree_score * 0.60
            + field_score * 0.40
        )

        education_results.append(
            {
                "degree_score": round(
                    degree_score,
                    2,
                ),
                "field_score": round(
                    field_score,
                    2,
                ),
                "score": round(
                    final_score,
                    2,
                ),
                "degree_type": education.get(
                    "degree_type"
                ),
                "field_of_study": education.get(
                    "field_of_study"
                ),
                "institution": education.get(
                    "institution"
                ),
                "graduation_year": education.get(
                    "graduation_year"
                ),
            }
        )

    # Defensive fallback if the education list
    # contained invalid/non-dict entries.
    if not education_results:
        return {
            "score": 0.0,
            "weight": 0.10,
            "degree_score": 0.0,
            "field_score": 0.0,
            "candidate_education": candidate_education_records,
            "required_education": jd_education,
            "status": (
                "not_required"
                if not jd_education
                else "no_data"
            ),
        }

    # --------------------------------------------------------
    # Select best education record
    # --------------------------------------------------------

    best_result = max(
        education_results,
        key=lambda item: item["score"],
    )

    return {
        "score": best_result["score"],
        "weight": 0.10,
        "degree_score": best_result["degree_score"],
        "field_score": best_result["field_score"],
        "candidate_education": candidate_education_records,
        "best_matching_education": best_result,
        "required_education": jd_education,
        "status": (
            "not_required"
            if not jd_education
            else "calculated"
        ),
    }