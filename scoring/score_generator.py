from typing import Any, Dict, Optional


# Score-generator-specific default weights.
#
# These are intentionally separate from the ATS orchestration weights.
# The ATS engine passes the individual component results here, and this
# module owns how those components are combined.
DEFAULT_WEIGHTS = {
    "skill": 0.45,
    "experience": 0.30,
    "education": 0.10,
    "semantic": 0.15,
}


ROLE_WEIGHT_PROFILES = {
    "backend": {
        "skill": 0.45,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.15,
    },
    "frontend": {
        "skill": 0.45,
        "experience": 0.25,
        "education": 0.10,
        "semantic": 0.20,
    },
    "data_ml": {
        "skill": 0.40,
        "experience": 0.25,
        "education": 0.15,
        "semantic": 0.20,
    },
    "general": {
    "skill": 0.40,
    "experience": 0.30,
    "education": 0.10,
    "semantic": 0.20,
    },
}


def _normalise_job_title(job_title: Any) -> str:
    """Return a normalized job title for role classification."""
    if not isinstance(job_title, str):
        return ""

    return " ".join(job_title.lower().strip().split())



def _detect_role_category(job_title: Any) -> str:
    """
    Classify the job title into the scoring role category.
    """

    title = _normalise_job_title(job_title)

    if not title:
        return "general"

    backend_terms = (
        "backend",
        "back-end",
        "back end",
        "python developer",
        "python engineer",
        "django developer",
        "fastapi developer",
        "flask developer",
        "node.js developer",
        "nodejs developer",
        "java developer",
        "java engineer",
        "spring boot",
        "php developer",
        ".net developer",
        "dotnet developer",
        "api developer",
        "server side",
        "server-side",
    )

    if any(term in title for term in backend_terms):
        return "backend"

    frontend_terms = (
        "frontend",
        "front-end",
        "front end",
        "react developer",
        "react engineer",
        "angular developer",
        "vue developer",
        "javascript developer",
        "typescript developer",
        "ui developer",
        "web ui",
    )

    if any(term in title for term in frontend_terms):
        return "frontend"

    data_ml_terms = (
        "data scientist",
        "data science",
        "machine learning",
        "machine-learning",
        "ml engineer",
        "ml developer",
        "ai engineer",
        "artificial intelligence",
        "data analyst",
        "data engineer",
    )

    if any(term in title for term in data_ml_terms):
        return "data_ml"

    return "general"

def _weights(
    custom: Optional[Dict[str, float]] = None,
    role_category: str = "general",
) -> Dict[str, float]:

    weights = ROLE_WEIGHT_PROFILES.get(
        role_category,
        ROLE_WEIGHT_PROFILES["general"],
    ).copy()

    if custom:
        for key in weights:
            if key not in custom:
                continue

            try:
                value = float(custom[key])
            except (TypeError, ValueError):
                continue

            if value >= 0:
                weights[key] = value

    return weights


def _get_score(result: Any) -> Optional[float]:
    """Safely extract a numeric component score."""
    if not isinstance(result, dict):
        return None

    score = result.get("score")

    if score is None:
        return None

    try:
        return float(score)
    except (TypeError, ValueError):
        return None


def _build_explanation(
    component_scores: Dict[str, Dict[str, Any]],
    available: list,
    missing_components: list,
    final_score: Optional[float],
) -> list:
    """
    Build a list of human-readable component explanations.
    """

    explanation = []

    for name in available:
        component = component_scores.get(name, {})

        score = component.get("score")
        weight_percentage = component.get(
            "weight_percentage"
        )

        if score is None:
            continue

        explanation.append(
            f"{name.capitalize()} score: "
            f"{score:.2f} "
            f"({weight_percentage:.2f}% weight)"
        )

    if missing_components:
        explanation.append(
            "Missing components: "
            + ", ".join(missing_components)
        )

    if not explanation:
        explanation.append(
            "No scoring components were available."
        )

    return explanation


def generate_candidate_score(
    skill_result: Dict[str, Any],
    experience_result: Dict[str, Any],
    education_result: Dict[str, Any],
    semantic_result: Dict[str, Any],
    job_title: str = "",
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Generate the final candidate score from the four scoring components.

    The individual scorers remain responsible for calculating their
    own scores. This module only combines those scores.
    """

    role_category = _detect_role_category(job_title)

    w = _weights(
        custom=custom_weights,
        role_category=role_category,
    )

    results = {
        "skill": skill_result,
        "experience": experience_result,
        "education": education_result,
        "semantic": semantic_result,
    }

    component_scores: Dict[str, Dict[str, Any]] = {}
    contributions: Dict[str, Dict[str, Any]] = {}

    available = []

    for name, result in results.items():
        score = _get_score(result)

        component_scores[name] = {
            "score": (
                None
                if score is None
                else round(score, 2)
            ),
            "weight": round(w[name], 4),
            "weight_percentage": round(w[name] * 100, 2),
        }

        if score is not None:
            available.append(name)

            contributions[name] = {
                "score": round(score, 2),
                "weight": round(w[name], 4),
                "weight_percentage": round(w[name] * 100, 2),
                "contribution": round(
                    score * w[name],
                    2,
                ),
            }

    missing_components = [
        name
        for name in results
        if name not in available
    ]

    if not available:
        final = None
    else:
        available_weight = sum(
            w[name]
            for name in available
        )

        # When data is missing, redistribute the available weights so
        # that the available components still form a complete score.
        #
        # Example:
        # skill     = 45%
        # experience = 30%
        # semantic   = 15%
        # education missing
        #
        # available total = 90%
        #
        # The available scores are normalized against that 90%.
        if missing_components and available_weight > 0:
            final = round(
                sum(
                    float(results[name]["score"]) * w[name]
                    for name in available
                )
                / available_weight,
                2,
            )
        else:
            final = round(
                sum(
                    float(results[name]["score"]) * w[name]
                    for name in available
                ),
                2,
            )

    available_weight = sum(
        w[name]
        for name in available
    )

    if custom_weights:
        weight_source = "custom"
    else:
        weight_source = "role_category"
        

    explanation = _build_explanation(
        component_scores=component_scores,
        available=available,
        missing_components=missing_components,
        final_score=final,
    )

    return {
        "final_score": final,

        "status": (
            "calculated"
            if len(available) == 4
            else (
                "partial_data"
                if available
                else "no_data"
            )
        ),

        "job_title": job_title,

        "weights": {
            key: round(value, 4)
            for key, value in w.items()
        },

        "component_scores": component_scores,

        "contributions": contributions,

        "missing_components": missing_components,

        "available_weight": round(
            available_weight,
            4,
        ),

        "weight_source": weight_source,

        "role_category": role_category,

        "explanation": explanation,
    }