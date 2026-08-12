from typing import Any, Dict, List, Optional

from .embedding_generator import EmbeddingGenerator


# ============================================================
# Embedding Generator
# ============================================================

_embedding_generator = EmbeddingGenerator()


# ============================================================
# Helper Functions
# ============================================================

def _safe_text(value: Any) -> str:
    """
    Convert a value into clean text suitable for embedding.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return ", ".join(
            str(item).strip()
            for item in value
            if item is not None and str(item).strip()
        )

    if isinstance(value, dict):
        return " ".join(
            str(v).strip()
            for v in value.values()
            if v is not None and str(v).strip()
        )

    return str(value).strip()


def _join_text(values: List[Any]) -> str:
    """
    Join multiple values into one clean text string.
    """

    texts = []

    for value in values:

        text = _safe_text(value)

        if text:
            texts.append(text)

    return " ".join(texts).strip()


# ============================================================
# Resume Section Builders
# ============================================================

def build_resume_skill_text(
    candidate_profile: Dict[str, Any]
) -> str:
    """
    Build clean text representation of candidate skills.
    """

    skills = candidate_profile.get("skills", [])

    if not skills:
        return ""

    skill_names = []

    for skill in skills:

        if isinstance(skill, str):

            skill_names.append(skill)

        elif isinstance(skill, dict):

            name = (
                skill.get("name")
                or skill.get("skill")
                or skill.get("canonical_name")
            )

            if name:
                skill_names.append(str(name))

    return _join_text(skill_names)


def build_resume_experience_text(
    candidate_profile: Dict[str, Any]
) -> str:
    """
    Build clean experience text.

    IMPORTANT:
    Only include job title, company and actual
    description/responsibilities.

    Do NOT embed metadata such as:
        company_id
        confidence
        matched_by
        industry
        title_id
    """

    experiences = candidate_profile.get("experience", [])

    if not experiences:
        return ""

    experience_text = []

    for experience in experiences:

        if isinstance(experience, str):

            if experience.strip():
                experience_text.append(
                    experience.strip()
                )

            continue

        if not isinstance(experience, dict):
            continue

        title = (
            experience.get("job_title")
            or experience.get("title")
            or experience.get("role")
            or ""
        )

        company = (
            experience.get("company")
            or experience.get("organization")
            or ""
        )

        description = (
            experience.get("description")
            or experience.get("summary")
            or experience.get("responsibilities")
            or experience.get("details")
            or ""
        )

        # Handle responsibility/description lists
        if isinstance(description, list):

            description = " ".join(
                str(item).strip()
                for item in description
                if item
            )

        text = _join_text(
            [
                title,
                company,
                description
            ]
        )

        if text:
            experience_text.append(text)

    return " ".join(experience_text).strip()


def build_resume_project_text(
    candidate_profile: Dict[str, Any]
) -> str:
    """
    Build clean text representation of projects.
    """

    projects = candidate_profile.get("projects", [])

    if not projects:
        return ""

    project_text = []

    for project in projects:

        if isinstance(project, str):

            if project.strip():
                project_text.append(
                    project.strip()
                )

            continue

        if not isinstance(project, dict):
            continue

        name = (
            project.get("name")
            or project.get("project_name")
            or ""
        )

        description = (
            project.get("description")
            or project.get("summary")
            or project.get("details")
            or ""
        )

        technologies = (
            project.get("technologies")
            or project.get("tech_stack")
            or project.get("skills")
            or []
        )

        text = _join_text(
            [
                name,
                description,
                technologies
            ]
        )

        if text:
            project_text.append(text)

    return " ".join(project_text).strip()


# ============================================================
# JD Section Builders
# ============================================================

def build_jd_skill_text(
    job_description: Dict[str, Any]
) -> str:
    """
    Build clean JD skill text.
    """

    required_skills = job_description.get(
        "required_skills",
        []
    )

    preferred_skills = job_description.get(
        "preferred_skills",
        []
    )

    return _join_text(
        [
            "Required skills",
            required_skills,
            "Preferred skills",
            preferred_skills
        ]
    )


def build_jd_experience_text(
    job_description: Dict[str, Any]
) -> str:
    """
    Build JD experience requirement text.
    """

    experience = (
        job_description.get("experience_summary")
        or job_description.get("experience")
        or job_description.get("experience_requirements")
        or job_description.get("experience_required")
        or ""
    )

    return _safe_text(experience)


def build_jd_project_text(
    job_description: Dict[str, Any]
) -> str:
    """
    Build JD project/work responsibility text.
    """

    project_description = (
        job_description.get("project_description")
        or job_description.get("project_requirements")
        or job_description.get("responsibilities")
        or job_description.get("description")
        or job_description.get("job_description")
        or ""
    )

    return _safe_text(project_description)


# ============================================================
# Single Section Embedding
# ============================================================

def _generate_section_embedding(
    text: str
) -> Optional[Any]:
    """
    Generate embedding only when text exists.

    This function should NOT access candidate_profile
    or job_description.

    It receives already-cleaned section text.
    """

    if not text:
        return None

    return _embedding_generator.generate_embedding(
        text
    )


# ============================================================
# Resume Section Embeddings
# ============================================================

def generate_resume_section_embeddings(
    candidate_profile: Dict[str, Any]
) -> Dict[str, Optional[Any]]:
    """
    Generate embeddings for resume sections.
    """

    sections = {

        "skills":
            build_resume_skill_text(
                candidate_profile
            ),

        "experience":
            build_resume_experience_text(
                candidate_profile
            ),

        "projects":
            build_resume_project_text(
                candidate_profile
            )
    }

    embeddings = {}

    for section, text in sections.items():

        print(
            f"\n===== RESUME {section.upper()} ====="
        )

        print(text)

        embeddings[section] = (
            _generate_section_embedding(text)
        )

    return embeddings


# ============================================================
# JD Section Embeddings
# ============================================================

def generate_jd_section_embeddings(
    job_description: Dict[str, Any]
) -> Dict[str, Optional[Any]]:
    """
    Generate embeddings for JD sections.
    """

    sections = {

        "skills":
            build_jd_skill_text(
                job_description
            ),

        "experience":
            build_jd_experience_text(
                job_description
            ),

        "projects":
            build_jd_project_text(
                job_description
            )
    }

    embeddings = {}

    for section, text in sections.items():

        print(
            f"\n===== JD {section.upper()} ====="
        )

        print(text)

        embeddings[section] = (
            _generate_section_embedding(text)
        )

    return embeddings


# ============================================================
# Complete Section Embedding Pipeline
# ============================================================

def generate_section_embeddings(
    candidate_profile: Dict[str, Any],
    job_description: Dict[str, Any]
) -> Dict[str, Dict[str, Optional[Any]]]:
    """
    Generate section-level embeddings for both
    candidate resume and job description.

    Returns:

    {
        "resume": {
            "skills": embedding,
            "experience": embedding,
            "projects": embedding
        },

        "jd": {
            "skills": embedding,
            "experience": embedding,
            "projects": embedding
        }
    }
    """

    resume_embeddings = (
        generate_resume_section_embeddings(
            candidate_profile
        )
    )

    jd_embeddings = (
        generate_jd_section_embeddings(
            job_description
        )
    )

    return {
        "resume": resume_embeddings,
        "jd": jd_embeddings
    }
