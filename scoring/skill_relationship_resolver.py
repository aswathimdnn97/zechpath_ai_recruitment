"""
Skill Relationship Resolver

Purpose:
    Loads skill relationship information from
    data/resume/skills/skill_relationships.json and provides
    reusable methods for identifying relationships between skills.

Supported relationship types:
    - broader
    - related

Important:
    Relationships are directional.

Example:
    REST API -> broader -> API

This means:
    REST API can provide evidence for API.

But:
    API -> REST API

is NOT automatically considered a match.

The resolver does NOT treat "related" skills as exact matches.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SkillRelationshipResolver:
    """
    Resolve relationships between technical skills using
    a data-driven JSON relationship dictionary.
    """

    def __init__(
        self,
        relationship_file: Optional[str | Path] = None,
    ) -> None:
        """
        Initialize the resolver.

        Args:
            relationship_file:
                Optional custom path to skill_relationships.json.

                If not provided, the resolver automatically looks for:
                    data/resume/skills/skill_relationships.json
        """

        self.relationship_file = self._resolve_relationship_file(
            relationship_file
        )

        self.relationships: Dict[str, Dict[str, List[str]]] = {}

        self._load_relationships()

    # ------------------------------------------------------------------
    # FILE HANDLING
    # ------------------------------------------------------------------

    def _resolve_relationship_file(
        self,
        relationship_file: Optional[str | Path],
    ) -> Path:
        """
        Resolve the relationship JSON path.

        Supports both:
            - absolute paths
            - project-relative paths
        """

        if relationship_file:
            path = Path(relationship_file)

            if path.is_absolute():
                return path

            return Path.cwd() / path

        # Current file:
        # project/scoring/skill_relationship_resolver.py

        project_root = Path(__file__).resolve().parent.parent

        return (
            project_root
            / "data"
            / "resume"
            / "skills"
            / "skill_relationships.json"
        )

    def _load_relationships(self) -> None:
        """
        Load and validate skill relationships from JSON.
        """

        if not self.relationship_file.exists():
            raise FileNotFoundError(
                "Skill relationship file not found: "
                f"{self.relationship_file}"
            )

        try:
            with self.relationship_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid JSON in skill relationship file: "
                f"{self.relationship_file}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Skill relationship JSON must contain "
                "a top-level object/dictionary."
            )

        self.relationships = self._normalize_relationship_data(data)

    # ------------------------------------------------------------------
    # NORMALIZATION
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_skill(skill: Any) -> str:
        """
        Normalize a skill name for comparison.

        Example:
            " REST API " -> "rest api"
            "Python"     -> "python"
        """

        if not isinstance(skill, str):
            return ""

        return " ".join(skill.strip().lower().split())

    @staticmethod
    def _display_skill(skill: str) -> str:
        """
        Clean skill value while preserving original capitalization
        where possible.
        """

        if not isinstance(skill, str):
            return ""

        return " ".join(skill.strip().split())

    def _normalize_relationship_data(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Normalize the loaded JSON structure.

        Converts:

            {
                "REST API": {
                    "broader": ["API"],
                    "related": ["FastAPI"]
                }
            }

        into a normalized internal representation using lowercase
        comparison keys.
        """

        normalized: Dict[str, Dict[str, List[str]]] = {}

        for skill, relationship_data in data.items():

            normalized_skill = self._normalize_skill(skill)

            if not normalized_skill:
                continue

            if not isinstance(relationship_data, dict):
                continue

            broader = relationship_data.get("broader", [])
            related = relationship_data.get("related", [])

            if not isinstance(broader, list):
                broader = []

            if not isinstance(related, list):
                related = []

            normalized_broader = []

            for item in broader:
                normalized_item = self._normalize_skill(item)

                if normalized_item:
                    normalized_broader.append(normalized_item)

            normalized_related = []

            for item in related:
                normalized_item = self._normalize_skill(item)

                if normalized_item:
                    normalized_related.append(normalized_item)

            normalized[normalized_skill] = {
                "broader": list(dict.fromkeys(normalized_broader)),
                "related": list(dict.fromkeys(normalized_related)),
            }

        return normalized

    # ------------------------------------------------------------------
    # BASIC LOOKUPS
    # ------------------------------------------------------------------

    def skill_exists(self, skill: str) -> bool:
        """
        Check whether a skill exists in the relationship dictionary.

        Args:
            skill:
                Skill name.

        Returns:
            True if skill exists, otherwise False.
        """

        normalized_skill = self._normalize_skill(skill)

        if not normalized_skill:
            return False

        return normalized_skill in self.relationships

    def get_relationships(
        self,
        skill: str,
    ) -> Dict[str, List[str]]:
        """
        Return all relationships for a skill.

        Example:

            resolver.get_relationships("REST API")

        Returns:

            {
                "broader": ["api"],
                "related": [
                    "django rest framework",
                    "fastapi"
                ]
            }
        """

        normalized_skill = self._normalize_skill(skill)

        if not normalized_skill:
            return {
                "broader": [],
                "related": [],
            }

        relationship = self.relationships.get(normalized_skill)

        if not relationship:
            return {
                "broader": [],
                "related": [],
            }

        return {
            "broader": list(relationship.get("broader", [])),
            "related": list(relationship.get("related", [])),
        }

    # ------------------------------------------------------------------
    # BROADER RELATIONSHIP
    # ------------------------------------------------------------------

    def get_broader_skills(
        self,
        skill: str,
    ) -> List[str]:
        """
        Return skills that are broader categories of the given skill.

        Example:

            REST API -> API

        Therefore:

            get_broader_skills("REST API")

        returns:

            ["api"]
        """

        normalized_skill = self._normalize_skill(skill)

        if not normalized_skill:
            return []

        relationship = self.relationships.get(normalized_skill)

        if not relationship:
            return []

        return list(relationship.get("broader", []))

    def is_broader_relationship(
        self,
        candidate_skill: str,
        required_skill: str,
    ) -> bool:
        """
        Determine whether candidate_skill is a more specific skill
        under required_skill.

        Example:

            candidate = REST API
            required  = API

        Result:
            True

        But:

            candidate = API
            required  = REST API

        Result:
            False
        """

        candidate = self._normalize_skill(candidate_skill)
        required = self._normalize_skill(required_skill)

        if not candidate or not required:
            return False

        if candidate == required:
            return False

        broader_skills = self.get_broader_skills(candidate)

        return required in broader_skills

    # ------------------------------------------------------------------
    # RELATED RELATIONSHIP
    # ------------------------------------------------------------------

    def get_related_skills(
        self,
        skill: str,
    ) -> List[str]:
        """
        Return related skills.

        Important:
            Related skills should normally be used as contextual
            evidence and should NOT automatically count as an
            exact skill match.
        """

        normalized_skill = self._normalize_skill(skill)

        if not normalized_skill:
            return []

        relationship = self.relationships.get(normalized_skill)

        if not relationship:
            return []

        return list(relationship.get("related", []))

    def is_related(
        self,
        candidate_skill: str,
        required_skill: str,
    ) -> bool:
        """
        Check whether two skills are explicitly marked as related.

        This relationship is directional according to the JSON.

        Example:

            Python -> related -> Django

        Therefore:

            is_related("Python", "Django")

        may return True.

        This method should NOT be used as an automatic full skill match.
        """

        candidate = self._normalize_skill(candidate_skill)
        required = self._normalize_skill(required_skill)

        if not candidate or not required:
            return False

        if candidate == required:
            return False

        related_skills = self.get_related_skills(candidate)

        return required in related_skills

    # ------------------------------------------------------------------
    # DIRECT RELATIONSHIP
    # ------------------------------------------------------------------

    def get_relationship_type(
        self,
        candidate_skill: str,
        required_skill: str,
    ) -> Optional[str]:
        """
        Return the direct relationship type between two skills.

        Possible return values:

            "broader"
            "related"
            None

        Exact matches return None because exact matching should be
        handled separately by the skill scorer.
        """

        candidate = self._normalize_skill(candidate_skill)
        required = self._normalize_skill(required_skill)

        if not candidate or not required:
            return None

        if candidate == required:
            return None

        if self.is_broader_relationship(
            candidate,
            required,
        ):
            return "broader"

        if self.is_related(
            candidate,
            required,
        ):
            return "related"

        return None


    def resolve(
    self,
    candidate_skill: str,
    required_skill: str,
) -> Optional[Dict[str, Any]]:
        """
        Resolve the relationship between a candidate skill
        and a required skill.

        This method provides a common interface for the scoring
        pipeline.

        Returns:
            {
                "candidate_skill": "...",
                "required_skill": "...",
                "relationship": "broader" | "related",
                "matched": bool,
            }

        Exact matches return None because exact matching is handled
        separately by SkillScore.
        """

        relationship = self.get_relationship_type(
            candidate_skill,
            required_skill,
        )

        if relationship is None:
            return None

        return {
            "candidate_skill": candidate_skill,
            "required_skill": required_skill,
            "relationship": relationship,
            "matched": relationship == "broader",
        }
    # ------------------------------------------------------------------
    # MATCH INFORMATION
    # ------------------------------------------------------------------

    def get_match_information(
        self,
        candidate_skill: str,
        required_skill: str,
    ) -> Dict[str, Any]:
        """
        Return detailed relationship information.

        Example:

            {
                "candidate_skill": "REST API",
                "required_skill": "API",
                "matched": True,
                "relationship": "broader"
            }
        """

        candidate = self._display_skill(candidate_skill)
        required = self._display_skill(required_skill)

        normalized_candidate = self._normalize_skill(candidate)
        normalized_required = self._normalize_skill(required)

        if not normalized_candidate or not normalized_required:
            return {
                "candidate_skill": candidate,
                "required_skill": required,
                "matched": False,
                "relationship": None,
            }

        if normalized_candidate == normalized_required:
            return {
                "candidate_skill": candidate,
                "required_skill": required,
                "matched": True,
                "relationship": "exact",
            }

        relationship = self.get_relationship_type(
            normalized_candidate,
            normalized_required,
        )

        return {
            "candidate_skill": candidate,
            "required_skill": required,
            "matched": relationship is not None,
            "relationship": relationship,
        }

    # ------------------------------------------------------------------
    # SKILL MATCHING
    # ------------------------------------------------------------------

    def find_relationship_match(
        self,
        candidate_skills: List[str],
        required_skill: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the first meaningful relationship between a list of
        candidate skills and one required skill.

        Priority:

            1. broader
            2. related

        Exact matches are intentionally not returned here because
        exact matching belongs to the main skill matching pipeline.
        """

        if not isinstance(candidate_skills, list):
            return None

        normalized_required = self._normalize_skill(required_skill)

        if not normalized_required:
            return None

        # --------------------------------------------------------------
        # First pass: broader relationship
        # --------------------------------------------------------------

        for candidate_skill in candidate_skills:

            if not isinstance(candidate_skill, str):
                continue

            if self.is_broader_relationship(
                candidate_skill,
                normalized_required,
            ):
                return {
                    "candidate_skill": candidate_skill,
                    "required_skill": required_skill,
                    "relationship": "broader",
                    "matched": True,
                }

        # --------------------------------------------------------------
        # Second pass: related relationship
        # --------------------------------------------------------------

        for candidate_skill in candidate_skills:

            if not isinstance(candidate_skill, str):
                continue

            if self.is_related(
                candidate_skill,
                normalized_required,
            ):
                return {
                    "candidate_skill": candidate_skill,
                    "required_skill": required_skill,
                    "relationship": "related",
                    "matched": True,
                }

        return None

    # ------------------------------------------------------------------
    # ALL RELATED INFORMATION
    # ------------------------------------------------------------------

    def get_all_relationships(
        self,
        skill: str,
    ) -> Dict[str, List[str]]:
        """
        Return a complete relationship map for a skill.

        This is mainly useful for debugging, testing, and
        explainability.
        """

        normalized_skill = self._normalize_skill(skill)

        if not normalized_skill:
            return {
                "broader": [],
                "related": [],
            }

        return self.get_relationships(normalized_skill)

    # ------------------------------------------------------------------
    # DEBUG / VALIDATION
    # ------------------------------------------------------------------

    def validate_relationships(self) -> Dict[str, Any]:
        """
        Validate the relationship dictionary.

        Checks for:
            - empty skill names
            - invalid relationship lists
            - duplicate values
            - self relationships

        Returns a validation report instead of raising an exception.
        """

        report = {
            "valid": True,
            "total_skills": len(self.relationships),
            "warnings": [],
        }

        for skill, relationship_data in self.relationships.items():

            for relationship_type in ("broader", "related"):

                values = relationship_data.get(
                    relationship_type,
                    [],
                )

                if not isinstance(values, list):
                    report["valid"] = False

                    report["warnings"].append(
                        f"{skill}: {relationship_type} "
                        "must be a list."
                    )

                    continue

                if skill in values:
                    report["valid"] = False

                    report["warnings"].append(
                        f"{skill}: self-reference found in "
                        f"{relationship_type}."
                    )

                if len(values) != len(set(values)):
                    report["valid"] = False

                    report["warnings"].append(
                        f"{skill}: duplicate values found in "
                        f"{relationship_type}."
                    )

        return report


# ----------------------------------------------------------------------
# OPTIONAL DEFAULT INSTANCE
# ----------------------------------------------------------------------

_default_resolver: Optional[SkillRelationshipResolver] = None


def get_skill_relationship_resolver() -> SkillRelationshipResolver:
    """
    Return a shared resolver instance.

    This avoids loading skill_relationships.json repeatedly when
    multiple scoring components use the resolver.
    """

    global _default_resolver

    if _default_resolver is None:
        _default_resolver = SkillRelationshipResolver()

    return _default_resolver
