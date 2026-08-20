from typing import Any, Dict, List, Tuple

from rapidfuzz import fuzz

from scoring.skill_semantic_matcher import (
    find_semantic_skill_matches,
)


# ============================================================
# Configuration
# ============================================================

FUZZY_MATCH_THRESHOLD = 90

REQUIRED_WEIGHT = 0.80
PREFERRED_WEIGHT = 0.20

FUZZY_MATCH_CONFIDENCE = 0.90

SEMANTIC_MATCH_MIN_THRESHOLD = 0.70


# ============================================================
# Normalization
# ============================================================

def _normalize_skill(skill: str) -> str:
    """Normalize skill names for comparison."""

    if not isinstance(skill, str):
        return ""

    return " ".join(
        skill.lower().strip().split()
    )


def _calculate_skill_similarity(
    candidate_skill: str,
    jd_skill: str,
) -> float:
    """
    Calculate conservative fuzzy similarity.

    Avoids token_set_ratio because it can incorrectly
    treat a shorter skill as a perfect match for a
    longer skill.

    Example:

        django
        django rest framework

    token_set_ratio -> 100
    which is too permissive.
    """

    candidate_skill = _normalize_skill(
        candidate_skill
    )

    jd_skill = _normalize_skill(
        jd_skill
    )

    if not candidate_skill or not jd_skill:
        return 0.0

    # Exact match
    if candidate_skill == jd_skill:
        return 100.0

    ratio_score = fuzz.ratio(
        candidate_skill,
        jd_skill,
    )

    token_sort_score = fuzz.token_sort_ratio(
        candidate_skill,
        jd_skill,
    )

    return max(
        ratio_score,
        token_sort_score,
    )

# ============================================================
# Skill extraction
# ============================================================

def _extract_skill_names(skills: Any) -> List[str]:
    """
    Convert candidate/JD skills into normalized names.

    Supports:

        ["Python", "Django"]

    and:

        [
            {"skill": "Python"},
            {"skill": "Django"}
        ]
    """

    if not isinstance(skills, list):
        return []

    result = []

    for skill in skills:

        if isinstance(skill, str):

            name = skill

        elif isinstance(skill, dict):

            name = (
                skill.get("skill")
                or skill.get("name")
                or skill.get("canonical_name")
            )

        else:
            continue

        normalized = _normalize_skill(name)

        if normalized:
            result.append(normalized)

    return list(dict.fromkeys(result))


# ============================================================
# Profile handling
# ============================================================

def _get_profile_data(
    profile: Dict[str, Any]
) -> Dict[str, Any]:

    if not isinstance(profile, dict):
        return {}

    resume_data = profile.get("resume_text")

    if isinstance(resume_data, dict):
        return resume_data

    return profile


# ============================================================
# Fuzzy skill matching
# ============================================================

def _find_best_skill_match(
    candidate_skill: str,
    jd_skills: List[str],
    threshold: int = FUZZY_MATCH_THRESHOLD,
) -> Tuple[str, float]:
    """
    Find the best fuzzy match for a candidate skill.

    Returns:

        (matched_skill, confidence)

    If no suitable match exists:

        ("", 0.0)
    """

    best_match = ""
    best_score = 0.0

    for jd_skill in jd_skills:

        similarity = fuzz.token_set_ratio(
            candidate_skill,
            jd_skill,
        )

        if similarity > best_score:

            best_score = similarity
            best_match = jd_skill

    if best_score >= threshold:

        return (
            best_match,
            best_score / 100.0,
        )

    return "", 0.0


# ============================================================
# Match required skills
# ============================================================

def _match_skills(
    candidate_skills: List[str],
    jd_skills: List[str],
    embedding_generator: Any = None,
) -> Tuple[
    List[str],
    List[str],
    List[Dict[str, Any]],
    List[Dict[str, Any]],
]:
    """
    Match candidate skills against JD skills.

    Matching order:

        1. Exact match
        2. Conservative fuzzy match
        3. Semantic match

    Exact matches are preferred over fuzzy and semantic
    matches.

    Returns:
        matched skills
        missing skills
        fuzzy match details
        semantic match details
    """

    candidate = set(candidate_skills)

    matched = []
    missing = []

    fuzzy_matches = []
    semantic_matches = []

    # ========================================================
    # Match each JD skill
    # ========================================================

    for jd_skill in jd_skills:

        # ----------------------------------------------------
        # 1. Exact match
        # ----------------------------------------------------

        if jd_skill in candidate:

            matched.append(
                jd_skill
            )

            # IMPORTANT:
            # Do not perform fuzzy or semantic matching
            # when an exact match already exists.

            continue

        # ----------------------------------------------------
        # 2. Fuzzy match
        # ----------------------------------------------------

        best_candidate = ""
        best_score = 0.0

        for candidate_skill in candidate:

            similarity = _calculate_skill_similarity(
                candidate_skill,
                jd_skill,
            )

            if similarity > best_score:

                best_score = similarity
                best_candidate = candidate_skill

        # ----------------------------------------------------
        # Accept fuzzy match
        # ----------------------------------------------------

        if (
            best_candidate
            and best_score >= FUZZY_MATCH_THRESHOLD
        ):

            matched.append(
                jd_skill
            )

            fuzzy_matches.append(
                {
                    "jd_skill": jd_skill,

                    "candidate_skill":
                        best_candidate,

                    "similarity":
                        round(
                            best_score,
                            2,
                        ),

                    "confidence":
                        FUZZY_MATCH_CONFIDENCE,

                    "match_type":
                        "fuzzy",
                }
            )

            # IMPORTANT:
            # Don't also perform semantic matching
            # for a skill already matched fuzzily.

            continue

        # ----------------------------------------------------
        # 3. Semantic matching
        # ----------------------------------------------------

        if embedding_generator is not None:

            semantic_results = (
                find_semantic_skill_matches(
                    candidate_skills=
                        list(candidate),

                    jd_skills=[
                        jd_skill
                    ],

                    embedding_generator=
                        embedding_generator,

                    threshold=
                        SEMANTIC_MATCH_MIN_THRESHOLD,
                )
            )
            print(
            "SEMANTIC INPUT:",
            candidate,
            jd_skill,
            )

            print(
            "SEMANTIC RESULTS:",
            semantic_results,
            )
            if semantic_results:

                semantic_match = (
                    semantic_results[0]
                )

                matched.append(
                    jd_skill
                )

                semantic_matches.append(
                    semantic_match
                )

                # Skill has been matched semantically.
                continue

        # ----------------------------------------------------
        # 4. No match
        # ----------------------------------------------------

        missing.append(
            jd_skill
        )

    return (
        sorted(set(matched)),
        sorted(set(missing)),
        fuzzy_matches,
        semantic_matches,
    )


# ============================================================
# Skill Score
# ============================================================

def calculate_skill_score(
    candidate_profile: Dict[str, Any],
    jd_profile: Dict[str, Any],
    embedding_generator: Any = None,
) -> Dict[str, Any]:
    """
    Calculate ATS skill score.

    Matching strategy:

        1. Exact matching
        2. Fuzzy matching

    Required skills:
        80%

    Preferred skills:
        20%
    """

    candidate_data = _get_profile_data(
        candidate_profile
    )

    jd_data = _get_profile_data(
        jd_profile
    )

    # --------------------------------------------------------
    # Candidate skills
    # --------------------------------------------------------

    candidate_skills = _extract_skill_names(
        candidate_data.get("skills", [])
    )

    # --------------------------------------------------------
    # JD skills
    # --------------------------------------------------------

    required_skills = _extract_skill_names(
        jd_data.get("required_skills", [])
    )

    preferred_skills = _extract_skill_names(
        jd_data.get("preferred_skills", [])
    )

    candidate = set(candidate_skills)

    # --------------------------------------------------------
    # Required matching
    # --------------------------------------------------------

    (
        matched_required,
        missing_required,
        fuzzy_required,
        semantic_required,
    ) = _match_skills(
        candidate_skills,
        required_skills,
        embedding_generator,
    )

    # --------------------------------------------------------
    # Preferred matching
    # --------------------------------------------------------

    (
        matched_preferred,
        missing_preferred,
        fuzzy_preferred,
        semantic_preferred
    ) = _match_skills(
        candidate_skills,
        preferred_skills,
        embedding_generator,
    )

    # --------------------------------------------------------
    # Required score
    # --------------------------------------------------------

    if required_skills:

        required_score = (
            len(matched_required)
            / len(required_skills)
        ) * 100

    else:

        required_score = None
    # --------------------------------------------------------
    # Preferred score
    # --------------------------------------------------------

    if preferred_skills:

        preferred_score = (
            len(matched_preferred)
            / len(preferred_skills)
        ) * 100

    else:

        preferred_score = None

    # --------------------------------------------------------
    # Final score
    # --------------------------------------------------------

    if (
        required_score is not None
        and preferred_score is not None
    ):

        final_score = (
            required_score * REQUIRED_WEIGHT
            + preferred_score * PREFERRED_WEIGHT
        )

    elif required_score is not None:

        final_score = required_score

    elif preferred_score is not None:

        final_score = preferred_score

    else:

        final_score = 0.0

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    if not candidate:

        status = "no_data"

    elif not required_skills and not preferred_skills:

        status = "no_requirements"

    else:

        status = "calculated"

    # --------------------------------------------------------
    # Match statistics
    # --------------------------------------------------------

    fuzzy_required_skills = {
    item["jd_skill"]
    for item in fuzzy_required
    }

    semantic_required_skills = {
        item["jd_skill"]
        for item in semantic_required
    }

    exact_required = [
        skill
        for skill in matched_required
        if (
            skill not in fuzzy_required_skills
            and skill not in semantic_required_skills
        )
    ]

    fuzzy_preferred_skills = {
    item["jd_skill"]
    for item in fuzzy_preferred
    }

    semantic_preferred_skills = {
        item["jd_skill"]
        for item in semantic_preferred
    }

    exact_preferred = [
        skill
        for skill in matched_preferred
        if (
            skill not in fuzzy_preferred_skills
            and skill not in semantic_preferred_skills
        )
    ]

    # --------------------------------------------------------
    # Output
    # --------------------------------------------------------

    return {

        "score": round(
            final_score,
            2
        ),

        "required_score": (
            round(required_score, 2)
            if required_score is not None
            else None
        ),

        "preferred_score": (
            round(preferred_score, 2)
            if preferred_score is not None
            else None
        ),

        "required_total": len(
            required_skills
        ),

      "required_matched": len(
            matched_required

        ),
       


        "required_match_percentage": (
            round(required_score, 2)
            if required_score is not None
            else None
        ),

        "matched_required_skills":
            matched_required,

        "missing_required_skills":
            missing_required,

        "fuzzy_required_matches":
            fuzzy_required,
        
        "semantic_required_matches":
            semantic_required,

        "exact_required_matches":
            exact_required,

        "preferred_total": len(
            preferred_skills
        ),

        "preferred_matched": len(
            matched_preferred
        ),
        "preferred_match_percentage": (
            round(preferred_score, 2)
            if preferred_score is not None
            else None
        ),

        "matched_preferred_skills":
            matched_preferred,

        "missing_preferred_skills":
            missing_preferred,

        "fuzzy_preferred_matches":
            fuzzy_preferred,
            
        "semantic_preferred_matches":
            semantic_preferred,

        "exact_preferred_matches":
            exact_preferred,

        "candidate_skill_count":
            len(candidate),

        "status":
            status,
    }