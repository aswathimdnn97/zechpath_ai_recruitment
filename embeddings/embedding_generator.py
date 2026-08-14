from typing import Any, Dict
from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:

    def __init__(
        self,
        model_name="all-MiniLM-L6-v2"
    ):
        self.model = SentenceTransformer(
            model_name
        )

    def _profile_to_text(
        self,
        profile: Dict[str, Any]
    ) -> str:

        if not isinstance(profile, dict):
            return ""

        # Handle resume_text wrapper
        data = profile.get(
            "resume_text",
            profile
        )

        if not isinstance(data, dict):
            return ""

        parts = []

        # Skills
        skills = data.get("skills", [])

        if isinstance(skills, list):

            for skill in skills:

                if isinstance(skill, str):
                    parts.append(skill)

                elif isinstance(skill, dict):

                    name = (
                        skill.get("skill")
                        or skill.get("name")
                        or skill.get("canonical_name")
                    )

                    if name:
                        parts.append(str(name))

        # Experience
        experience = data.get(
            "experience",
            []
        )

        if isinstance(experience, list):

            for item in experience:

                if not isinstance(item, dict):
                    continue

                title = item.get("title")

                if isinstance(title, dict):
                    title = title.get("title")

                if title:
                    parts.append(str(title))

                descriptions = item.get(
                    "description",
                    []
                )

                if isinstance(descriptions, list):
                    parts.extend(
                        str(x)
                        for x in descriptions
                        if x
                    )

                elif descriptions:
                    parts.append(
                        str(descriptions)
                    )

        # Education
        education = data.get(
            "education",
            []
        )

        if isinstance(education, list):

            for item in education:

                if isinstance(item, dict):

                    for key in (
                        "degree_type",
                        "degree",
                        "field_of_study",
                        "field",
                        "institution"
                    ):

                        value = item.get(key)

                        if value:
                            parts.append(
                                str(value)
                            )

                elif isinstance(item, str):
                    parts.append(item)

        # Projects
        projects = data.get(
            "projects",
            []
        )

        if isinstance(projects, list):

            for project in projects:

                if isinstance(project, dict):

                    for key in (
                        "name",
                        "title",
                        "description"
                    ):

                        value = project.get(key)

                        if value:
                            parts.append(
                                str(value)
                            )

                elif isinstance(project, str):
                    parts.append(project)

        return " ".join(parts)

    # ========================================================
    # Generic embedding
    # ========================================================

    def generate_embedding(self, profile):

        if isinstance(profile, dict):

            text = self._profile_to_text(
                profile
            )

        else:

            text = str(profile)

        if not text.strip():
            raise ValueError(
                "Cannot generate embedding from empty text"
            )

        return self.model.encode(
            text,
            convert_to_numpy=True
        )

    # ========================================================
    # Candidate embedding
    # ========================================================

    def generate_candidate_embedding(
        self,
        candidate_profile
    ):

        return self.generate_embedding(
            candidate_profile
        )

    # ========================================================
    # JD embedding
    # ========================================================

    def generate_jd_embedding(
        self,
        jd_profile
    ):

        return self.generate_embedding(
            jd_profile
        )