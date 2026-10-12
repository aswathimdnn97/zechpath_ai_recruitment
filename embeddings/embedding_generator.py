from threading import Lock
from typing import Any, Dict

from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """
    Production embedding generator.

    Responsibilities
    ----------------
    1. Load SentenceTransformer model once per process.
    2. Generate candidate embeddings.
    3. Generate JD embeddings.
    4. Reuse the same embedding model for candidates and JDs.

    Default model:
        all-MiniLM-L6-v2

    Notes
    -----
    The model is cached at class level so creating multiple
    EmbeddingGenerator instances does not reload the model.
    """

    DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

    _models: Dict[str, SentenceTransformer] = {}
    _model_lock = Lock()

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
    ):
        self.model_name = model_name
        self.model = self._get_model(model_name)

    # ============================================================
    # MODEL MANAGEMENT
    # ============================================================

    @classmethod
    def _get_model(
        cls,
        model_name: str,
    ) -> SentenceTransformer:
        """
        Return a cached SentenceTransformer model.

        The model is loaded only once per model name and
        reused by all EmbeddingGenerator instances in the
        same Python process.
        """

        # Fast path: model already loaded.
        model = cls._models.get(model_name)

        if model is not None:
            return model

        # Thread-safe model initialization.
        with cls._model_lock:

            # Check again after acquiring the lock.
            model = cls._models.get(model_name)

            if model is not None:
                return model

            model = SentenceTransformer(
                model_name
            )

            cls._models[model_name] = model

            return model

    # ============================================================
    # PROFILE → EMBEDDING TEXT
    # ============================================================

    def _profile_to_text(
        self,
        profile: Dict[str, Any],
    ) -> str:
        """
        Convert candidate/JD structured data into embedding text.

        The method intentionally preserves the existing
        candidate/JD embedding structure.
        """

        if not isinstance(profile, dict):
            return ""

        # Handle resume_text wrapper.
        data = profile.get(
            "resume_text",
            profile,
        )

        if not isinstance(data, dict):
            return ""

        parts = []

        # ========================================================
        # SKILLS
        # ========================================================

        skills = data.get(
            "skills",
            [],
        )

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

        # ========================================================
        # EXPERIENCE
        # ========================================================

        experience = data.get(
            "experience",
            [],
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
                    [],
                )

                if isinstance(descriptions, list):

                    parts.extend(
                        str(description)
                        for description in descriptions
                        if description
                    )

                elif descriptions:

                    parts.append(
                        str(descriptions)
                    )

        # ========================================================
        # EDUCATION
        # ========================================================

        education = data.get(
            "education",
            [],
        )

        if isinstance(education, list):

            for item in education:

                if isinstance(item, dict):

                    for key in (
                        "degree_type",
                        "degree",
                        "field_of_study",
                        "field",
                        "institution",
                    ):

                        value = item.get(key)

                        if value:
                            parts.append(str(value))

                elif isinstance(item, str):

                    parts.append(item)

        # ========================================================
        # PROJECTS
        # ========================================================

        projects = data.get(
            "projects",
            [],
        )

        if isinstance(projects, list):

            for project in projects:

                if isinstance(project, dict):

                    for key in (
                        "name",
                        "title",
                        "description",
                    ):

                        value = project.get(key)

                        if value:
                            parts.append(str(value))

                elif isinstance(project, str):

                    parts.append(project)

        return " ".join(parts)

    # ============================================================
    # GENERIC EMBEDDING
    # ============================================================

    def generate_embedding(
        self,
        profile: Any,
    ):
        """
        Generate an embedding for structured profile data
        or plain text.
        """

        if isinstance(profile, dict):

            text = self._profile_to_text(profile)

        else:

            text = str(profile)

        text = text.strip()

        if not text:
            raise ValueError(
                "Cannot generate embedding from empty text"
            )

        return self.model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    # ============================================================
    # CANDIDATE EMBEDDING
    # ============================================================

    def generate_candidate_embedding(
        self,
        candidate_profile: Dict[str, Any],
    ):
        """
        Generate embedding for a candidate profile.
        """

        return self.generate_embedding(
            candidate_profile
        )

    # ============================================================
    # JD EMBEDDING
    # ============================================================

    def generate_jd_embedding(
        self,
        jd_profile: Dict[str, Any],
    ):
        """
        Generate embedding for a job description.
        """

        return self.generate_embedding(
            jd_profile
        )