import re

from typing import Any, Dict, List, Optional


EXPERIENCE_WEIGHT = 0.30

YEARS_WEIGHT = 0.35
ROLE_WEIGHT = 0.25
TECHNOLOGY_WEIGHT = 0.40


def normalize_text(value: Any) -> str:
    return " ".join(
        str(value or "").strip().lower().split()
    )


def extract_required_years(value: Any) -> Dict[str, Optional[float]]:
    """
    Extract minimum and maximum experience requirements.

    Supported examples:

        "2 - 4 Years"
        "2-4 years"
        "2 years"
        "2+ years"
        "Minimum 2 years"
        "At least 2 years"

    Also supports lists and dictionaries.
    """

    if value is None:
        return {
            "minimum_years": 0.0,
            "maximum_years": None,
        }

    # --------------------------------------------------------
    # List / tuple
    # --------------------------------------------------------

    if isinstance(value, (list, tuple)):
        values = [
            extract_required_years(item)
            for item in value
        ]

        minimum_values = [
            item["minimum_years"]
            for item in values
            if item["minimum_years"] is not None
        ]

        maximum_values = [
            item["maximum_years"]
            for item in values
            if item["maximum_years"] is not None
        ]

        return {
            "minimum_years": max(
                minimum_values or [0.0]
            ),
            "maximum_years": (
                max(maximum_values)
                if maximum_values
                else None
            ),
        }

    # --------------------------------------------------------
    # Dictionary
    # --------------------------------------------------------

    if isinstance(value, dict):

        minimum = value.get("minimum_years")
        maximum = value.get("maximum_years")

        text = (
            value.get("description")
            or value.get("required_experience")
            or value.get("experience")
            or ""
        )

        if minimum is None:
            minimum = extract_required_years(
                text
            )["minimum_years"]

        if maximum is None:
            maximum = extract_required_years(
                text
            )["maximum_years"]

        try:
            minimum = float(minimum or 0)
        except (TypeError, ValueError):
            minimum = 0.0

        try:
            maximum = (
                None
                if maximum is None
                else float(maximum)
            )
        except (TypeError, ValueError):
            maximum = None

        return {
            "minimum_years": minimum,
            "maximum_years": maximum,
        }

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    text = normalize_text(value)

    # Example:
    # 2 - 4 years
    # 2–4 years
    # 2 — 4 yrs
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*[-–—]\s*"
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:years?|yrs?)",
        text,
        re.IGNORECASE,
    )

    if range_match:
        return {
            "minimum_years": float(
                range_match.group(1)
            ),
            "maximum_years": float(
                range_match.group(2)
            ),
        }

    # Example:
    # 2+ years
    plus_match = re.search(
        r"(\d+(?:\.\d+)?)\s*\+\s*"
        r"(?:years?|yrs?)",
        text,
        re.IGNORECASE,
    )

    if plus_match:
        return {
            "minimum_years": float(
                plus_match.group(1)
            ),
            "maximum_years": None,
        }

    # Example:
    # minimum 2 years
    # min 2 years
    # at least 2 years
    minimum_match = re.search(
        r"(?:minimum|min|at\s+least)\s*"
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:years?|yrs?)",
        text,
        re.IGNORECASE,
    )

    if minimum_match:
        return {
            "minimum_years": float(
                minimum_match.group(1)
            ),
            "maximum_years": None,
        }

    # Example:
    # 2 years
    simple_match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:years?|yrs?)",
        text,
        re.IGNORECASE,
    )

    if simple_match:
        return {
            "minimum_years": float(
                simple_match.group(1)
            ),
            "maximum_years": None,
        }

    return {
        "minimum_years": 0.0,
        "maximum_years": None,
    }


def calculate_year_score(
    candidate_years: Any,
    required_years: Any,
) -> float:

    try:
        candidate = float(
            candidate_years or 0
        )
        required = float(
            required_years or 0
        )
    except (TypeError, ValueError):
        candidate = 0.0
        required = 0.0

    # No JD requirement.
    if required <= 0:
        return 100.0

    # Candidate satisfies minimum.
    if candidate >= required:
        return 100.0

    return round(
        max(
            0.0,
            candidate / required * 100,
        ),
        2,
    )


def calculate_role_relevance(
    candidate_roles: List[str],
    target_role: Optional[str] = None,
    target_job_title: Optional[str] = None,
) -> float:

    target = normalize_text(
        target_role or target_job_title
    )

    roles = [
        normalize_text(role)
        for role in (candidate_roles or [])
        if normalize_text(role)
    ]

    if not target or not roles:
        return 0.0

    # Exact / containment match.
    for role in roles:

        if (
            role == target
            or target in role
            or role in target
        ):
            return 100.0

    # Token overlap fallback.
    target_tokens = set(
        target.split()
    )

    best = 0.0

    for role in roles:

        role_tokens = set(
            role.split()
        )

        if not target_tokens:
            continue

        overlap = (
            len(
                target_tokens
                & role_tokens
            )
            / len(target_tokens)
            * 100
        )

        best = max(
            best,
            overlap,
        )

    return round(best, 2)


def calculate_technology_relevance(
    candidate_skills: List[str],
    required_skills: List[str],
) -> float:

    required = {
        normalize_text(skill)
        for skill in (required_skills or [])
        if normalize_text(skill)
    }

    candidate = {
        normalize_text(skill)
        for skill in (candidate_skills or [])
        if normalize_text(skill)
    }

    if not required:
        return 100.0

    return round(
        len(required & candidate)
        / len(required)
        * 100,
        2,
    )


def _profile(profile: Any) -> Dict[str, Any]:
    """
    Support both:

        {
            "experience": [...]
        }

    and:

        {
            "resume_text": {
                "experience": [...]
            }
        }
    """

    if not isinstance(profile, dict):
        return {}

    resume_text = profile.get(
        "resume_text"
    )

    if isinstance(resume_text, dict):
        return {
            **resume_text,
            **profile,
        }

    return profile


def _candidate_years(
    profile: Any,
) -> float:

    profile = _profile(profile)

    total_experience = profile.get(
        "total_experience"
    )

    if isinstance(
        total_experience,
        dict,
    ):

        total_months = (
            total_experience.get(
                "total_months"
            )
        )

        if total_months is not None:
            try:
                return round(
                    float(total_months) / 12,
                    2,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        total_years = (
            total_experience.get(
                "total_years"
            )
        )

        if total_years is not None:
            try:
                return round(
                    float(total_years),
                    2,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

    experience = profile.get(
        "experience",
        [],
    )

    if not isinstance(
        experience,
        list,
    ):
        experience = []

    best = 0.0

    for record in experience:

        if not isinstance(
            record,
            dict,
        ):
            continue

        total = record.get(
            "total_experience"
        )

        if not isinstance(
            total,
            dict,
        ):
            continue

        total_years = total.get(
            "total_years"
        )

        if total_years is not None:
            try:
                best = max(
                    best,
                    float(total_years),
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        total_months = total.get(
            "total_months"
        )

        if total_months is not None:
            try:
                best = max(
                    best,
                    float(total_months) / 12,
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

    return round(
        best,
        2,
    )


def _roles(
    profile: Any,
) -> List[str]:

    profile = _profile(profile)

    experience = profile.get(
        "experience",
        [],
    )

    if not isinstance(
        experience,
        list,
    ):
        return []

    roles = []

    for record in experience:

        if not isinstance(
            record,
            dict,
        ):
            continue

        role = (
            record.get("role")
            or record.get("job_title")
            or record.get("title")
        )

        if role:

            role = str(
                role
            ).strip()

            if (
                role
                and role not in roles
            ):
                roles.append(role)

    return roles


def _skills(
    profile: Any,
) -> List[str]:
    """
    Collect skills from:

    1. top-level skills
    2. skills inside experience records
    """

    profile = _profile(profile)

    collected = []

    def add_skill(value: Any):

        if isinstance(
            value,
            dict,
        ):
            value = (
                value.get("name")
                or value.get("skill")
                or value.get("canonical_name")
            )

        if value is None:
            return

        value = str(value).strip()

        if (
            value
            and value not in collected
        ):
            collected.append(value)

    # --------------------------------------------------------
    # Top-level skills
    # --------------------------------------------------------

    skills = profile.get(
        "skills",
        [],
    )

    if isinstance(
        skills,
        str,
    ):
        skills = [skills]

    if isinstance(
        skills,
        list,
    ):
        for skill in skills:
            add_skill(skill)

    # --------------------------------------------------------
    # Experience-level skills
    # --------------------------------------------------------

    experience = profile.get(
        "experience",
        [],
    )

    if isinstance(
        experience,
        list,
    ):

        for record in experience:

            if not isinstance(
                record,
                dict,
            ):
                continue

            experience_skills = record.get(
                "skills",
                [],
            )

            if isinstance(
                experience_skills,
                str,
            ):
                experience_skills = [
                    experience_skills
                ]

            if isinstance(
                experience_skills,
                list,
            ):
                for skill in experience_skills:
                    add_skill(skill)

    return collected


def calculate_experience_score(
    candidate_profile: Any,
    jd_profile: Any,
    skill_result: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:

    candidate = _profile(
        candidate_profile
    )

    jd = _profile(
        jd_profile
    )

    # --------------------------------------------------------
    # Candidate data
    # --------------------------------------------------------

    candidate_years = _candidate_years(
        candidate
    )

    candidate_roles = _roles(
        candidate
    )

    experience_skills = _skills(
        candidate
    )

    # --------------------------------------------------------
    # JD data
    # --------------------------------------------------------

    target_role = str(
        jd.get("job_title")
        or jd.get("title")
        or jd.get("position")
        or ""
    )

    required_skills = list(
        jd.get(
            "required_skills",
            [],
        )
        or []
    )

    required_experience = jd.get(
        "experience",
        [],
    )

    required_experience_data = (
        extract_required_years(
            required_experience
        )
    )

    required_minimum_years = (
        required_experience_data[
            "minimum_years"
        ]
    )

    required_maximum_years = (
        required_experience_data[
            "maximum_years"
        ]
    )

    # --------------------------------------------------------
    # Calculate components
    # --------------------------------------------------------

    years_score = calculate_year_score(
        candidate_years,
        required_minimum_years,
    )

    role_score = calculate_role_relevance(
        candidate_roles,
        target_role=target_role,
    )

    # Technology score can come from the
    # SkillScore module.
    if isinstance(
        skill_result,
        dict,
    ):

        technology_score = float(
            (
                skill_result.get(
                    "required"
                )
                or {}
            ).get(
                "match_percentage",
                0,
            )
            or 0
        )

        technology_score_source = (
            "skill_score"
        )

    else:

        technology_score = (
            calculate_technology_relevance(
                experience_skills,
                required_skills,
            )
        )

        technology_score_source = (
            "legacy_technology_scorer"
        )

    # --------------------------------------------------------
    # Final experience score
    # --------------------------------------------------------

    final_score = round(
        years_score * YEARS_WEIGHT
        + role_score * ROLE_WEIGHT
        + technology_score
        * TECHNOLOGY_WEIGHT,
        2,
    )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    has_experience_data = bool(
        candidate_roles
        or experience_skills
        or candidate_years > 0
    )

    return {
        "score": final_score,
        "weight": EXPERIENCE_WEIGHT,

        # Numeric component scores are expected
        # by the experience scorer test suite.
        "component_scores": {
            "years": round(
                years_score,
                2,
            ),
            "role": round(
                role_score,
                2,
            ),
            "technology": round(
                technology_score,
                2,
            ),
        },

        # Component weights remain available
        # separately.
        "weights": {
            "years": YEARS_WEIGHT,
            "role": ROLE_WEIGHT,
            "technology": TECHNOLOGY_WEIGHT,
        },

        "candidate_years": candidate_years,

        "required_minimum_years": (
            required_minimum_years
        ),

        "required_maximum_years": (
            required_maximum_years
        ),

        "candidate_roles": candidate_roles,

        "target_role": target_role,

        "candidate_skills": experience_skills,

        # Explicit field required by the
        # experience scorer tests.
        "experience_skills": experience_skills,

        "required_skills": required_skills,

        "technology_score_source": (
            technology_score_source
        ),

        "status": (
            "calculated"
            if has_experience_data
            else "no_data"
        ),
    }