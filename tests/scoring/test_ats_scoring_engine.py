import pytest

from scoring.ats_scoring_engine import calculate_ats_score


# ============================================================
# Test data
# ============================================================

def candidate_profile():
    return {
        "resume_text": {
            "personal_information": {
                "name": "John Doe"
            },

            "skills": [
                "Python",
                "Django",
                "REST API",
                "PostgreSQL",
                "Git"
            ],

            "experience": [
                {
                    "title": "Python Developer",
                    "total_experience": {
                        "total_years": 3.0
                    },
                    "skills": [
                        "Python",
                        "Django",
                        "REST API",
                        "PostgreSQL",
                        "Git"
                    ]
                }
            ],

            "education": [
                {
                    "degree": "B.Tech",
                    "field": "Computer Science"
                }
            ]
        }
    }


def jd_profile():
    return {
        "resume_text": {
            "job_title": "Python Developer",

            "required_skills": [
                "Python",
                "Django",
                "Django REST Framework",
                "REST API",
                "PostgreSQL",
                "Git",
                "Object-Oriented Programming",
                "SQL"
            ],

            "preferred_skills": [
                "Docker",
                "AWS",
                "Redis"
            ],

            "experience": [
                "2 - 4 Years",
                "Minimum 2 years of Python development experience."
            ],

            "education": [
                "Bachelor's degree in Computer Science, Information Technology, Electronics, or related field."
            ]
        }
    }


# ============================================================
# Test 1: Complete ATS scoring
# ============================================================

def test_complete_ats_scoring():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    assert "candidate_score" in result
    assert "component_scores" in result
    assert "metadata" in result


# ============================================================
# Test 2: All four component scores exist
# ============================================================

def test_all_component_scores_exist():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    components = result["component_scores"]

    assert "skill" in components
    assert "experience" in components
    assert "education" in components
    assert "semantic" in components


# ============================================================
# Test 3: Skill scorer is called correctly
# ============================================================

# ============================================================
# Test 3: Skill scorer is called correctly
# ============================================================

def test_skill_score():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    skill_result = result[
        "component_scores"
    ]["skill"]

    assert skill_result["required_total"] == 8

    assert skill_result["required_matched"] == 5

    # Skills are normalized to lowercase by skill_score.py
    assert "python" in (
        skill_result[
            "matched_required_skills"
        ]
    )

# ============================================================
# Test 4: Experience scorer receives candidate data
# ============================================================

def test_experience_score():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    experience_result = result[
        "component_scores"
    ]["experience"]

    assert experience_result[
        "candidate_years"
    ] == 3.0

    assert experience_result[
        "required_minimum_years"
    ] == 2.0

    assert experience_result[
        "target_job_title"
    ] == "Python Developer"

    assert experience_result[
        "role_relevance_score"
    ] == 100.0


# ============================================================
# Test 5: Technology relevance
# ============================================================

def test_experience_technology_relevance():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    experience_result = result[
        "component_scores"
    ]["experience"]

    assert (
        experience_result[
            "technology_relevance_score"
        ]
        == 62.5
    )


# ============================================================
# Test 6: Education score
# ============================================================

def test_education_score():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    education_result = result[
        "component_scores"
    ]["education"]

    assert education_result[
        "degree_score"
    ] == 100.0

    assert education_result[
        "field_score"
    ] == 100.0

    assert education_result[
        "score"
    ] == 100.0


# ============================================================
# Test 7: Semantic score
# ============================================================

def test_semantic_score():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    semantic_result = result[
        "component_scores"
    ]["semantic"]

    assert semantic_result[
        "similarity"
    ] == 1.0

    assert semantic_result[
        "score"
    ] == 100.0


# ============================================================
# Test 8: Final score exists
# ============================================================

def test_final_score_exists():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    final_score = result[
        "candidate_score"
    ]["final_score"]

    assert final_score is not None

    assert 0 <= final_score <= 100


# ============================================================
# Test 9: Metadata
# ============================================================

def test_metadata():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    metadata = result["metadata"]

    assert metadata[
        "job_title"
    ] == "Python Developer"

    assert metadata[
        "required_skills_count"
    ] == 8

    assert metadata[
        "preferred_skills_count"
    ] == 3

    assert metadata[
        "candidate_skills_count"
    ] == 5

    assert metadata[
        "candidate_years"
    ] == 3.0

    assert "Python Developer" in (
        metadata["candidate_roles"]
    )


# ============================================================
# Test 10: Missing semantic data
# ============================================================

def test_missing_semantic_data():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=None,
        jd_embedding=None,
    )

    semantic_result = result[
        "component_scores"
    ]["semantic"]

    assert semantic_result[
        "status"
    ] == "no_data"

    assert semantic_result[
        "score"
    ] is None


# ============================================================
# Test 11: Missing candidate data
# ============================================================

def test_missing_candidate_data():

    candidate = {
        "resume_text": {}
    }

    result = calculate_ats_score(
        candidate,
        jd_profile(),
        resume_embedding=None,
        jd_embedding=None,
    )

    assert "candidate_score" in result

    assert result[
        "component_scores"
    ]["semantic"]["status"] == "no_data"

    assert result[
        "component_scores"
    ]["experience"]["candidate_years"] == 0.0


# ============================================================
# Test 12: Custom weights
# ============================================================

def test_custom_weights():

    custom_weights = {
        "skill": 0.50,
        "experience": 0.25,
        "education": 0.10,
        "semantic": 0.15,
    }

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
        custom_weights=custom_weights,
    )

    candidate_score = result[
        "candidate_score"
    ]

    assert candidate_score[
        "weight_source"
    ] == "custom"

    assert candidate_score[
        "weights"
    ] == custom_weights


# ============================================================
# Test 13: Different embeddings
# ============================================================

def test_different_embeddings():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0],
        jd_embedding=[0.0, 1.0],
    )

    semantic_result = result[
        "component_scores"
    ]["semantic"]

    assert semantic_result[
        "similarity"
    ] == 0.0

    assert semantic_result[
        "score"
    ] == 50.0


# ============================================================
# Test 14: Invalid embedding dimensions
# ============================================================

def test_invalid_embedding_dimensions():

    with pytest.raises(ValueError):

        calculate_ats_score(
            candidate_profile(),
            jd_profile(),
            resume_embedding=[
                1.0,
                0.0
            ],
            jd_embedding=[
                1.0,
                0.0,
                0.0
            ],
        )


# ============================================================
# Test 15: Explainable output
# ============================================================

def test_explainable_output():

    result = calculate_ats_score(
        candidate_profile(),
        jd_profile(),
        resume_embedding=[1.0, 0.0, 0.0],
        jd_embedding=[1.0, 0.0, 0.0],
    )

    candidate_score = result[
        "candidate_score"
    ]

    assert "explanation" in candidate_score

    assert isinstance(
        candidate_score["explanation"],
        list,
    )

    assert len(
        candidate_score["explanation"]
    ) > 0