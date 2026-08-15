from scoring.ranking.recruiters_output import (
    generate_recruiter_output
)


def test_recruiter_output():

    candidates = [

        {
            "candidate_id": "CAN_001",

            "candidate_name": "Rahul Nair",

            "rank": 1,

            "decision": "REVIEW",

            "candidate_score": {
                "final_score": 76.54
            },

            "component_scores": {

                "skill": {
                    "score": 68.89,
                    "required_total": 8,
                    "required_matched": 6,
                    "required_match_percentage": 75.0,
                    "matched_required_skills": [
                        "python",
                        "django",
                        "postgresql"
                    ],
                    "missing_required_skills": [
                        "sql",
                        "object-oriented programming"
                    ]
                },

                "experience": {
                    "score": 90.0,
                    "candidate_years": 3.2,
                    "role_relevance_score": 100.0,
                    "technology_relevance_score": 75.0
                },

                "education": {
                    "score": 100.0
                },

                "semantic": {
                    "score": 56.93
                }
            }
        }
    ]

    result = generate_recruiter_output(
        candidates
    )

    assert len(result) == 1

    candidate = result[0]

    assert candidate["candidate_name"] == "Rahul Nair"

    assert candidate["rank"] == 1

    assert candidate["overall_score"] == 76.54

    assert candidate["decision"] == "REVIEW"

    assert candidate["score_breakdown"]["skill"] == 68.89

    assert candidate["score_breakdown"]["experience"] == 90.0

    assert candidate["required_skill_match"]["matched"] == 6

    assert candidate["required_skill_match"]["total"] == 8

    assert "sql" in candidate[
        "required_skill_match"
    ]["missing_skills"]

    assert candidate["experience"]["years"] == 3.2