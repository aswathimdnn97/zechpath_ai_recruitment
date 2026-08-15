from scoring.ranking.ranking_pipeline import rank_and_shortlist


def test_rank_and_shortlist():

    candidates = [
        {
            "candidate_id": "CAN_003",
            "candidate_name": "Rahul",
            "candidate_score": {
                "final_score": 55.0
            },
        },
        {
            "candidate_id": "CAN_001",
            "candidate_name": "John",
            "candidate_score": {
                "final_score": 92.5
            },
        },
        {
            "candidate_id": "CAN_002",
            "candidate_name": "Anu",
            "candidate_score": {
                "final_score": 72.5
            },
        },
    ]

    result = rank_and_shortlist(candidates)

    # ========================================================
    # Ranking
    # ========================================================

    assert result[0]["candidate_id"] == "CAN_001"
    assert result[0]["rank"] == 1

    assert result[1]["candidate_id"] == "CAN_002"
    assert result[1]["rank"] == 2

    assert result[2]["candidate_id"] == "CAN_003"
    assert result[2]["rank"] == 3

    # ========================================================
    # Decisions
    # ========================================================

    assert result[0]["decision"] == "SHORTLIST"
    assert result[1]["decision"] == "REVIEW"
    assert result[2]["decision"] == "REJECT"