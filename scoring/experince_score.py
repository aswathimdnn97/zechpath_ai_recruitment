import re
from typing import Any, Dict, List


# ============================================================
# Patterns
# ============================================================

YEAR_RANGE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*[-–]\s*"
    r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
    re.IGNORECASE,
)

MIN_YEAR_PATTERN = re.compile(
    r"(?:minimum|min|at least)\s*"
    r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
    re.IGNORECASE,
)


# ============================================================
# Text normalization
# ============================================================

def normalize_text(value: Any) -> str:
    """
    Normalize text for comparison.
    """

    if not isinstance(value, str):
        return ""

    value = value.lower().strip()

    value = re.sub(
        r"[^a-z0-9+#.\s-]",
        " ",
        value,
    )

    return " ".join(value.split())


# ============================================================
# Extract required experience
# ============================================================

def extract_required_years(
    experience: List[str],
) -> Dict[str, float]:
    """
    Extract minimum and maximum experience
    requirements from JD experience text.
    """

    min_years = 0.0
    max_years = 0.0

    for item in experience or []:

        if not isinstance(item, str):
            continue

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
                range_min,
            )

            max_years = max(
                max_years,
                range_max,
            )

            continue

        min_match = MIN_YEAR_PATTERN.search(item)

        if min_match:

            min_years = max(
                min_years,
                float(min_match.group(1)),
            )

    return {
        "minimum_years": min_years,
        "maximum_years": max_years,
    }


# ============================================================
# Years score
# ============================================================

def calculate_year_score(
    candidate_years: float,
    required_years: float,
) -> float:
    """
    Calculate experience-years score.
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
# Role relevance
# ============================================================

def calculate_role_relevance(
    candidate_roles: List[str],
    target_job_title: str,
) -> float:
    """Calculate relevance between candidate roles and target JD title."""
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
        if normalized_role == target:
            return 100.0
        role_tokens = set(normalized_role.split())
        if role_tokens:
            best_score = max(
                best_score,
                len(target_tokens & role_tokens) / len(target_tokens) * 100,
            )
    return round(best_score, 2)


# ============================================================
# Technology relevance
# ============================================================

def calculate_technology_relevance(
    candidate_skills: List[str],
    required_skills: List[str],
) -> float:
    """
    Calculate technology/skill relevance.

    The score is based on how many JD-required
    technologies are present in the candidate profile.
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

    matched = candidate.intersection(
        required
    )

    return round(
        (
            len(matched)
            / len(required)
        ) * 100,
        2,
    )


# ============================================================
# Extract candidate experience skills
# ============================================================

def _extract_experience_skills(
    candidate_roles_data: Any,
) -> List[str]:
    """
    Extract skills from experience records.

    Supports:

        [
            {
                "title": "Python Developer",
                "skills": [
                    "Python",
                    "Django"
                ]
            }
        ]
    """

    if not isinstance(
        candidate_roles_data,
        list,
    ):
        return []

    skills = []

    for item in candidate_roles_data:

        if not isinstance(item, dict):
            continue

        item_skills = item.get(
            "skills",
            [],
        )

        if not isinstance(
            item_skills,
            list,
        ):
            continue

        for skill in item_skills:

            if isinstance(
                skill,
                str,
            ):
                skills.append(skill)

            elif isinstance(
                skill,
                dict,
            ):

                name = (
                    skill.get("name")
                    or skill.get("skill")
                    or skill.get(
                        "canonical_name"
                    )
                )

                if isinstance(
                    name,
                    str,
                ):
                    skills.append(name)

    return skills


# ============================================================
# Backward-compatible aliases
# ============================================================

calculate_role_relevance_score = calculate_role_relevance
calculate_technology_relevance_score = calculate_technology_relevance


# ============================================================
# Profile helpers
# ============================================================

def _resume_data(profile: Any) -> Dict[str, Any]:
    if not isinstance(profile, dict):
        return {}

    data = profile.get("resume_text")
    return data if isinstance(data, dict) else profile


def _experience_records(profile: Any) -> List[Dict[str, Any]]:
    data = _resume_data(profile)
    value = data.get("experience", [])
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _candidate_years(records: List[Dict[str, Any]]) -> float:
    values = []

    for item in records:
        total = item.get("total_experience", {})
        if isinstance(total, dict):
            value = total.get("total_years")
            try:
                if value is not None:
                    values.append(float(value))
            except (TypeError, ValueError):
                pass

        try:
            if item.get("total_years") is not None:
                values.append(float(item["total_years"]))
        except (TypeError, ValueError):
            pass

    return max(values, default=0.0)


def _candidate_roles(
    records: List[Dict[str, Any]]
) -> List[str]:

    roles = []

    print("\n===== _candidate_roles DEBUG =====")
    print("Records:", records)

    for item in records:

        if not isinstance(item, dict):
            continue

        title = item.get("title")

        print("TITLE:", title)
        print("TITLE TYPE:", type(title))

        # title = "Python Developer"
        if isinstance(title, str):
            title = title.strip()

            if title:
                roles.append(title)

        # title = {"title": "Python Developer", ...}
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

    roles = list(dict.fromkeys(roles))

    print("FINAL ROLES:", roles)
    print("=================================\n")

    return roles


def _experience_skills(records: List[Dict[str, Any]]) -> List[str]:
    skills = []

    for item in records:
        values = item.get("skills", [])
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

    return list(dict.fromkeys(skills))


# ============================================================
# Main experience scorer
# ============================================================

def calculate_experience_score(
    candidate_profile: Any,
    jd_profile: Any,
) -> Dict[str, Any]:
    """
    Calculate complete experience relevance score.

    Years       = 35%
    Role        = 25%
    Technology  = 40%

    Accepts complete candidate and JD profiles.
    """

    candidate_data = _resume_data(candidate_profile)
    jd_data = _resume_data(jd_profile)
    
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

    records = _experience_records(candidate_profile)

    candidate_years = _candidate_years(records)
    candidate_roles = _candidate_roles(records)
    experience_skills = _experience_skills(records)

    jd_experience = jd_data.get("experience", [])
    if not isinstance(jd_experience, list):
        jd_experience = []

    jd_job_title = jd_data.get("job_title", "")
    if not isinstance(jd_job_title, str):
        jd_job_title = ""

    required_skills = jd_data.get("required_skills", [])
    if not isinstance(required_skills, list):
        required_skills = []

    requirement = extract_required_years(jd_experience)
    required_years = requirement["minimum_years"]
    maximum_years = requirement["maximum_years"]

    years_score = calculate_year_score(
        candidate_years,
        required_years,
    )
    
    print("\n===== ROLE DEBUG =====")
    print("Candidate roles:", candidate_roles)
    print("JD job title:", jd_job_title)
    print("Calculated role score:", calculate_role_relevance(
        candidate_roles,
        jd_job_title
    ))
    print("=====================\n")

    role_score = calculate_role_relevance(
        candidate_roles,
        jd_job_title,
    )

    technology_score = calculate_technology_relevance(
        experience_skills,
        required_skills,
    )

    final_score = (
        years_score * 0.35
        + role_score * 0.25
        + technology_score * 0.40
    )

    if not records:
        status = "no_data"
    elif not jd_experience:
        status = "no_requirement"
    else:
        status = "calculated"

    return {
        "score": round(final_score, 2),
        "years_score": round(years_score, 2),
        "role_relevance_score": round(role_score, 2),
        "technology_relevance_score": round(technology_score, 2),
        "candidate_years": candidate_years,
        "required_minimum_years": required_years,
        "preferred_maximum_years": maximum_years,
        "candidate_roles": candidate_roles,
        "target_job_title": jd_job_title,
        "experience_skills": experience_skills,
        "candidate_skills": experience_skills,
        "required_skills": required_skills,
        "status": status,
    }