import pytest

from scoring.ranking.shortlisting_engine import (
    classify_candidate,
    shortlist_candidates,
)


# ============================================================
# classify_candidate() tests
# ============================================================

def test_high_score_is_shortlisted():

    result = classify_candidate(90)

    assert result == "SHORTLIST"


def test_shortlist_boundary_score():

    result = classify_candidate(80)

    assert result == "SHORTLIST"


def test_review_score():

    result = classify_candidate(70)

    assert result == "REVIEW"


def test_review_boundary_score():

    result = classify_candidate(60)

    assert result == "REVIEW"


def test_reject_score():

    result = classify_candidate(50)

    assert result == "REJECT"


def test_reject_boundary_below_review():

    result = classify_candidate(59.99)

    assert result == "REJECT"


def test_invalid_thresholds():

    with pytest.raises(ValueError):

        classify_candidate(
            score=80,
            shortlist_threshold=60,
            review_threshold=80,
        )


# ============================================================
# shortlist_candidates() tests
# ============================================================

def test_candidates_receive_decision():

    candidates = [

        {
            "candidate_id": "CAN_001",
            "candidate_name": "John",

            "candidate_score": {
                "final_score": 92.5
            },

            "rank": 1,
        },

        {
            "candidate_id": "CAN_002",
            "candidate_name": "Anu",

            "candidate_score": {
                "final_score": 72.5
            },

            "rank": 2,
        },

        {
            "candidate_id": "CAN_003",
            "candidate_name": "Rahul",

            "candidate_score": {
                "final_score": 45.0
            },

            "rank": 3,
        },
    ]

    result = shortlist_candidates(
        candidates
    )

    assert result[0]["decision"] == "SHORTLIST"

    assert result[1]["decision"] == "REVIEW"

    assert result[2]["decision"] == "REJECT"


def test_rank_and_score_are_preserved():

    candidates = [

        {
            "candidate_id": "CAN_001",

            "candidate_score": {
                "final_score": 88.5
            },

            "rank": 1,
        }
    ]

    result = shortlist_candidates(
        candidates
    )

    assert result[0]["candidate_id"] == "CAN_001"

    assert (
        result[0]["candidate_score"]["final_score"]
        == 88.5
    )

    assert result[0]["rank"] == 1

    assert result[0]["decision"] == "SHORTLIST"


def test_custom_thresholds():

    candidates = [

        {
            "candidate_id": "CAN_001",

            "candidate_score": {
                "final_score": 75
            },
        },

        {
            "candidate_id": "CAN_002",

            "candidate_score": {
                "final_score": 65
            },
        },

        {
            "candidate_id": "CAN_003",

            "candidate_score": {
                "final_score": 50
            },
        },
    ]

    result = shortlist_candidates(
        candidates,
        shortlist_threshold=75,
        review_threshold=60,
    )

    assert result[0]["decision"] == "SHORTLIST"

    assert result[1]["decision"] == "REVIEW"

    assert result[2]["decision"] == "REJECT"