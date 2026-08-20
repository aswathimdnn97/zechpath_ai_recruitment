from scoring.score_generator import generate_candidate_score


def test_score_generator_normalizes_component_scores():

    skill_result = {
        "score": 80,
        "status": "calculated"
    }

    experience_result = {
        "score": 70,
        "status": "calculated"
    }

    education_result = {
        "score": 90,
        "status": "calculated"
    }

    semantic_result = {
        "score": 85,
        "status": "calculated"
    }

    result = generate_candidate_score(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        semantic_result=semantic_result,
        job_title="Python Developer",
    )

    assert result["final_score"] is not None

    assert 0 <= result["final_score"] <= 100

    assert result["component_scores"]["skill"]["score"] == 80.0
    assert result["component_scores"]["experience"]["score"] == 70.0
    assert result["component_scores"]["education"]["score"] == 90.0
    assert result["component_scores"]["semantic"]["score"] == 85.0