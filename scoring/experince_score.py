import re
from typing import Any, Dict, List


# ============================================================
# Patterns
# ============================================================

YEAR_RANGE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*[-–—]\s*"
    r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
    re.IGNORECASE,
)

PLUS_YEAR_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)",
    re.IGNORECASE,
)

MIN_YEAR_PATTERN = re.compile(
    r"(?:minimum|min|at least)\s*"
    r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
    re.IGNORECASE,
)




# ============================================================
# Text Normalization
# ============================================================

def normalize_text(value: Any) -> str:
    """
    Normalize text for comparison.
    """
    if not isinstance(value, str):
        return ""

    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9+#.\s-]", " ", value)

    return " ".join(value.split())


# ============================================================
# JD Experience Parsing
# ============================================================

def extract_required_years(
    experience: List[Any]
) -> Dict[str, float]:
    """
    Extract minimum and maximum years of experience
    from JD experience requirements.

    Supports both structured dictionaries and strings.

    Structured example:
        {
            "minimum_years": 0,
            "maximum_years": 1,
            "description": "0-1 year experience"
        }

    String examples:
        "2-4 years"
        "3+ years"
        "minimum 2 years"
        "at least 1 year"
    """

    min_years = 0.0
    max_years = 0.0

    for item in experience or []:

        # ----------------------------------------------------
        # Structured experience object
        # ----------------------------------------------------
        if isinstance(item, dict):

            minimum = item.get("minimum_years")
            maximum = item.get("maximum_years")

            # Read explicit minimum_years
            try:
                if minimum is not None:
                    minimum_value = float(minimum)

                    min_years = max(
                        min_years,
                        minimum_value
                    )
            except (TypeError, ValueError):
                pass

            # Read explicit maximum_years
            try:
                if maximum is not None:
                    maximum_value = float(maximum)

                    max_years = max(
                        max_years,
                        maximum_value
                    )
            except (TypeError, ValueError):
                pass

            # ------------------------------------------------
            # Also inspect description
            # ------------------------------------------------
            description = item.get("description")

            if isinstance(description, str):

                # 2-4 years
                range_match = YEAR_RANGE_PATTERN.search(
                    description
                )

                if range_match:
                    range_min = float(
                        range_match.group(1)
                    )

                    range_max = float(
                        range_match.group(2)
                    )

                    min_years = max(
                        min_years,
                        range_min
                    )

                    max_years = max(
                        max_years,
                        range_max
                    )

                    continue

                # 3+ years
                plus_match = PLUS_YEAR_PATTERN.search(
                    description
                )

                if plus_match:
                    plus_min = float(
                        plus_match.group(1)
                    )

                    min_years = max(
                        min_years,
                        plus_min
                    )

                    continue

                # minimum 2 years / at least 1 year
                min_match = MIN_YEAR_PATTERN.search(
                    description
                )

                if min_match:
                    description_min = float(
                        min_match.group(1)
                    )

                    min_years = max(
                        min_years,
                        description_min
                    )

            continue

        # ----------------------------------------------------
        # String experience requirement
        # ----------------------------------------------------
        if isinstance(item, str):

            # 2-4 years
            range_match = YEAR_RANGE_PATTERN.search(item)

            if range_match:
                range_min = float(
                    range_match.group(1)
                )

                range_max = float(
                    range_match.group(2)
                )

                min_years = max(
                    min_years,
                    range_min
                )

                max_years = max(
                    max_years,
                    range_max
                )

                continue

            # 3+ years
            plus_match = PLUS_YEAR_PATTERN.search(item)

            if plus_match:
                plus_min = float(
                    plus_match.group(1)
                )

                min_years = max(
                    min_years,
                    plus_min
                )

                continue

            # minimum 2 years / at least 1 year
            min_match = MIN_YEAR_PATTERN.search(item)

            if min_match:
                string_min = float(
                    min_match.group(1)
                )

                min_years = max(
                    min_years,
                    string_min
                )

    return {
        "minimum_years": min_years,
        "maximum_years": max_years,
    }
# ============================================================
# Years Score
# ============================================================

def calculate_year_score(
    candidate_years: float,
    required_years: float
) -> float:
    """
    Calculate candidate experience score based on
    the minimum required years.

    Current logic:
        Candidate >= required -> 100
        Candidate < required  -> proportional score

    If no minimum experience is required,
    the score is 100.
    """

    if required_years <= 0:
        return 100.0

    if candidate_years >= required_years:
        return 100.0

    return min(
        (candidate_years / required_years) * 100,
        100.0,
    )


# ============================================================
# Role Relevance
# ============================================================

def calculate_role_relevance(
    candidate_roles: List[str],
    target_job_title: str,
) -> float:
    """
    Compare candidate's previous roles with the target job title.
    """

    if not candidate_roles or not target_job_title:
        return 0.0

    target = normalize_text(target_job_title)

    if not target:
        return 0.0

    target_tokens = set(target.split())

    best_score = 0.0

    for role in candidate_roles:

        normalized_role = normalize_text(role)

        if not normalized_role:
            continue

        # Exact role match
        if normalized_role == target:
            return 100.0

        role_tokens = set(normalized_role.split())

        if role_tokens:

            overlap = (
                len(target_tokens & role_tokens)
                / len(target_tokens)
                * 100
            )

            best_score = max(
                best_score,
                overlap
            )

    return round(best_score, 2)


# ============================================================
# Technology Relevance
# ============================================================

def calculate_technology_relevance(
    candidate_skills: List[str],
    required_skills: List[str],
) -> float:
    """
    Compare candidate skills with required JD skills.

    Example:

        Candidate:
            Python
            Django
            FastAPI
            PostgreSQL

        Required:
            Python
            Django
            FastAPI
            PostgreSQL

        Score = 100
    """

    if not required_skills:
        return 100.0

    if not candidate_skills:
        return 0.0

    candidate = {
        normalize_text(skill)
        for skill in candidate_skills
        if normalize_text(skill)
    }

    required = {
        normalize_text(skill)
        for skill in required_skills
        if normalize_text(skill)
    }

    if not required:
        return 100.0

    matched = candidate.intersection(required)

    return round(
        (len(matched) / len(required)) * 100,
        2,
    )


# ============================================================
# Experience Skills
# ============================================================

def _extract_experience_skills(
    candidate_roles_data: Any
) -> List[str]:
    """
    Extract skills from individual experience records.

    This is kept for compatibility with the existing project.
    """

    if not isinstance(candidate_roles_data, list):
        return []

    skills = []

    for item in candidate_roles_data:

        if not isinstance(item, dict):
            continue

        item_skills = item.get("skills", [])

        if not isinstance(item_skills, list):
            continue

        for skill in item_skills:

            if isinstance(skill, str):
                skills.append(skill)

            elif isinstance(skill, dict):

                name = (
                    skill.get("name")
                    or skill.get("skill")
                    or skill.get("canonical_name")
                )

                if isinstance(name, str):
                    skills.append(name)

    return skills


# Backward-compatible aliases
calculate_role_relevance_score = calculate_role_relevance
calculate_technology_relevance_score = calculate_technology_relevance


# ============================================================
# Profile Helpers
# ============================================================

def _resume_data(profile: Any) -> Dict[str, Any]:
    """
    Return the actual resume/JD data.

    Supports both:
        profile
    and:
        profile["resume_text"]
    """

    if not isinstance(profile, dict):
        return {}

    data = profile.get("resume_text")

    return data if isinstance(data, dict) else profile


# ============================================================
# Experience Records
# ============================================================

def _experience_records(
    profile: Any
) -> List[Dict[str, Any]]:
    """
    Extract experience records from candidate profile.
    """

    data = _resume_data(profile)

    value = data.get("experience", [])

    if not isinstance(value, list):
        return []

    return [
        item
        for item in value
        if isinstance(item, dict)
    ]


# ============================================================
# Candidate Years
# ============================================================

def _candidate_years(
    records: List[Dict[str, Any]]
) -> float:
    """
    Calculate total candidate experience in years.

    Priority:
        total_months
        total_years

    Example:
        4 months + 7 months
        = 11 months
        = 0.92 years
    """

    total_months = 0.0

    for item in records:

        total_experience = item.get(
            "total_experience",
            {}
        )

        if isinstance(total_experience, dict):

            months = total_experience.get(
                "total_months"
            )

            try:

                if months is not None:

                    total_months += float(months)

                    continue

            except (TypeError, ValueError):
                pass

            years = total_experience.get(
                "total_years"
            )

            try:

                if years is not None:

                    total_months += (
                        float(years) * 12
                    )

                    continue

            except (TypeError, ValueError):
                pass

        # Fallback
        try:

            years = item.get("total_years")

            if years is not None:

                total_months += (
                    float(years) * 12
                )

        except (TypeError, ValueError):
            pass

    return round(
        total_months / 12,
        2
    )


# ============================================================
# Candidate Roles
# ============================================================

def _candidate_roles(
    records: List[Dict[str, Any]]
) -> List[str]:
    """
    Extract candidate job titles from experience records.
    """

    roles = []

    print("\n===== _candidate_roles DEBUG =====")
    print("Records:", records)

    for item in records:

        if not isinstance(item, dict):
            continue

        title = item.get("title")

        print("TITLE:", title)
        print("TITLE TYPE:", type(title))

        # Example:
        # "title": "Python Developer"
        if isinstance(title, str):

            title = title.strip()

            if title:
                roles.append(title)

        # Example:
        # "title": {
        #     "title": "Python Developer"
        # }
        elif isinstance(title, dict):

            title_name = title.get("title")

            print("TITLE NAME:", title_name)

            if (
                isinstance(title_name, str)
                and title_name.strip()
            ):
                roles.append(
                    title_name.strip()
                )

    # Remove duplicate roles while preserving order
    roles = list(
        dict.fromkeys(roles)
    )

    print("FINAL ROLES:", roles)
    print("=================================\n")

    return roles


# ============================================================
# Experience-Level Skills
# ============================================================

def _experience_skills(
    records: List[Dict[str, Any]]
) -> List[str]:
    """
    Extract skills that are explicitly stored inside
    individual experience records.

    This may be empty if skills are stored only at
    the top-level profile.
    """

    skills = []

    for item in records:

        values = item.get(
            "skills",
            []
        )

        if not isinstance(values, list):
            continue

        for skill in values:

            if isinstance(skill, str):

                skills.append(skill)

            elif isinstance(skill, dict):

                name = (
                    skill.get("name")
                    or skill.get("skill")
                    or skill.get("canonical_name")
                )

                if isinstance(name, str):
                    skills.append(name)

    return list(
        dict.fromkeys(skills)
    )


# ============================================================
# Candidate Top-Level Skills
# ============================================================

def _candidate_skills(
    profile: Any
) -> List[str]:
    """
    Extract normalized candidate skills from the
    top-level profile.

    Expected structure:

        "skills": [
            {
                "skill": "Python"
            },
            {
                "skill": "Django"
            },
            {
                "skill": "FastAPI"
            }
        ]

    Also supports:

        "skills": [
            "Python",
            "Django",
            "FastAPI"
        ]
    """

    data = _resume_data(profile)

    skills_data = data.get(
        "skills",
        []
    )

    if not isinstance(skills_data, list):
        return []

    skills = []

    for item in skills_data:

        # String skill
        if isinstance(item, str):

            skill = item.strip()

            if skill:
                skills.append(skill)

        # Dictionary skill
        elif isinstance(item, dict):

            skill = (
                item.get("skill")
                or item.get("name")
                or item.get("canonical_name")
            )

            if isinstance(skill, str):

                skill = skill.strip()

                if skill:
                    skills.append(skill)

    # Remove duplicates while preserving order
    return list(
        dict.fromkeys(skills)
    )


# ============================================================
# Main Experience Scoring
# ============================================================

def calculate_experience_score(
    candidate_profile: Any,
    jd_profile: Any,
) -> Dict[str, Any]:
    """
    Calculate experience score.

    Weight distribution:

        Years       = 35%
        Role        = 25%
        Technology  = 40%
    """

    candidate_data = _resume_data(
        candidate_profile
    )

    jd_data = _resume_data(
        jd_profile
    )

    # --------------------------------------------------------
    # No data
    # --------------------------------------------------------

    if not candidate_data and not jd_data:

        return {
            "score": 100.0,
            "years_score": 100.0,
            "role_relevance_score": 100.0,
            "technology_relevance_score": 100.0,
            "candidate_years": 0.0,
            "required_minimum_years": 0.0,
            "preferred_maximum_years": 0.0,
            "candidate_roles": [],
            "target_job_title": "",
            "experience_skills": [],
            "candidate_skills": [],
            "required_skills": [],
            "status": "no_data",
        }

    # --------------------------------------------------------
    # Candidate data
    # --------------------------------------------------------

    records = _experience_records(
        candidate_profile
    )

    candidate_years = _candidate_years(
        records
    )

    candidate_roles = _candidate_roles(
        records
    )

    # Skills stored inside experience records
    experience_skills = _experience_skills(
        records
    )

    # IMPORTANT:
    # Candidate's actual normalized skills are stored
    # at the top-level "skills" field.
    candidate_skills = _candidate_skills(
        candidate_profile
    )

    # --------------------------------------------------------
    # JD data
    # --------------------------------------------------------

    jd_experience = jd_data.get(
        "experience",
        []
    )

    if not isinstance(jd_experience, list):
        jd_experience = []

    jd_job_title = jd_data.get(
        "job_title",
        ""
    )

    if not isinstance(jd_job_title, str):
        jd_job_title = ""

    required_skills = jd_data.get(
        "required_skills",
        []
    )

    if not isinstance(required_skills, list):
        required_skills = []

    # --------------------------------------------------------
    # Required experience
    # --------------------------------------------------------

    requirement = extract_required_years(
        jd_experience
    )

    required_years = requirement[
        "minimum_years"
    ]

    maximum_years = requirement[
        "maximum_years"
    ]

    # --------------------------------------------------------
    # Years score
    # --------------------------------------------------------

    years_score = calculate_year_score(
        candidate_years,
        required_years,
    )

    # --------------------------------------------------------
    # Role score
    # --------------------------------------------------------

    print("\n===== ROLE DEBUG =====")
    print(
        "Candidate roles:",
        candidate_roles
    )
    print(
        "JD job title:",
        jd_job_title
    )
    print(
        "Calculated role score:",
        calculate_role_relevance(
            candidate_roles,
            jd_job_title
        )
    )
    print("=====================\n")

    role_score = calculate_role_relevance(
        candidate_roles,
        jd_job_title,
    )

    # --------------------------------------------------------
    # Technology score
    # --------------------------------------------------------
    #
    # IMPORTANT CHANGE:
    #
    # Previously:
    #
    #     experience_skills
    #
    # was used for technology scoring.
    #
    # But the candidate JSON stores normalized skills
    # at:
    #
    #     profile["skills"]
    #
    # Therefore we now use:
    #
    #     candidate_skills
    #
    # for technology relevance.
    # --------------------------------------------------------

    technology_score = calculate_technology_relevance(
        candidate_skills,
        required_skills,
    )

    # --------------------------------------------------------
    # Final experience score
    # --------------------------------------------------------

    final_score = (
        years_score * 0.35
        + role_score * 0.25
        + technology_score * 0.40
    )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    if not records:

        status = "no_data"

    elif not jd_experience:

        status = "no_requirement"

    else:

        status = "calculated"

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    return {
        "score": round(
            final_score,
            2
        ),

        "years_score": round(
            years_score,
            2
        ),

        "role_relevance_score": round(
            role_score,
            2
        ),

        "technology_relevance_score": round(
            technology_score,
            2
        ),

        "candidate_years": candidate_years,

        "required_minimum_years": required_years,

        "preferred_maximum_years": maximum_years,

        "candidate_roles": candidate_roles,

        "target_job_title": jd_job_title,

        # Skills specifically stored inside
        # experience records.
        "experience_skills": experience_skills,

        # Candidate's normalized top-level skills.
        "candidate_skills": candidate_skills,

        "required_skills": required_skills,

        "status": status,
    }
