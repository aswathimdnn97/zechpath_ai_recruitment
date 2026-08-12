from typing import Any, Dict, List, Optional

from embeddings.embedding_generator import EmbeddingGenerator
from similarity.similarity import cosine_similarity

from matching.skill_importence import (
    build_skill_weights,
    normalize_skill_list,
)


# ============================================================
# Configuration
# ============================================================

_embedding_generator = EmbeddingGenerator()

# Explicit skill matching should have more influence
# than semantic similarity.
EXPLICIT_WEIGHT = 0.70
SEMANTIC_WEIGHT = 0.30


# Semantic similarity bands
STRONG_SEMANTIC_THRESHOLD = 0.75
RELATED_SEMANTIC_THRESHOLD = 0.60
WEAK_SEMANTIC_THRESHOLD = 0.50


# ============================================================
# Helpers
# ============================================================

def _safe_similarity(value: Any) -> float:
    """
    Keep similarity within 0-1.
    """

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(1.0, value))


def _semantic_contribution(
    similarity: float,
):
    """
    Convert raw semantic similarity into a graded
    semantic contribution.

    Strong relationship:
        >= 0.75 -> full contribution

    Related relationship:
        0.60 - 0.74 -> 80% contribution

    Weak relationship:
        0.50 - 0.59 -> 50% contribution

    Below 0.50:
        no contribution
    """

    similarity = _safe_similarity(
        similarity
    )

    if similarity >= STRONG_SEMANTIC_THRESHOLD:

        return similarity, "strong"

    if similarity >= RELATED_SEMANTIC_THRESHOLD:

        return similarity * 0.80, "related"

    if similarity >= WEAK_SEMANTIC_THRESHOLD:

        return similarity * 0.50, "weak"

    return 0.0, "none"


# ============================================================
# Generate Skill Embeddings
# ============================================================

def _generate_skill_embeddings(
    skills: List[str],
) -> Dict[str, Any]:
    """
    Generate one embedding for each skill.
    """

    embeddings = {}

    for skill in skills:

        if not skill:
            continue

        embeddings[skill] = (
            _embedding_generator
            .generate_embedding(skill)
        )

    return embeddings


# ============================================================
# Per-Skill Semantic Similarity
# ============================================================

def calculate_per_skill_semantic_similarity(
    candidate_skills: List[Any],
    required_skills: List[Any],
) -> Dict[str, Any]:
    """
    Compare every required JD skill against every
    candidate skill.

    The best candidate skill is selected for each
    required skill.
    """

    candidate = normalize_skill_list(
        candidate_skills
    )

    required = normalize_skill_list(
        required_skills
    )

    candidate = list(
        dict.fromkeys(candidate)
    )

    required = list(
        dict.fromkeys(required)
    )

    if not candidate or not required:

        return {
            "score": 0.0,
            "required_semantic_matches": [],
        }

    # --------------------------------------------------------
    # Generate embeddings
    # --------------------------------------------------------

    candidate_embeddings = (
        _generate_skill_embeddings(
            candidate
        )
    )

    required_embeddings = (
        _generate_skill_embeddings(
            required
        )
    )

    # --------------------------------------------------------
    # Compare each required skill
    # --------------------------------------------------------

    semantic_matches = []

    total_semantic_score = 0.0

    for required_skill in required:

        required_embedding = (
            required_embeddings.get(
                required_skill
            )
        )

        if required_embedding is None:
            continue

        best_candidate = None
        best_similarity = 0.0

        # ----------------------------------------------------
        # Find best candidate skill
        # ----------------------------------------------------

        for candidate_skill in candidate:

            candidate_embedding = (
                candidate_embeddings.get(
                    candidate_skill
                )
            )

            if candidate_embedding is None:
                continue

            similarity = cosine_similarity(
                required_embedding,
                candidate_embedding,
            )

            similarity = _safe_similarity(
                similarity
            )

            if similarity > best_similarity:

                best_similarity = similarity
                best_candidate = candidate_skill

        # ----------------------------------------------------
        # Graded semantic contribution
        # ----------------------------------------------------

        semantic_score, match_level = (
            _semantic_contribution(
                best_similarity
            )
        )

        total_semantic_score += (
            semantic_score
        )

        semantic_matches.append({
            "required_skill": required_skill,

            "best_candidate_skill":
                best_candidate,

            "similarity":
                round(
                    best_similarity,
                    4
                ),

            "semantic_score":
                round(
                    semantic_score,
                    4
                ),

            "match_level":
                match_level,

            "matched":
                match_level != "none",
        })

    # --------------------------------------------------------
    # Average semantic score
    # --------------------------------------------------------

    semantic_score = (
        total_semantic_score / len(required)
        if required
        else 0.0
    )

    return {
        "score": round(
            semantic_score,
            4
        ),

        "required_semantic_matches":
            semantic_matches,
    }


# ============================================================
# Explicit Skill Similarity
# ============================================================

def calculate_explicit_skill_similarity(
    candidate_skills: List[Any],
    required_skills: List[Any],
    preferred_skills: Optional[
        List[Any]
    ] = None,
) -> Dict[str, Any]:
    """
    Calculate explicit skill similarity.

    Required skills:
        80%

    Preferred skills:
        20%
    """

    if preferred_skills is None:
        preferred_skills = []

    candidate = set(
        normalize_skill_list(
            candidate_skills
        )
    )

    required = list(
        dict.fromkeys(
            normalize_skill_list(
                required_skills
            )
        )
    )

    preferred = list(
        dict.fromkeys(
            normalize_skill_list(
                preferred_skills
            )
        )
    )

    # --------------------------------------------------------
    # Build skill importance
    # --------------------------------------------------------

    skill_weights = build_skill_weights(
        required,
        preferred,
    )

    # ========================================================
    # Required skills
    # ========================================================

    matched_required = []
    missing_required = []

    matched_required_weight = 0.0
    total_required_weight = 0.0

    required_details = []

    for skill in required:

        weight = skill_weights.get(
            skill,
            0.0
        )

        total_required_weight += weight

        matched = skill in candidate

        if matched:

            matched_required.append(
                skill
            )

            matched_required_weight += (
                weight
            )

        else:

            missing_required.append(
                skill
            )

        required_details.append({
            "skill": skill,
            "weight": round(
                weight,
                4
            ),
            "matched": matched,
            "importance": "required",
        })

    required_coverage = (
        matched_required_weight
        / total_required_weight
        if total_required_weight
        else 0.0
    )

    # ========================================================
    # Preferred skills
    # ========================================================

    matched_preferred = []
    missing_preferred = []

    matched_preferred_weight = 0.0
    total_preferred_weight = 0.0

    preferred_details = []

    for skill in preferred:

        if skill in required:
            continue

        weight = skill_weights.get(
            skill,
            0.0
        )

        total_preferred_weight += weight

        matched = skill in candidate

        if matched:

            matched_preferred.append(
                skill
            )

            matched_preferred_weight += (
                weight
            )

        else:

            missing_preferred.append(
                skill
            )

        preferred_details.append({
            "skill": skill,
            "weight": round(
                weight,
                4
            ),
            "matched": matched,
            "importance": "preferred",
        })

    preferred_coverage = (
        matched_preferred_weight
        / total_preferred_weight
        if total_preferred_weight
        else 0.0
    )

    # ========================================================
    # Explicit score
    # ========================================================

    explicit_score = (
        required_coverage * 0.80
        +
        preferred_coverage * 0.20
    )

    return {
        "score": round(
            explicit_score,
            4
        ),

        "required_coverage":
            round(
                required_coverage,
                4
            ),

        "preferred_coverage":
            round(
                preferred_coverage,
                4
            ),

        "matched_required":
            matched_required,

        "missing_required":
            missing_required,

        "matched_preferred":
            matched_preferred,

        "missing_preferred":
            missing_preferred,

        "required_skill_details":
            required_details,

        "preferred_skill_details":
            preferred_details,
    }


# ============================================================
# Hybrid Skill Similarity
# ============================================================

def calculate_hybrid_skill_similarity(
    candidate_skills: List[Any],
    required_skills: List[Any],
    preferred_skills: Optional[
        List[Any]
    ] = None,
) -> Dict[str, Any]:
    """
    Calculate final hybrid skill similarity.

    Explicit matching:
        70%

    Semantic matching:
        30%
    """

    if preferred_skills is None:
        preferred_skills = []

    # --------------------------------------------------------
    # Explicit similarity
    # --------------------------------------------------------

    explicit_result = (
        calculate_explicit_skill_similarity(
            candidate_skills=
                candidate_skills,

            required_skills=
                required_skills,

            preferred_skills=
                preferred_skills,
        )
    )

    # --------------------------------------------------------
    # Per-skill semantic similarity
    # --------------------------------------------------------

    semantic_result = (
        calculate_per_skill_semantic_similarity(
            candidate_skills=
                candidate_skills,

            required_skills=
                required_skills,
        )
    )

    explicit_score = (
        explicit_result["score"]
    )

    semantic_score = (
        semantic_result["score"]
    )

    # --------------------------------------------------------
    # Hybrid score
    # --------------------------------------------------------

    hybrid_score = (
        explicit_score
        * EXPLICIT_WEIGHT
        +
        semantic_score
        * SEMANTIC_WEIGHT
    )

    return {
        "score":
            round(
                hybrid_score,
                4
            ),

        "explicit_score":
            round(
                explicit_score,
                4
            ),

        "semantic_score":
            round(
                semantic_score,
                4
            ),

        "required_coverage":
            explicit_result[
                "required_coverage"
            ],

        "preferred_coverage":
            explicit_result[
                "preferred_coverage"
            ],

        "matched_required":
            explicit_result[
                "matched_required"
            ],

        "missing_required":
            explicit_result[
                "missing_required"
            ],

        "matched_preferred":
            explicit_result[
                "matched_preferred"
            ],

        "missing_preferred":
            explicit_result[
                "missing_preferred"
            ],

        "required_skill_details":
            explicit_result[
                "required_skill_details"
            ],

        "preferred_skill_details":
            explicit_result[
                "preferred_skill_details"
            ],

        # Detailed semantic information
        "required_semantic_matches":
            semantic_result[
                "required_semantic_matches"
            ],
    }