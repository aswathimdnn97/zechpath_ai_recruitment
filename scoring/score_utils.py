from typing import Any, Dict


def get_final_score(
    candidate: Dict[str, Any]
) -> float:

    return float(
        candidate
        .get("candidate_score", {})
        .get("final_score", 0.0)
    )


def get_component_score(
    candidate: Dict[str, Any],
    component: str
) -> float:

    return float(
        candidate
        .get("component_scores", {})
        .get(component, {})
        .get("score", 0.0)
    )