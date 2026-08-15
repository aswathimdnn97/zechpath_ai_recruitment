from typing import Any, Dict, List


def get_top_candidates(
    candidates: List[Dict[str, Any]],
    top_n: int = 10,
    decision: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Return the top N candidates.

    Args:
        candidates:
            Ranked candidate results.

        top_n:
            Maximum number of candidates to return.

        decision:
            Optional decision filter:
            SHORTLIST, REVIEW, or REJECT.

    Returns:
        List of top candidates.
    """

    if top_n <= 0:
        raise ValueError("top_n must be greater than 0")

    if decision is not None:
        decision = decision.upper()

        valid_decisions = {
            "SHORTLIST",
            "REVIEW",
            "REJECT",
        }

        if decision not in valid_decisions:
            raise ValueError(
                f"Invalid decision '{decision}'. "
                f"Expected one of {valid_decisions}"
            )

        candidates = [
            candidate
            for candidate in candidates
            if candidate.get("decision") == decision
        ]

    # Ensure candidates are ordered by rank.
    candidates = sorted(
        candidates,
        key=lambda candidate: candidate.get("rank", float("inf"))
    )

    return candidates[:top_n]