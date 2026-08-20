from typing import Any, Dict


def profile_to_embedding_text(
    profile: Dict[str, Any]
) -> str:
    """
    Convert a masked candidate profile into
    semantic embedding text.

    Personal information is intentionally excluded.
    """

    if not isinstance(profile, dict):
        return ""

    parts = []

    # Skills
    skills = profile.get("skills", [])

    if isinstance(skills, list):
        for skill in skills:
            if isinstance(skill, dict):
                skill_name = (
                    skill.get("skill")
                    or skill.get("skill_name")
                    or skill.get("name")
                    or ""
                )
            else:
                skill_name = str(skill)

            if skill_name:
                parts.append(str(skill_name))

    elif isinstance(skills, str):
        parts.append(skills)

    # Experience
    experience = profile.get("experience", [])

    if isinstance(experience, list):
        for item in experience:

            if not isinstance(item, dict):
                continue

            title = item.get("title", "")

            if isinstance(title, dict):
                title = (
                    title.get("title")
                    or title.get("name")
                    or ""
                )

            if title:
                parts.append(str(title))

            company = item.get("company", "")

            if isinstance(company, dict):
                company = (
                    company.get("name")
                    or company.get("company_name")
                    or ""
                )

            if company:
                parts.append(str(company))

            experience_skills = item.get("skills", [])

            if isinstance(experience_skills, list):
                for skill in experience_skills:

                    if isinstance(skill, dict):
                        skill_name = (
                            skill.get("skill")
                            or skill.get("skill_name")
                            or skill.get("name")
                            or ""
                        )
                    else:
                        skill_name = str(skill)

                    if skill_name:
                        parts.append(str(skill_name))

            descriptions = item.get("description", [])

            if isinstance(descriptions, list):
                for description in descriptions:
                    if description:
                        parts.append(str(description))

            elif descriptions:
                parts.append(str(descriptions))

    # Education
    education = profile.get("education", [])

    if isinstance(education, list):
        for item in education:

            if not isinstance(item, dict):
                continue

            degree = item.get("degree_type", "")
            field = item.get("field_of_study", "")
            institution = item.get("institution", "")

            if degree:
                parts.append(str(degree))

            if field:
                parts.append(str(field))

            if institution:
                parts.append(str(institution))

    # Projects
    projects = profile.get("projects", [])

    if isinstance(projects, list):
        for project in projects:

            if not isinstance(project, dict):
                continue

            project_name = project.get("project_name", "")
            description = project.get("description", "")
            technologies = project.get("technologies", [])

            if project_name:
                parts.append(str(project_name))

            if description:
                parts.append(str(description))

            if isinstance(technologies, list):
                for technology in technologies:
                    if technology:
                        parts.append(str(technology))

    # Certifications
    certifications = profile.get("certifications", [])

    if isinstance(certifications, list):
        for certification in certifications:

            if not isinstance(certification, dict):
                continue

            certification_name = certification.get(
                "certification_name",
                ""
            )

            if certification_name:
                parts.append(str(certification_name))

    return " ".join(
        part.strip()
        for part in parts
        if isinstance(part, str)
        and part.strip()
    ).strip()


def build_jd_embedding_text(
    jd_profile: Dict[str, Any]
) -> str:
    """
    Convert structured JD JSON into semantic
    embedding text.
    """

    if not isinstance(jd_profile, dict):
        return ""

    parts = []

    job_title = jd_profile.get("job_title")

    if job_title:
        parts.append(
            f"Job Title: {job_title}"
        )

    for key in (
        "summary",
        "description",
        "job_summary",
        "responsibilities",
        "job_responsibilities",
    ):

        value = jd_profile.get(key)

        if isinstance(value, str) and value.strip():
            parts.append(value.strip())

        elif isinstance(value, list):
            for item in value:
                if item:
                    parts.append(str(item).strip())

    required_skills = jd_profile.get(
        "required_skills",
        []
    )

    skill_names = []

    if isinstance(required_skills, list):
        for skill in required_skills:

            if isinstance(skill, dict):
                skill_name = (
                    skill.get("skill")
                    or skill.get("name")
                    or skill.get("skill_name")
                    or ""
                )
            else:
                skill_name = str(skill)

            if skill_name:
                skill_names.append(str(skill_name))

    elif isinstance(required_skills, str):
        skill_names.append(required_skills)

    if skill_names:
        parts.append(
            "Required Skills: "
            + ", ".join(skill_names)
        )

    preferred_skills = jd_profile.get(
        "preferred_skills",
        []
    )

    preferred_names = []

    if isinstance(preferred_skills, list):
        for skill in preferred_skills:

            if isinstance(skill, dict):
                skill_name = (
                    skill.get("skill")
                    or skill.get("name")
                    or skill.get("skill_name")
                    or ""
                )
            else:
                skill_name = str(skill)

            if skill_name:
                preferred_names.append(
                    str(skill_name)
                )

    elif isinstance(preferred_skills, str):
        preferred_names.append(preferred_skills)

    if preferred_names:
        parts.append(
            "Preferred Skills: "
            + ", ".join(preferred_names)
        )

    experience = jd_profile.get("experience")

    if experience:
        parts.append(
            f"Experience Requirements: {experience}"
        )

    education = jd_profile.get("education")

    if education:
        parts.append(
            f"Education Requirements: {education}"
        )

    return "\n".join(
        part
        for part in parts
        if part and str(part).strip()
    ).strip()