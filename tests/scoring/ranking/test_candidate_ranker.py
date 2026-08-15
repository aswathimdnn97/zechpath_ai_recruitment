from scoring.ranking.candidate_ranker import rank_candidates


def test_candidates_are_ranked_by_score():

    candidates = [
        {
            "candidate_id": "CAN_003",
            "candidate_name": "Rahul",
            "candidate_score": {
                "final_score": 55.2
            }
        },
        {
            "candidate_id": "CAN_001",
            "candidate_name": "John",
            "candidate_score": {
                "final_score": 92.5
            }
        },
        {
            "candidate_id": "CAN_002",
            "candidate_name": "Anu",
            "candidate_score": {
                "final_score": 78.4
            }
        }
    ]

    result = rank_candidates(candidates)

    assert result[0]["candidate_id"] == "CAN_001"
    assert result[0]["rank"] == 1

    assert result[1]["candidate_id"] == "CAN_002"
    assert result[1]["rank"] == 2

    assert result[2]["candidate_id"] == "CAN_003"
    assert result[2]["rank"] == 3