from typing import Any, Dict

from scoring.weight_config import get_weights


# ============================================================
# Score Generator
# ============================================================

def generate_candidate_score(
    skill_result: Dict[str, Any],
    experience_result: Dict[str, Any],
    education_result: Dict[str, Any],
    semantic_result: Dict[str, Any],
    job_title: str = "",
    custom_weights: Dict[str, float] = None,
) -> Dict[str, Any]:
    """
    Generate the final ATS candidate score.

    Individual scorers:
        - Skill
        - Experience
        - Education
        - Semantic

    Dynamic weights are obtained from weight_config.py.
    """

    # ========================================================
    # Get dynamic weights
    # ========================================================

    weight_config = get_weights(
        job_title=job_title,
        custom_weights=custom_weights,
    )

    weights = weight_config["weights"]

    # ========================================================
    # Extract individual scores
    # ========================================================

    component_results = {
        "skill": skill_result,
        "experience": experience_result,
        "education": education_result,
        "semantic": semantic_result,
    }

    # ========================================================
    # Calculate weighted contributions
    # ========================================================

    contributions = {}

    available_components = []

    missing_components = []

    for component, result in component_results.items():

        score = result.get("score")

        if score is None:

            missing_components.append(
                component
            )

            continue

        score = float(score)

        weight = weights[component]

        contribution = score * weight

        contributions[component] = {
            "score": round(score, 2),
            "weight": round(weight, 4),
            "weight_percentage": round(
                weight * 100,
                2
            ),
            "contribution": round(
                contribution,
                2
            ),
        }

        available_components.append(
            component
        )

    # ========================================================
    # Handle complete missing data
    # ========================================================

    if not available_components:

        return {
            "final_score": None,

            "status": "no_data",

            "job_title": job_title,

            "role_category":
                weight_config["role_category"],

            "weight_source":
                weight_config["source"],

            "weights": weights,

            "component_scores": {},

            "contributions": {},

            "missing_components":
                missing_components,

            "explanation":
                "No scoring components contain usable data.",
        }

    # ========================================================
    # Missing data policy
    #
    # IMPORTANT:
    #
    # We do not penalize the candidate simply because
    # one component is unavailable.
    #
    # Available weights are normalized.
    # ========================================================

    available_weight = sum(
        weights[component]
        for component in available_components
    )

    weighted_score = sum(
        contributions[component]["contribution"]
        for component in available_components
    )

    # Normalize against available weights.
    final_score = (
        weighted_score / available_weight
    ) if available_weight > 0 else 0.0

    # ========================================================
    # Build component score output
    # ========================================================

    component_scores = {}

    for component, result in component_results.items():

        score = result.get("score")

        component_scores[component] = {
            "score": (
                round(float(score), 2)
                if score is not None
                else None
            ),
            "status": result.get(
                "status",
                "unknown"
            ),
        }

    # ========================================================
    # Build explanation
    # ========================================================

    explanation_parts = []

    for component in available_components:

        contribution = contributions[
            component
        ]

        explanation_parts.append(
            f"{component.title()} score "
            f"{contribution['score']:.2f} "
            f"with {contribution['weight_percentage']:.0f}% "
            f"weight contributed "
            f"{contribution['contribution']:.2f} points."
        )

    if missing_components:

        explanation_parts.append(
            "Missing components: "
            + ", ".join(
                missing_components
            )
            + ". Available component weights "
              "were normalized."
        )

    # ========================================================
    # Final result
    # ========================================================

    return {

        "final_score": round(
            final_score,
            2
        ),

        "status": (
            "partial_data"
            if missing_components
            else "calculated"
        ),

        "job_title": job_title,

        "role_category":
            weight_config["role_category"],

        "weight_source":
            weight_config["source"],

        "weights": {
            key: round(value, 4)
            for key, value in weights.items()
        },

        "component_scores":
            component_scores,

        "contributions":
            contributions,

        "missing_components":
            missing_components,

        "available_weight":
            round(
                available_weight,
                4
            ),

        "explanation":
            explanation_parts,
    }