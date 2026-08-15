import pytest

from scoring.ranking.top_candidates import get_top_candidates


@pytest.fixture
def ranked_candidates():
    return [
        {
            "candidate_id": "CAN_001",
            "candidate_score": {"final_score": 92.5},
            "rank": 1,
            "decision": "SHORTLIST",
        },
        {
            "candidate_id": "CAN_002",
            "candidate_score": {"final_score": 87.4},
            "rank": 2,
            "decision": "SHORTLIST",
        },
        {
            "candidate_id": "CAN_003",
            "candidate_score": {"final_score": 76.5},
            "rank": 3,
            "decision": "REVIEW",
        },
        {
            "candidate_id": "CAN_004",
            "candidate_score": {"final_score": 68.2},
            "rank": 4,
            "decision": "REVIEW",
        },
        {
            "candidate_id": "CAN_005",
            "candidate_score": {"final_score": 54.3},
            "rank": 5,
            "decision": "REJECT",
        },
    ]


def test_get_top_candidates(ranked_candidates):

    result = get_top_candidates(
        ranked_candidates,
        top_n=3
    )

    assert len(result) == 3

    assert result[0]["candidate_id"] == "CAN_001"
    assert result[1]["candidate_id"] == "CAN_002"
    assert result[2]["candidate_id"] == "CAN_003"


def test_get_top_one_candidate(ranked_candidates):

    result = get_top_candidates(
        ranked_candidates,
        top_n=1
    )

    assert len(result) == 1
    assert result[0]["candidate_id"] == "CAN_001"


def test_top_n_greater_than_candidates(ranked_candidates):

    result = get_top_candidates(
        ranked_candidates,
        top_n=20
    )

    assert len(result) == 5


def test_top_shortlisted_candidates(ranked_candidates):

    result = get_top_candidates(
        ranked_candidates,
        top_n=5,
        decision="SHORTLIST"
    )

    assert len(result) == 2

    assert result[0]["candidate_id"] == "CAN_001"
    assert result[1]["candidate_id"] == "CAN_002"


def test_top_review_candidates(ranked_candidates):

    result = get_top_candidates(
        ranked_candidates,
        top_n=5,
        decision="REVIEW"
    )

    assert len(result) == 2

    assert result[0]["candidate_id"] == "CAN_003"
    assert result[1]["candidate_id"] == "CAN_004"


def test_top_rejected_candidates(ranked_candidates):

    result = get_top_candidates(
        ranked_candidates,
        top_n=5,
        decision="REJECT"
    )

    assert len(result) == 1
    assert result[0]["candidate_id"] == "CAN_005"


def test_decision_is_case_insensitive(ranked_candidates):

    result = get_top_candidates(
        ranked_candidates,
        top_n=5,
        decision="shortlist"
    )

    assert len(result) == 2


def test_invalid_top_n(ranked_candidates):

    with pytest.raises(ValueError):
        get_top_candidates(
            ranked_candidates,
            top_n=0
        )


def test_invalid_decision(ranked_candidates):

    with pytest.raises(ValueError):
        get_top_candidates(
            ranked_candidates,
            top_n=5,
            decision="INVALID"
        )