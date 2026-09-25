"""
Skill Scorer

Responsibilities:
    - Extract candidate skills
    - Extract required and preferred JD skills
    - Match candidate skills against JD skills
    - Support:
        1. Exact matching
        2. Relationship matching
        3. Fuzzy matching
        4. Semantic matching
    - Calculate required/preferred skill scores
    - Return explainable scoring results

Matching priority:
    Exact
        ↓
    Broader relationship
        ↓
    Fuzzy
        ↓
    Semantic
        ↓
    Missing

Important:
    "related" skills from skill_relationships.json are NOT treated
    as automatic matches.

Example:
    Candidate: REST API
    Required: API

    REST API -> broader -> API

    This can receive relationship credit.

But:

    Candidate: PostgreSQL
    Required: MySQL

    PostgreSQL -> related -> MySQL

    This is NOT counted as a skill match.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from scoring.semantic_scorer import find_semantic_skill_matches
from scoring.skill_relationship_resolver import (
    SkillRelationshipResolver,
)


# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------

FUZZY_MATCH_THRESHOLD = 90

REQUIRED_WEIGHT = 0.80
PREFERRED_WEIGHT = 0.20

FUZZY_MATCH_CONFIDENCE = 0.90

SEMANTIC_MATCH_MIN_THRESHOLD = 0.70


class SkillScore:
    """
    Calculate candidate skill match score against a job description.
    """

    def __init__(
        self,
        relationship_resolver: Optional[
            SkillRelationshipResolver
        ] = None,
    ) -> None:
        """
        Initialize the skill scorer.

        Args:
            relationship_resolver:
                Optional shared SkillRelationshipResolver.

                If not supplied, a new resolver is created.
        """

        self.relationship_resolver = (
            relationship_resolver
            if relationship_resolver is not None
            else SkillRelationshipResolver()
        )

    # ------------------------------------------------------------------
    # NORMALIZATION
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_skill(skill: Any) -> str:
        """
        Normalize a skill for comparison.

        Example:
            " Python " -> "python"
            "REST   API" -> "rest api"
        """

        if not isinstance(skill, str):
            return ""

        return " ".join(
            skill.strip().lower().split()
        )

    # ------------------------------------------------------------------
    # SKILL SIMILARITY
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_skill_similarity(
        candidate_skill: str,
        required_skill: str,
    ) -> float:
        """
        Calculate fuzzy similarity between two skills.

        Uses:
            - fuzz.ratio
            - fuzz.token_sort_ratio

        token_set_ratio is intentionally avoided because it can
        produce false perfect matches.

        Example problem:

            "django"
            "django rest framework"

        token_set_ratio can consider these too similar.
        """

        candidate = SkillScore._normalize_skill(
            candidate_skill
        )

        required = SkillScore._normalize_skill(
            required_skill
        )

        if not candidate or not required:
            return 0.0

        ratio_score = fuzz.ratio(
            candidate,
            required,
        )

        token_sort_score = fuzz.token_sort_ratio(
            candidate,
            required,
        )

        return max(
            float(ratio_score),
            float(token_sort_score),
        )

    # ------------------------------------------------------------------
    # EXTRACT SKILL NAMES
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_skill_names(
        skills: Any,
    ) -> List[str]:
        """
        Extract skill names from either:

            [
                "Python",
                "Django"
            ]

        or:

            [
                {
                    "skill": "Python"
                },
                {
                    "name": "Django"
                }
            ]

        Supported dictionary keys:
            - skill
            - name
            - canonical_name
        """

        if not isinstance(skills, list):
            return []

        extracted: List[str] = []

        for skill in skills:

            # ----------------------------------------------------------
            # String skill
            # ----------------------------------------------------------

            if isinstance(skill, str):

                value = skill.strip()

                if value:
                    extracted.append(value)

                continue

            # ----------------------------------------------------------
            # Dictionary skill
            # ----------------------------------------------------------

            if isinstance(skill, dict):

                value = (
                    skill.get("skill")
                    or skill.get("name")
                    or skill.get("canonical_name")
                )

                if isinstance(value, str):

                    value = value.strip()

                    if value:
                        extracted.append(value)

        return extracted

    # ------------------------------------------------------------------
    # CANDIDATE SKILL EXTRACTION
    # ------------------------------------------------------------------

    def _extract_candidate_skills(
        self,
        profile: Dict[str, Any],
    ) -> List[str]:
        """
        Extract candidate skills from:

            profile["skills"]

        and skills inside:

            profile["experience"][...]["skills"]

        Duplicate skills are removed while preserving order.
        """

        if not isinstance(profile, dict):
            return []

        candidate_skills: List[str] = []

        # --------------------------------------------------------------
        # Top-level skills
        # --------------------------------------------------------------

        top_level_skills = profile.get(
            "skills",
            [],
        )

        candidate_skills.extend(
            self._extract_skill_names(
                top_level_skills
            )
        )

        # --------------------------------------------------------------
        # Experience skills
        # --------------------------------------------------------------

        experience = profile.get(
            "experience",
            [],
        )

        if isinstance(experience, list):

            for experience_item in experience:

                if not isinstance(
                    experience_item,
                    dict,
                ):
                    continue

                experience_skills = experience_item.get(
                    "skills",
                    [],
                )

                candidate_skills.extend(
                    self._extract_skill_names(
                        experience_skills
                    )
                )

        # --------------------------------------------------------------
        # Remove duplicates
        # --------------------------------------------------------------

        unique_skills: List[str] = []

        seen = set()

        for skill in candidate_skills:

            normalized = self._normalize_skill(
                skill
            )

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)

            unique_skills.append(skill)

        return unique_skills

    # ------------------------------------------------------------------
    # PROFILE DATA
    # ------------------------------------------------------------------

    @staticmethod
    def _get_profile_data(
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Return the actual candidate profile data.

        Supports both:

            profile = {
                "skills": [...]
            }

        and:

            profile = {
                "resume_text": {
                    "skills": [...]
                }
            }
        """

        if not isinstance(profile, dict):
            return {}

        resume_text = profile.get(
            "resume_text"
        )

        if isinstance(
            resume_text,
            dict,
        ):
            return resume_text

        return profile

    # ------------------------------------------------------------------
    # REQUIRED / PREFERRED SKILLS
    # ------------------------------------------------------------------

    def _extract_required_skills(
        self,
        job_description: Dict[str, Any],
    ) -> List[str]:
        """
        Extract required skills from JD.
        """

        if not isinstance(
            job_description,
            dict,
        ):
            return []

        return self._extract_skill_names(
            job_description.get(
                "required_skills",
                [],
            )
        )

    def _extract_preferred_skills(
        self,
        job_description: Dict[str, Any],
    ) -> List[str]:
        """
        Extract preferred skills from JD.
        """

        if not isinstance(
            job_description,
            dict,
        ):
            return []

        return self._extract_skill_names(
            job_description.get(
                "preferred_skills",
                [],
            )
        )

    # ------------------------------------------------------------------
    # EXACT MATCH
    # ------------------------------------------------------------------

    def _find_exact_match(
        self,
        candidate_skills: List[str],
        required_skill: str,
    ) -> Optional[str]:
        """
        Find an exact normalized skill match.
        """

        required_normalized = self._normalize_skill(
            required_skill
        )

        if not required_normalized:
            return None

        for candidate_skill in candidate_skills:

            candidate_normalized = self._normalize_skill(
                candidate_skill
            )

            if (
                candidate_normalized
                == required_normalized
            ):
                return candidate_skill

        return None

    # ------------------------------------------------------------------
    # RELATIONSHIP MATCH
    # ------------------------------------------------------------------

    def _find_relationship_match(
        self,
        candidate_skills: List[str],
        required_skill: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a data-driven relationship match.

        Only "broader" relationships are allowed to satisfy a
        required skill.

        "related" relationships are intentionally ignored as
        scoring matches.

        Example:

            Candidate:
                REST API

            Required:
                API

            Relationship:
                REST API -> broader -> API

        Result:

            {
                "candidate_skill": "REST API",
                "required_skill": "API",
                "relationship": "broader",
                "matched": True
            }
        """

        if not candidate_skills:
            return None

        for candidate_skill in candidate_skills:

            relationship_type = (
                self.relationship_resolver.get_relationship_type(
                    candidate_skill,
                    required_skill,
                )
            )

            # ----------------------------------------------------------
            # Only broader relationships receive match status.
            # ----------------------------------------------------------

            if relationship_type == "broader":

                return {
                    "candidate_skill": candidate_skill,
                    "required_skill": required_skill,
                    "relationship": "broader",
                    "matched": True,
                }

        return None

    # ------------------------------------------------------------------
    # RELATED SKILL INFORMATION
    # ------------------------------------------------------------------

    def _find_related_skill_context(
        self,
        candidate_skills: List[str],
        required_skill: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Detect related skills for explainability.

        Related skills are NOT counted as matches.

        Example:

            Candidate:
                PostgreSQL

            Required:
                MySQL

            Result:

                {
                    "candidate_skill": "PostgreSQL",
                    "required_skill": "MySQL",
                    "relationship": "related",
                    "matched": False
                }
        """

        if not candidate_skills:
            return None

        for candidate_skill in candidate_skills:

            relationship_type = (
                self.relationship_resolver.get_relationship_type(
                    candidate_skill,
                    required_skill,
                )
            )

            if relationship_type == "related":

                return {
                    "candidate_skill": candidate_skill,
                    "required_skill": required_skill,
                    "relationship": "related",
                    "matched": False,
                }

        return None

    # ------------------------------------------------------------------
    # FUZZY MATCH
    # ------------------------------------------------------------------

    def _find_fuzzy_match(
        
        self,
        candidate_skills: List[str],
        required_skill: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best fuzzy candidate skill.

        Returns a match only when the score reaches
        FUZZY_MATCH_THRESHOLD.
        """

        best_candidate: Optional[str] = None
        best_score = 0.0

        for candidate_skill in candidate_skills:

            similarity = self._calculate_skill_similarity(
                candidate_skill,
                required_skill,
            )

            if similarity > best_score:

                best_score = similarity
                best_candidate = candidate_skill

        if (
            best_candidate is not None
            and best_score >= FUZZY_MATCH_THRESHOLD
        ):

            return {
                "candidate_skill": best_candidate,
                "required_skill": required_skill,
                "similarity": round(
                    best_score / 100,
                    4,
                ),
                "similarity_percentage": round(
                    best_score,
                    2,
                ),
                "confidence": FUZZY_MATCH_CONFIDENCE,
                "matched": True,
            }

        return None

    # ------------------------------------------------------------------
    # SEMANTIC MATCH
    # ------------------------------------------------------------------

    def _find_semantic_match(
        self,
        candidate_skills: List[str],
        required_skill: str,
        embedding_generator: Any = None,
        ) -> Optional[Dict[str, Any]]:
        
        
      
    
        """
        Find semantic skill matches using the existing
        semantic_scorer implementation.
        """

        if not candidate_skills:
            return None

        try:
            semantic_matches = find_semantic_skill_matches(
                candidate_skills,
                [required_skill],
                embedding_generator=embedding_generator,
                threshold=SEMANTIC_MATCH_MIN_THRESHOLD,
            )

        except Exception:
            # Semantic matching should not break the entire ATS
            # scoring pipeline.
            return None

        if not semantic_matches:
            return None

        # ----------------------------------------------------------
        # Current semantic_scorer returns:
        #
        # {
        #     "semantic_matches": [...],
        #     "unmatched_required_skills": [...],
        #     "scores": {...}
        # }
        # ----------------------------------------------------------

        if isinstance(semantic_matches, dict):

            matches = semantic_matches.get(
                "semantic_matches",
                []
            )

            if isinstance(matches, list):

                best_match = None

                for item in matches:

                    if not isinstance(item, dict):
                        continue

                    candidate_skill = (
                        item.get("candidate_skill")
                        or item.get("skill")
                        or item.get("candidate")
                    )

                    similarity = item.get(
                        "similarity",
                        item.get("score")
                    )

                    if not isinstance(
                        similarity,
                        (int, float)
                    ):
                        continue

                    if float(similarity) < SEMANTIC_MATCH_MIN_THRESHOLD:
                        continue

                    if (
                        best_match is None
                        or float(similarity) > best_match["similarity"]
                    ):
                        best_match = {
                            "candidate_skill": candidate_skill,
                            "similarity": float(similarity),
                        }

                if best_match is not None:

                    return {
                        "candidate_skill": best_match[
                            "candidate_skill"
                        ],
                        "required_skill": required_skill,
                        "similarity": round(
                            best_match["similarity"],
                            4
                        ),
                        "matched": True,
                    }

        return None
    # ------------------------------------------------------------------
    # MAIN MATCH FUNCTION
    # ------------------------------------------------------------------

    def _match_skills(
    self,
    candidate_skills: List[str],
    required_skills: List[str],
    embedding_generator: Any = None,
) -> Dict[str, Any]:
        """
        Match candidate skills against required skills.

        Matching priority:

            1. Exact
            2. Broader relationship
            3. Fuzzy
            4. Semantic
            5. Missing

        Related skills are reported separately and are not counted
        as successful matches.
        """

        exact_matches: List[str] = []
        relationship_matches: List[Dict[str, Any]] = []
        fuzzy_matches: List[Dict[str, Any]] = []
        semantic_matches: List[Dict[str, Any]] = []
        related_skill_context: List[Dict[str, Any]] = []
        missing_skills: List[str] = []

        matched_required_skills: List[str] = []

        used_candidate_skills = set()

        # --------------------------------------------------------------
        # Process every required skill
        # --------------------------------------------------------------

        for required_skill in required_skills:

            # ==========================================================
            # 1. EXACT MATCH
            # ==========================================================

            exact_candidate = self._find_exact_match(
                candidate_skills,
                required_skill,
            )

            if exact_candidate is not None:

                normalized_candidate = self._normalize_skill(
                    exact_candidate
                )

                if normalized_candidate not in used_candidate_skills:

                    exact_matches.append(
                        exact_candidate
                    )

                    matched_required_skills.append(
                        required_skill
                    )

                    used_candidate_skills.add(
                        normalized_candidate
                    )

                    continue

            # ==========================================================
            # 2. BROADER RELATIONSHIP MATCH
            # ==========================================================

            relationship_match = (
                self._find_relationship_match(
                    candidate_skills,
                    required_skill,
                )
            )

            if relationship_match is not None:

                relationship_candidate = (
                    relationship_match[
                        "candidate_skill"
                    ]
                )

                normalized_candidate = (
                    self._normalize_skill(
                        relationship_candidate
                    )
                )

                if (
                    normalized_candidate
                    not in used_candidate_skills
                ):

                    relationship_matches.append(
                        relationship_match
                    )

                    matched_required_skills.append(
                        required_skill
                    )

                    used_candidate_skills.add(
                        normalized_candidate
                    )

                    continue

            # ==========================================================
            # RELATED CONTEXT
            # ==========================================================

            related_context = (
                self._find_related_skill_context(
                    candidate_skills,
                    required_skill,
                )
            )

            if related_context is not None:

                related_skill_context.append(
                    related_context
                )

            # ==========================================================
            # 3. FUZZY MATCH
            # ==========================================================

            fuzzy_match = self._find_fuzzy_match(
                candidate_skills,
                required_skill,
            )

            if fuzzy_match is not None:

                fuzzy_candidate = (
                    fuzzy_match[
                        "candidate_skill"
                    ]
                )

                normalized_candidate = (
                    self._normalize_skill(
                        fuzzy_candidate
                    )
                )

                if (
                    normalized_candidate
                    not in used_candidate_skills
                ):

                    fuzzy_matches.append(
                        fuzzy_match
                    )

                    matched_required_skills.append(
                        required_skill
                    )

                    used_candidate_skills.add(
                        normalized_candidate
                    )

                    continue

            # ==========================================================
            # 4. SEMANTIC MATCH
            # ==========================================================

            semantic_match = self._find_semantic_match(
                candidate_skills,
                required_skill,
                embedding_generator=embedding_generator,
            )

            if semantic_match is not None:

                semantic_candidate = (
                    semantic_match.get(
                        "candidate_skill",
                        "",
                    )
                )

                normalized_candidate = (
                    self._normalize_skill(
                        semantic_candidate
                    )
                )

                if (
                    normalized_candidate
                    and normalized_candidate
                    not in used_candidate_skills
                ):

                    semantic_matches.append(
                        semantic_match
                    )

                    matched_required_skills.append(
                        required_skill
                    )

                    used_candidate_skills.add(
                        normalized_candidate
                    )

                    continue

            # ==========================================================
            # 5. MISSING
            # ==========================================================

            missing_skills.append(
                required_skill
            )

        # --------------------------------------------------------------
        # Match counts
        # --------------------------------------------------------------

        total_required = len(
            required_skills
        )

        matched_required = len(
            matched_required_skills
        )

        required_match_percentage = (
            (
                matched_required
                / total_required
            ) * 100
            if total_required > 0
            else 0.0
        )

        return {
            "exact_matches": exact_matches,
            "relationship_matches": relationship_matches,
            "fuzzy_matches": fuzzy_matches,
            "semantic_matches": semantic_matches,
            "related_skill_context": related_skill_context,
            "missing_skills": missing_skills,

            "matched_required_skills": (
                matched_required_skills
            ),

            "total_required_skills": (
                total_required
            ),

            "matched_required_skills_count": (
                matched_required
            ),

            "required_match_percentage": round(
                required_match_percentage,
                2,
            ),
        }

    # ------------------------------------------------------------------
    # PREFERRED SKILL MATCHING
    # ------------------------------------------------------------------

    def _match_preferred_skills(
        self,
        candidate_skills: List[str],
        preferred_skills: List[str],
        embedding_generator: Any = None,
    ) -> Dict[str, Any]:
        """
        Match preferred skills using the same matching pipeline.
        """

        return self._match_skills(
            candidate_skills,
            preferred_skills,
            embedding_generator=embedding_generator,
        )

    # ------------------------------------------------------------------
    # PUBLIC SCORING METHOD
    # ------------------------------------------------------------------

    def calculate_skill_score(
        self,
        profile: Dict[str, Any],
        job_description: Dict[str, Any],
        embedding_generator: Any = None,
    ) -> Dict[str, Any]:
        """
        Calculate the final skill score.

        Required skills:
            80%

        Preferred skills:
            20%

        If only required skills exist:
            required score is used.

        If only preferred skills exist:
            preferred score is used.

        If neither exists:
            score is 0.
        """

        # --------------------------------------------------------------
        # Get profile data
        # --------------------------------------------------------------

        profile_data = self._get_profile_data(
            profile
        )

        # --------------------------------------------------------------
        # Extract skills
        # --------------------------------------------------------------

        candidate_skills = (
            self._extract_candidate_skills(
                profile_data
            )
        )

        required_skills = (
            self._extract_required_skills(
                job_description
            )
        )

        preferred_skills = (
            self._extract_preferred_skills(
                job_description
            )
        )

        # --------------------------------------------------------------
        # Match required skills
        # --------------------------------------------------------------

        required_results = self._match_skills(
            candidate_skills,
            required_skills,
            embedding_generator=embedding_generator,
        )

        # --------------------------------------------------------------
        # Match preferred skills
        # --------------------------------------------------------------

        preferred_results = (
            self._match_preferred_skills(
                candidate_skills,
                preferred_skills,
                embedding_generator=embedding_generator,
            )
        )

        # --------------------------------------------------------------
        # Scores
        # --------------------------------------------------------------

        required_score = (
            required_results[
                "required_match_percentage"
            ]
        )

        preferred_score = (
            preferred_results[
                "required_match_percentage"
            ]
        )

        # --------------------------------------------------------------
        # Final weighted score
        # --------------------------------------------------------------

        if required_skills and preferred_skills:

            final_score = (
                required_score
                * REQUIRED_WEIGHT
                + preferred_score
                * PREFERRED_WEIGHT
            )

        elif required_skills:

            final_score = required_score

        elif preferred_skills:

            final_score = preferred_score

        else:

            final_score = 0.0

        # --------------------------------------------------------------
        # Return detailed scoring result
        # --------------------------------------------------------------

        return {
            "score": round(
                final_score,
                2,
            ),

            "weight": 0.40,

            "weight_percentage": 40.0,

            "candidate_skills": candidate_skills,

            "required_skills": required_skills,

            "preferred_skills": preferred_skills,

            "required": {
                "score": round(
                    required_score,
                    2,
                ),

                "weight": (
                    REQUIRED_WEIGHT
                ),

                "weight_percentage": (
                    REQUIRED_WEIGHT * 100
                ),

                "contribution": round(
                    required_score
                    * REQUIRED_WEIGHT,
                    2,
                ),

                "total_skills": (
                    required_results[
                        "total_required_skills"
                    ]
                ),

                "matched_skills": (
                    required_results[
                        "matched_required_skills_count"
                    ]
                ),

                "match_percentage": (
                    required_results[
                        "required_match_percentage"
                    ]
                ),

                "exact_matches": (
                    required_results[
                        "exact_matches"
                    ]
                ),

                "relationship_matches": (
                    required_results[
                        "relationship_matches"
                    ]
                ),

                "fuzzy_matches": (
                    required_results[
                        "fuzzy_matches"
                    ]
                ),

                "semantic_matches": (
                    required_results[
                        "semantic_matches"
                    ]
                ),

                "related_skill_context": (
                    required_results[
                        "related_skill_context"
                    ]
                ),

                "missing_skills": (
                    required_results[
                        "missing_skills"
                    ]
                ),
            },

            "preferred": {
                "score": round(
                    preferred_score,
                    2,
                ),

                "weight": (
                    PREFERRED_WEIGHT
                ),

                "weight_percentage": (
                    PREFERRED_WEIGHT * 100
                ),

                "contribution": round(
                    preferred_score
                    * PREFERRED_WEIGHT,
                    2,
                ),

                "total_skills": (
                    preferred_results[
                        "total_required_skills"
                    ]
                ),

                "matched_skills": (
                    preferred_results[
                        "matched_required_skills_count"
                    ]
                ),

                "match_percentage": (
                    preferred_results[
                        "required_match_percentage"
                    ]
                ),

                "exact_matches": (
                    preferred_results[
                        "exact_matches"
                    ]
                ),

                "relationship_matches": (
                    preferred_results[
                        "relationship_matches"
                    ]
                ),

                "fuzzy_matches": (
                    preferred_results[
                        "fuzzy_matches"
                    ]
                ),

                "semantic_matches": (
                    preferred_results[
                        "semantic_matches"
                    ]
                ),

                "related_skill_context": (
                    preferred_results[
                        "related_skill_context"
                    ]
                ),

                "missing_skills": (
                    preferred_results[
                        "missing_skills"
                    ]
                ),
            },
        }


# ----------------------------------------------------------------------
# OPTIONAL CONVENIENCE FUNCTION
# ----------------------------------------------------------------------

def calculate_skill_score(
    profile: Dict[str, Any],
    job_description: Dict[str, Any],
    embedding_generator: Any = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper.

    Allows existing code to call:

        calculate_skill_score(
            profile,
            jd,
            embedding_generator=embedding_generator
        )
    """

    scorer = SkillScore()

    return scorer.calculate_skill_score(
        profile,
        job_description,
        embedding_generator=embedding_generator,
    )