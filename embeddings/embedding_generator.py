from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:

    def __init__(self):
        print("Loading embedding model: all-MiniLM-L6-v2")

        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        print("Embedding model loaded successfully.")

    def generate_embedding(self, text):
        """Generate embedding for text."""

        return self.model.encode(
            text,
            normalize_embeddings=True
        )

    def candidate_to_text(self, candidate):
        """Convert candidate profile JSON to text."""

        parts = []

        personal = candidate.get(
            "personal_information",
            {}
        )

        if personal.get("name"):
            parts.append(
                personal["name"]
            )

        # Skills
        skills = candidate.get(
            "skills",
            []
        )

        for skill in skills:

            if isinstance(skill, dict):

                name = skill.get("name")

                if name:
                    parts.append(str(name))

            elif isinstance(skill, str):

                parts.append(skill)

        # Experience
        experiences = candidate.get(
            "experience",
            []
        )

        for experience in experiences:

            if not isinstance(experience, dict):
                continue

            company = experience.get("company")

            if company:
                parts.append(str(company))

            job_title = (
                experience.get("job_title")
                or experience.get("role")
                or experience.get("title")
            )

            if job_title:
                parts.append(str(job_title))

            description = experience.get("description")

            if isinstance(description, list):

                parts.extend(
                    str(item)
                    for item in description
                    if item
                )

            elif description:

                parts.append(
                    str(description)
                )

            summary = experience.get("summary")

            if summary:
                parts.append(str(summary))

        # Education
        education = candidate.get(
            "education",
            []
        )

        for edu in education:

            if isinstance(edu, dict):

                for key in [
                    "degree",
                    "field_of_study",
                    "institution"
                ]:

                    value = edu.get(key)

                    if value:
                        parts.append(
                            str(value)
                        )

        # Certifications
        certifications = candidate.get(
            "certifications",
            []
        )

        for certification in certifications:

            if isinstance(certification, dict):

                name = certification.get("name")

                if name:
                    parts.append(
                        str(name)
                    )

            elif isinstance(certification, str):

                parts.append(certification)

        return " ".join(parts)

    def job_to_text(self, job):
        """Convert JD JSON to text."""

        parts = []

        for key in [
            "job_title",
            "summary",
            "description",
            "responsibilities",
            "required_skills",
            "preferred_skills",
            "qualifications",
            "experience_required"
        ]:

            value = job.get(key)

            if isinstance(value, list):

                parts.extend(
                    str(item)
                    for item in value
                )

            elif value:

                parts.append(
                    str(value)
                )

        return " ".join(parts)

    def generate_candidate_embedding(
        self,
        candidate
    ):
        """Generate embedding for candidate."""

        text = self.candidate_to_text(
            candidate
        )

        print(
            "Candidate text:",
            text
        )

        return self.generate_embedding(text)

    def generate_jd_embedding(
        self,
        job
    ):
        """Generate embedding for JD."""

        text = self.job_to_text(
            job
        )

        print(
            "JD text:",
            text
        )

        return self.generate_embedding(text)