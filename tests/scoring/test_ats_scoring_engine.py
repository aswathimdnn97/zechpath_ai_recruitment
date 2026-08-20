import pytest

import numpy as np


class FakeEmbeddingModel:

    def encode(
        self,
        text,
        convert_to_numpy=True,
    ):

        text = str(text).strip().lower()

        vectors = {
            "python": [
                1.0,
                0.0,
                0.0,
            ],

            "django rest framework": [
                0.0,
                1.0,
                0.0,
            ],

            "rest api development": [
                0.0,
                0.95,
                0.05,
            ],

            "postgresql": [
                0.0,
                0.0,
                1.0,
            ],
        }

        if text not in vectors:
            raise ValueError(
                f"Fake embedding not defined for: {text}"
            )

        return np.asarray(
            vectors[text],
            dtype=float,
        )


class FakeEmbeddingGenerator:

    def __init__(self):
        self.model = FakeEmbeddingModel()
        
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

    skill_result = result["component_scores"]["skill"]

    print("Matched:", skill_result["matched_required_skills"])
    print("Missing:", skill_result["missing_required_skills"])
    print("Fuzzy:", skill_result["fuzzy_required_matches"])

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
    
    
def test_semantic_skill_matcher_directly():

    embedding_generator = FakeEmbeddingGenerator()

    from scoring.skill_semantic_matcher import (
        find_semantic_skill_matches,
    )

    matches = find_semantic_skill_matches(
        candidate_skills=[
            "django rest framework",
            "python",
            "postgresql",
        ],
        jd_skills=[
            "rest api development",
        ],
        embedding_generator=embedding_generator,
        threshold=0.70,
    )

    print(
        "DIRECT SEMANTIC MATCHES:",
        matches,
    )

    assert len(matches) == 1

    assert (
        matches[0]["jd_skill"]
        == "rest api development"
    )

    assert (
        matches[0]["candidate_skill"]
        == "django rest framework"
    )

    assert (
        matches[0]["match_type"]
        == "semantic"
    )

    assert (
        matches[0]["similarity"]
        >= 0.70
    )
    
def test_semantic_skill_match():

    embedding_generator = FakeEmbeddingGenerator()

    candidate = {
        "resume_text": {
            "skills": [
                "Python",
                "Django REST Framework",
                "PostgreSQL",
            ]
        }
    }

    jd = {
        "job_title": "Python Developer",
        "required_skills": [
            "Python",
            "REST API development",
            "PostgreSQL",
        ],
        "preferred_skills": [],
    }

    result = calculate_ats_score(
        candidate,
        jd,
        resume_embedding=[
            1.0,
            0.0,
            0.0,
        ],
        jd_embedding=[
            1.0,
            0.0,
            0.0,
        ],
        embedding_generator=embedding_generator,
    )

    skill_result = result[
        "component_scores"
    ]["skill"]

    print(
        "Matched:",
        skill_result[
            "matched_required_skills"
        ],
    )

    print(
        "Missing:",
        skill_result[
            "missing_required_skills"
        ],
    )

    print(
        "Semantic:",
        skill_result[
            "semantic_required_matches"
        ],
    )

    assert (
        skill_result["required_total"]
        == 3
    )

    assert (
        skill_result["required_matched"]
        == 3
    )

    assert (
        skill_result[
            "missing_required_skills"
        ]
        == []
    )

    semantic_matches = skill_result[
        "semantic_required_matches"
    ]

    assert len(
        semantic_matches
    ) == 1

    assert (
        semantic_matches[0]["jd_skill"]
        == "rest api development"
    )

    assert (
        semantic_matches[0]["candidate_skill"]
        == "django rest framework"
    )

    assert (
        semantic_matches[0]["match_type"]
        == "semantic"
    )

    assert (
        semantic_matches[0]["similarity"]
        >= 0.70
    )
    
    
def test_ats_score_is_independent_of_personal_attributes():
    """
    Personal attributes such as name, email, phone, LinkedIn,
    and GitHub must not affect the ATS score.

    candidate_id is allowed to differ because it is an
    identifier, not a scoring feature.
    """

    candidate_1 = {
        "candidate_id": "CAN_001",

        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "9876543210",
        "linkedin": "linkedin.com/in/john",
        "github": "github.com/john",

        "skill": [
            {
                "skill_name": "Python",
                "experience": 3,
                "profficiency": "Advanced",
            },
            {
                "skill_name": "Django",
                "experience": 2,
                "profficiency": "Advanced",
            },
        ],

        "experience": [
            {
                "company_name": "ABC Technologies",
                "employment_type": "Full-time",
                "start_date": "2021",
                "end_date": "2024",
                "currently_working": False,
                "responsibility": [
                    "Developed Python applications"
                ],
                "technologies": [
                    "Python",
                    "Django",
                ],
            }
        ],

        "education": [
            {
                "degree": "BTech",
                "specialization": "Computer Science",
                "institution": "ABC University",
                "graduation_year": 2021,
                "cgpa": 8,
            }
        ],
    }

    candidate_2 = {
        "candidate_id": "CAN_002",

        # Completely different personal information
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com",
        "phone": "1234567890",
        "linkedin": "linkedin.com/in/alice",
        "github": "github.com/alice",

        # SAME professional information
        "skill": [
            {
                "skill_name": "Python",
                "experience": 3,
                "profficiency": "Advanced",
            },
            {
                "skill_name": "Django",
                "experience": 2,
                "profficiency": "Advanced",
            },
        ],

        "experience": [
            {
                "company_name": "ABC Technologies",
                "employment_type": "Full-time",
                "start_date": "2021",
                "end_date": "2024",
                "currently_working": False,
                "responsibility": [
                    "Developed Python applications"
                ],
                "technologies": [
                    "Python",
                    "Django",
                ],
            }
        ],

        "education": [
            {
                "degree": "BTech",
                "specialization": "Computer Science",
                "institution": "ABC University",
                "graduation_year": 2021,
                "cgpa": 8,
            }
        ],
    }

    jd = {
        "job_title": "Python Developer",

        "required_skills": [
            "Python",
            "Django",
        ],

        "preferred_skills": [],

        "experience": [
            {
                "min_years": 2,
            }
        ],

        "education": [
            {
                "degree": "BTech",
            }
        ],
    }

    # Same embeddings because professional content is identical.
    resume_embedding = [
        1.0,
        0.0,
        0.0,
    ]

    jd_embedding = [
        1.0,
        0.0,
        0.0,
    ]

    # ========================================================
    # Score candidate 1
    # ========================================================

    result_1 = calculate_ats_score(
        candidate_1,
        jd,
        resume_embedding=resume_embedding,
        jd_embedding=jd_embedding,
    )

    # ========================================================
    # Score candidate 2
    # ========================================================

    result_2 = calculate_ats_score(
        candidate_2,
        jd,
        resume_embedding=resume_embedding,
        jd_embedding=jd_embedding,
    )

    # ========================================================
    # Extract final scores
    # ========================================================

    score_1 = result_1[
        "candidate_score"
    ]["final_score"]

    score_2 = result_2[
        "candidate_score"
    ]["final_score"]

    print("Candidate 1 score:", score_1)
    print("Candidate 2 score:", score_2)

    # ========================================================
    # Main bias-mitigation assertion
    # ========================================================

    assert score_1 == score_2

    # ========================================================
    # Candidate identity must still be preserved
    # ========================================================

    assert result_1["candidate_id"] == "CAN_001"
    assert result_2["candidate_id"] == "CAN_002"

    # ========================================================
    # Bias mitigation metadata
    # ========================================================

    assert (
        result_1["bias_mitigation"]
        ["personal_attributes_masked"]
        is True
    )

    assert (
        result_2["bias_mitigation"]
        ["personal_attributes_masked"]
        is True
    )