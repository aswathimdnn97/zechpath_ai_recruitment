"""
Skill scoring.

Matching priority
-----------------
Exact
    ↓
Broader relationship
    ↓
Related context
    ↓
Fuzzy
    ↓
Semantic
    ↓
Missing

Important:
"related" skills never receive match credit.
"""

import logging
from typing import Any, Dict, List, Optional, Set

from rapidfuzz import fuzz

from scoring.skill_semantic_matcher import find_semantic_skill_matches
from scoring.skill_relationship_resolver import SkillRelationshipResolver


logger = logging.getLogger(__name__)

FUZZY_MATCH_THRESHOLD = 90
REQUIRED_WEIGHT = 0.80
PREFERRED_WEIGHT = 0.20
SEMANTIC_MATCH_MIN_THRESHOLD = 0.70


class SkillScore:

    def __init__(self, embedding_generator=None):
        self.embedding_generator = embedding_generator
        self.relationship_resolver = SkillRelationshipResolver()

    def _normalize_skill(self, skill: Any) -> str:
        if skill is None:
            return ""

        if isinstance(skill, dict):
            skill = (
                skill.get("name")
                or skill.get("skill")
                or skill.get("canonical_name")
                or skill.get("skill_name")
                or ""
            )

        return " ".join(
            str(skill).strip().lower().split()
        )

    def _calculate_skill_similarity(
        self,
        candidate_skill: str,
        required_skill: str,
    ) -> float:
        candidate = self._normalize_skill(candidate_skill)
        required = self._normalize_skill(required_skill)

        if not candidate or not required:
            return 0.0

        return max(
            fuzz.ratio(candidate, required),
            fuzz.token_sort_ratio(candidate, required),
        )

    def _extract_skill_names(self, skills: Any) -> List[str]:
        if not skills:
            return []

        if isinstance(skills, dict):
            skills = skills.values()

        if isinstance(skills, str):
            skills = [skills]

        result = []

        for skill in skills:
            if isinstance(skill, str):
                normalized = skill.strip()
            elif isinstance(skill, dict):
                normalized = (
                    skill.get("name")
                    or skill.get("skill")
                    or skill.get("canonical_name")
                    or skill.get("skill_name")
                    or ""
                )
                normalized = str(normalized).strip()
            else:
                continue

            if normalized:
                result.append(normalized)

        return result

    def _extract_candidate_skills(
        self,
        candidate_profile: Dict[str, Any],
    ) -> List[str]:

        skills = []

        skills.extend(
            self._extract_skill_names(
                candidate_profile.get("skills", [])
            )
        )

        experience = candidate_profile.get("experience", [])

        if isinstance(experience, list):
            for record in experience:
                if not isinstance(record, dict):
                    continue

                skills.extend(
                    self._extract_skill_names(
                        record.get("skills", [])
                    )
                )

        unique = []
        seen = set()

        for skill in skills:
            normalized = self._normalize_skill(skill)

            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(skill)

        return unique

    def _get_profile_data(self, profile: Any) -> Dict[str, Any]:
        return profile if isinstance(profile, dict) else {}

    def _extract_required_skills(
        self,
        jd_profile: Dict[str, Any],
    ) -> List[str]:
        return self._extract_skill_names(
            jd_profile.get("required_skills", [])
        )

    def _extract_preferred_skills(
        self,
        jd_profile: Dict[str, Any],
    ) -> List[str]:
        return self._extract_skill_names(
            jd_profile.get("preferred_skills", [])
        )

    def _get_available_candidate_skills(
        self,
        candidate_skills: List[str],
        used_candidate_skills: Set[str],
    ) -> List[str]:
        return [
            skill
            for skill in candidate_skills
            if self._normalize_skill(skill)
            not in used_candidate_skills
        ]

    def _find_exact_match(
        self,
        required_skill: str,
        candidate_skills: List[str],
    ) -> Optional[Dict[str, Any]]:

        required_normalized = self._normalize_skill(
            required_skill
        )

        for candidate_skill in candidate_skills:
            if (
                self._normalize_skill(candidate_skill)
                == required_normalized
            ):
                return {
                    "required_skill": required_skill,
                    "matched_skill": candidate_skill,
                    "matched": True,
                    "match_type": "exact",
                    "confidence": 1.0,
                }

        return None

    def _resolve_relationship(
        self,
        candidate_skill: str,
        required_skill: str,
    ):
        try:
            return self.relationship_resolver.resolve(
                candidate_skill,
                required_skill,
            )
        except Exception:
            return None

    def _find_relationship_match(
        self,
        required_skill: str,
        candidate_skills: List[str],
    ) -> Optional[Dict[str, Any]]:

        for candidate_skill in candidate_skills:
            relationship = self._resolve_relationship(
                candidate_skill,
                required_skill,
            )

            if not relationship:
                continue

            if relationship.get("relationship") == "broader":
                return {
                    "required_skill": required_skill,
                    "matched_skill": candidate_skill,
                    "matched": True,
                    "match_type": "broader",
                    "relationship": "broader",
                    "confidence": 1.0,
                }

        return None

    def _find_related_skill_context(
        self,
        required_skill: str,
        candidate_skills: List[str],
    ) -> Optional[Dict[str, Any]]:

        for candidate_skill in candidate_skills:
            relationship = self._resolve_relationship(
                candidate_skill,
                required_skill,
            )

            if not relationship:
                continue

            if relationship.get("relationship") == "related":
                return {
                    "required_skill": required_skill,
                    "matched_skill": candidate_skill,
                    "matched": False,
                    "match_type": "related",
                    "relationship": "related",
                    "confidence": 0.0,
                }

        return None

    def _find_fuzzy_match(
        self,
        required_skill: str,
        candidate_skills: List[str],
    ) -> Optional[Dict[str, Any]]:

        best_skill = None
        best_score = 0.0

        for candidate_skill in candidate_skills:
            similarity = self._calculate_skill_similarity(
                candidate_skill,
                required_skill,
            )

            if similarity > best_score:
                best_score = similarity
                best_skill = candidate_skill

        if (
            best_skill is not None
            and best_score >= FUZZY_MATCH_THRESHOLD
        ):
            return {
                "required_skill": required_skill,
                "matched_skill": best_skill,
                "matched": True,
                "match_type": "fuzzy",
                "confidence": round(best_score / 100, 4),
                "similarity": round(best_score, 2),
            }

        return None

    def _find_semantic_match(
        self,
        required_skill: str,
        candidate_skills: List[str],
    ) -> Optional[Dict[str, Any]]:

        if (
            not candidate_skills
            or self.embedding_generator is None
        ):
            return None

        try:
            result = find_semantic_skill_matches(
                candidate_skills=candidate_skills,
                required_skills=[required_skill],
                embedding_generator=self.embedding_generator,
                threshold=SEMANTIC_MATCH_MIN_THRESHOLD,
            )

            if isinstance(result, list):
                semantic_matches = result
            elif isinstance(result, dict):
                semantic_matches = result.get("semantic_matches", [])
            else:
                return None

            if not semantic_matches:
                return None

            best_match = semantic_matches[0]

            if not isinstance(best_match, dict):
                return None

            matched_skill = (
                best_match.get("matched_skill")
                or best_match.get("candidate_skill")
                or best_match.get("skill")
            )

            similarity = best_match.get(
                "similarity",
                best_match.get("score", 0.0),
            )

            if matched_skill is None:
                return None

            similarity = float(similarity)

            # If score is expressed as 0-100, convert it back to
            # a confidence-like 0-1 value for this result.
            if similarity > 1.0:
                confidence = similarity / 100.0
            else:
                confidence = similarity

            return {
                "required_skill": required_skill,
                "matched_skill": matched_skill,
                "matched": True,
                "match_type": "semantic",
                "confidence": round(confidence, 4),
                "similarity": round(similarity, 4),
            }

        except Exception as exc:
            logger.exception(
                "Semantic skill matching failed for '%s': %s",
                required_skill,
                exc,
            )
            return None

    def _match_skills(
        self,
        candidate_skills: List[str],
        jd_skills: List[str],
    ) -> Dict[str, Any]:

        matched = []
        missing = []

        used_candidate_skills: Set[str] = set()

        for required_skill in jd_skills:

            available = self._get_available_candidate_skills(
                candidate_skills,
                used_candidate_skills,
            )

            # 1. Exact
            result = self._find_exact_match(
                required_skill,
                available,
            )

            if result:
                matched.append(result)
                used_candidate_skills.add(
                    self._normalize_skill(
                        result["matched_skill"]
                    )
                )
                continue

            # 2. Broader
            result = self._find_relationship_match(
                required_skill,
                available,
            )

            if result:
                matched.append(result)
                used_candidate_skills.add(
                    self._normalize_skill(
                        result["matched_skill"]
                    )
                )
                continue

            # 3. Related
            #
            # Related skills are explanation-only and MUST NOT
            # proceed to fuzzy/semantic matching. Otherwise a
            # relationship explicitly marked "related" could
            # accidentally receive match credit.
            related_context = self._find_related_skill_context(
                required_skill,
                available,
            )
            
            

            if related_context:
                missing.append({
                    "required_skill": required_skill,
                    "matched": False,
                    "match_type": "missing",
                    "related_skill_context": related_context,
                })
                continue

            # 4. Fuzzy
            result = self._find_fuzzy_match(
                required_skill,
                available,
            )

            if result:
                matched.append(result)
                used_candidate_skills.add(
                    self._normalize_skill(
                        result["matched_skill"]
                    )
                )
                continue

            # 5. Semantic
            result = self._find_semantic_match(
                required_skill,
                available,
            )

            if result:
                matched.append(result)
                used_candidate_skills.add(
                    self._normalize_skill(
                        result["matched_skill"]
                    )
                )
                continue

            # 6. Missing
            missing.append({
                "required_skill": required_skill,
                "matched": False,
                "match_type": "missing",
            })

        return {
            "matched": matched,
            "missing": missing,
        }

    def _match_preferred_skills(
        self,
        candidate_skills: List[str],
        preferred_skills: List[str],
    ) -> Dict[str, Any]:
        return self._match_skills(
            candidate_skills,
            preferred_skills,
        )

    def calculate_skill_score(
        self,
        candidate_profile: Any,
        jd_profile: Any,
    ) -> Dict[str, Any]:

        candidate_profile = self._get_profile_data(
            candidate_profile
        )
        jd_profile = self._get_profile_data(
            jd_profile
        )

        candidate_skills = self._extract_candidate_skills(
            candidate_profile
        )
        required_skills = self._extract_required_skills(
            jd_profile
        )
        preferred_skills = self._extract_preferred_skills(
            jd_profile
        )

        required_result = self._match_skills(
            candidate_skills,
            required_skills,
        )
        preferred_result = self._match_preferred_skills(
            candidate_skills,
            preferred_skills,
        )

        required_count = len(required_skills)
        preferred_count = len(preferred_skills)

        required_match_count = len(
            required_result["matched"]
        )
        preferred_match_count = len(
            preferred_result["matched"]
        )

        required_percentage = (
            required_match_count / required_count * 100
            if required_count
            else 100.0
        )

        preferred_percentage = (
            preferred_match_count / preferred_count * 100
            if preferred_count
            else 100.0
        )

        final_skill_score = (
            required_percentage * REQUIRED_WEIGHT
            + preferred_percentage * PREFERRED_WEIGHT
        )

        return {
            "score": round(final_skill_score, 2),
            "weight": 0.40,
            "candidate_skills": candidate_skills,
            "required": {
                "skills": required_skills,
                "matched": required_result["matched"],
                "missing": required_result["missing"],
                "match_percentage": round(
                    required_percentage,
                    2,
                ),
            },
            "preferred": {
                "skills": preferred_skills,
                "matched": preferred_result["matched"],
                "missing": preferred_result["missing"],
                "match_percentage": round(
                    preferred_percentage,
                    2,
                ),
            },
            "weights": {
                "required": REQUIRED_WEIGHT,
                "preferred": PREFERRED_WEIGHT,
            },
        }


def calculate_skill_score(
    candidate_profile: Any,
    jd_profile: Any,
    embedding_generator=None,
) -> Dict[str, Any]:

    scorer = SkillScore(
        embedding_generator=embedding_generator
    )

    return scorer.calculate_skill_score(
        candidate_profile,
        jd_profile,
    )
