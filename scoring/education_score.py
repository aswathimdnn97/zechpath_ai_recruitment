import re
from typing import Any, Dict, List


DEGREE_ALIASES = {
    "b.tech": "bachelor",
    "btech": "bachelor",
    "b.e": "bachelor",
    "be": "bachelor",
    "bachelor": "bachelor",
    "bachelor's": "bachelor",

    "mca": "master",
    "m.sc": "master",
    "msc": "master",
    "master": "master",
    "bachelor of technology": "bachelor",
    "bachelor of engineering": "bachelor",
    "master of computer applications": "master",
    "master of science": "master",
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


# ============================================================
# Text normalization
# ============================================================

def normalize_text(value: Any) -> str:
    """
    Normalize text for education comparison.
    """

    if not isinstance(value, str):
        return ""

    value = value.lower()

    value = re.sub(
        r"[^\w\s.]",
        " ",
        value
    )

    return " ".join(
        value.split()
    )


# ============================================================
# Degree detection
# ============================================================

def detect_degree_level(
    text: str
) -> str:
    """
    Detect broad degree level.

    Returns:

        bachelor
        master
        ""
    """

    text = normalize_text(text)

    for alias, level in DEGREE_ALIASES.items():

        normalized_alias = normalize_text(
            alias
        )

        if normalized_alias in text:
            return level

    return ""


# ============================================================
# Extract candidate education
# ============================================================

def _extract_candidate_education(
    candidate_profile: Dict[str, Any]
) -> List[Dict[str, Any]]:

    if not isinstance(candidate_profile, dict):
        return []

    resume_data = candidate_profile.get(
        "resume_text"
    )

    if isinstance(resume_data, dict):
        education = resume_data.get(
            "education",
            []
        )
    else:
        education = candidate_profile.get(
            "education",
            []
        )

    if not isinstance(education, list):
        return []

    return [
        item
        for item in education
        if isinstance(item, dict)
    ]


# ============================================================
# Convert candidate education object to text
# ============================================================

def _education_to_text(
    education: Dict[str, Any]
) -> str:
    """
    Convert a structured education object
    into searchable text.

    This also handles cases where field_of_study
    is missing but the institution/other fields
    contain useful information.
    """

    values = []

    for key in [
    "degree_type",
    "field_of_study",
    "field",
    "institution",
    "education",
    "degree",
    "course",
    ]:

        value = education.get(key)

        if isinstance(value, str):
            values.append(value)

    return " ".join(values)


# ============================================================
# Degree score
# ============================================================

def calculate_degree_score(
    candidate_education: str,
    jd_education: List[str]
) -> float:
    """
    Compare candidate degree level with JD requirements.

    Exact level match = 100
    Different known level = 40
    Missing candidate education = 0
    No JD requirement = 100
    """

    if not jd_education:
        return 100.0

    if not candidate_education:
        return 0.0

    candidate_level = detect_degree_level(
        candidate_education
    )

    required_levels = set()

    for requirement in jd_education:

        level = detect_degree_level(
            requirement
        )

        if level:
            required_levels.add(level)

    if not required_levels:
        return 100.0

    if candidate_level in required_levels:
        return 100.0

    return 40.0


# ============================================================
# Field score
# ============================================================

def calculate_field_score(
    candidate_education: str,
    jd_education: List[str]
) -> float:
    """
    Compare candidate field of study with
    fields mentioned in the JD.
    """

    if not jd_education:
        return 100.0

    if not candidate_education:
        return 0.0

    candidate_text = normalize_text(
        candidate_education
    )

    matched_fields = []

    for canonical_field, aliases in (
        FIELD_ALIASES.items()
    ):

        candidate_has_field = any(
            normalize_text(alias)
            in candidate_text
            for alias in aliases
        )

        if not candidate_has_field:
            continue

        for requirement in jd_education:

            requirement_text = normalize_text(
                requirement
            )

            requirement_has_field = any(
                normalize_text(alias)
                in requirement_text
                for alias in aliases
            )

            if requirement_has_field:

                matched_fields.append(
                    canonical_field
                )

                break

    return (
        100.0
        if matched_fields
        else 40.0
    )


# ============================================================
# Main education scorer
# ============================================================

def calculate_education_score(
    candidate_profile: Dict[str, Any],
    jd_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate ATS education score.

    Degree alignment = 60%
    Field alignment  = 40%
    """

    # --------------------------------------------------------
    # Candidate education
    # --------------------------------------------------------

    candidate_education_records = (
        _extract_candidate_education(
            candidate_profile
        )
    )

    # --------------------------------------------------------
    # JD education
    # --------------------------------------------------------

    jd_data = jd_profile.get(
    "resume_text"
)

    if not isinstance(jd_data, dict):
        jd_data = jd_profile

    jd_education = jd_data.get(
        "education",
        []
    )

    if not isinstance(jd_education, list):
        jd_education = []

    # --------------------------------------------------------
    # Missing candidate education
    # --------------------------------------------------------

    if not candidate_education_records:

        return {
            "score": 0.0,
            "degree_score": 0.0,
            "field_score": 0.0,
            "candidate_education": [],
            "required_education": jd_education,
            "status": (
                "not_required"
                if not jd_education
                else "no_data"
            )
        }

    # --------------------------------------------------------
    # Score every candidate education record
    # --------------------------------------------------------

    education_results = []

    for education in (
        candidate_education_records
    ):

        education_text = (
            _education_to_text(
                education
            )
        )

        degree_score = (
            calculate_degree_score(
                education_text,
                jd_education
            )
        )

        field_score = (
            calculate_field_score(
                education_text,
                jd_education
            )
        )

        final_score = (
            degree_score * 0.60
            + field_score * 0.40
        )

        education_results.append({

            "degree_score": round(
                degree_score,
                2
            ),

            "field_score": round(
                field_score,
                2
            ),

            "score": round(
                final_score,
                2
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
            )
        })

    # --------------------------------------------------------
    # Select best education match
    # --------------------------------------------------------

    best_result = max(
        education_results,
        key=lambda item: item["score"]
    )

    # --------------------------------------------------------
    # Final output
    # --------------------------------------------------------

    return {

        "score": best_result["score"],

        "degree_score":
            best_result["degree_score"],

        "field_score":
            best_result["field_score"],

        "candidate_education":
            candidate_education_records,

        "best_matching_education":
            best_result,

        "required_education":
            jd_education,

        "status": (
            "not_required"
            if not jd_education
            else "calculated"
        )
    }