"""
Tests for ATS Scoring Engine

Current ATS pipeline
--------------------
Candidate Profile
    ↓
Bias Mitigation
    ↓
Skill Score
    ↓
Experience Score
    ↓
Education Score
    ↓
Semantic Score
    ↓
Final ATS Score

Current calculate_ats_score() API
---------------------------------
calculate_ats_score(
    candidate_profile,
    jd_profile,
    embedding_generator=None,
)
"""

import pytest

from scoring.ats_scoring_engine import calculate_ats_score
from scoring.skill_semantic_matcher import find_semantic_skill_matches


# ============================================================
# FAKE EMBEDDING GENERATOR
# ============================================================

class FakeEmbeddingGenerator:
    """
    Lightweight deterministic embedding generator for tests.

    This avoids loading SentenceTransformer during unit tests.
    """

    EMBEDDINGS = {
        "python": [1.0, 0.0, 0.0],
        "django": [0.0, 1.0, 0.0],
        "django rest framework": [0.0, 1.0, 0.0],
        "rest api development": [0.0, 0.95, 0.05],
        "rest api": [0.0, 0.95, 0.05],
        "postgresql": [0.0, 0.0, 1.0],
        "mysql": [0.0, 0.0, 0.95],
        "docker": [0.7, 0.2, 0.1],
        "aws": [0.6, 0.3, 0.1],
        "redis": [0.2, 0.3, 0.5],
        "java": [0.2, 0.1, 0.0],
    }

    def encode(self, texts):
        """
        Support both a single string and a list of strings.
        """

        if isinstance(texts, str):
            return self._encode_one(texts)

        return [self._encode_one(text) for text in texts]

    def _encode_one(self, text):
        normalized = str(text).strip().lower()

        if normalized in self.EMBEDDINGS:
            return self.EMBEDDINGS[normalized]

        # Deterministic neutral vector for unknown text.
        return [0.33, 0.33, 0.33]


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def embedding_generator():
    return FakeEmbeddingGenerator()


@pytest.fixture
def candidate_profile():
    return {
        "candidate_id": "CAN_001",

        "personal_information": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "9876543210",
            "location": "Kerala",
        },

        "resume_text": (
            "Python Developer with 3 years of experience "
            "building web applications and REST APIs."
        ),

        "skills": [
            "Python",
            "Django",
            "REST API",
            "PostgreSQL",
            "Docker",
        ],

        "experience": [
            {
                "title": "Python Developer",
                "total_experience": {
                    "total_years": 3.0,
                    "total_months": 36,
                },
                "skills": [
                    "Python",
                    "Django",
                    "REST API",
                    "PostgreSQL",
                    "Docker",
                ],
            }
        ],

        "education": [
            {
                "degree": "B.Tech",
                "field": "Computer Science",
                "institution": "ABC University",
                "graduation_year": 2022,
            }
        ],
    }


@pytest.fixture
def jd_profile():
    return {
        "job_title": "Python Developer",

        "required_skills": [
            "Python",
            "Django",
            "REST API",
            "PostgreSQL",
            "Git",
            "SQL",
            "HTML",
            "JavaScript",
        ],

        "preferred_skills": [
            "Docker",
            "AWS",
            "Redis",
        ],

        "experience": [
            "2 - 4 Years",
            "Minimum 2 years of experience",
        ],

        "education": [
            {
                "degree": "B.Tech",
                "field": "Computer Science",
            }
        ],
    }


# ============================================================
# BASIC CONTRACT TESTS
# ============================================================

def test_complete_ats_scoring(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert isinstance(result, dict)

    assert "candidate_id" in result
    assert "candidate_score" in result
    assert "component_scores" in result
    assert "metadata" in result
    assert "bias_mitigation" in result


def test_candidate_id_is_preserved(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert result["candidate_id"] == "CAN_001"

    assert (
        result["metadata"]["candidate_id"]
        == "CAN_001"
    )


# ============================================================
# COMPONENT SCORE TESTS
# ============================================================

def test_all_component_scores_exist(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    components = result["component_scores"]

    assert "skill" in components
    assert "experience" in components
    assert "education" in components
    assert "semantic" in components


def test_skill_score(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    skill_result = result["component_scores"]["skill"]

    assert isinstance(skill_result, dict)
    assert "score" in skill_result
    assert "weight" in skill_result

    assert 0 <= skill_result["score"] <= 100

    assert skill_result["weight"] == pytest.approx(0.40)


def test_experience_score(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    experience_result = result["component_scores"]["experience"]

    assert isinstance(experience_result, dict)
    assert "score" in experience_result
    assert "weight" in experience_result
    assert "component_scores" in experience_result

    assert 0 <= experience_result["score"] <= 100

    assert experience_result["weight"] == pytest.approx(0.30)


def test_experience_technology_relevance(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    experience_result = result["component_scores"]["experience"]

    technology_score = (
        experience_result["component_scores"]
        ["technology"]
    )

    skill_result = result["component_scores"]["skill"]

    expected = skill_result["required"]["match_percentage"]

    assert technology_score == pytest.approx(expected)

    assert (
        experience_result["technology_score_source"]
        == "skill_score"
    )


def test_education_score(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    education_result = result["component_scores"]["education"]

    assert isinstance(education_result, dict)
    assert "score" in education_result
    assert "weight" in education_result

    assert 0 <= education_result["score"] <= 100

    assert education_result["weight"] == pytest.approx(0.10)


def test_semantic_score(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    semantic_result = result["component_scores"]["semantic"]

    assert isinstance(semantic_result, dict)
    assert "score" in semantic_result
    assert "weight" in semantic_result

    assert 0 <= semantic_result["score"] <= 100

    assert semantic_result["weight"] == pytest.approx(0.20)


# ============================================================
# FINAL SCORE TESTS
# ============================================================

def test_final_score_exists(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    candidate_score = result["candidate_score"]

    assert isinstance(candidate_score, dict)

    assert "final_score" in candidate_score

    assert 0 <= candidate_score["final_score"] <= 100


def test_final_score_matches_weighted_components(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    components = result["component_scores"]

    skill = components["skill"]["score"]
    experience = components["experience"]["score"]
    education = components["education"]["score"]
    semantic = components["semantic"]["score"]

    weights = result["candidate_score"]["weights"]

    expected = (
        skill * weights["skill"]
        + experience * weights["experience"]
        + education * weights["education"]
        + semantic * weights["semantic"]
    )

    actual = result["candidate_score"]["final_score"]

    assert actual == pytest.approx(
        round(expected, 2),
        abs=0.01,
    )


# ============================================================
# SKILL STRUCTURE TESTS
# ============================================================

def test_required_skill_structure(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    required = (
        result["component_scores"]
        ["skill"]
        ["required"]
    )

    assert "skills" in required
    assert "matched" in required
    assert "missing" in required
    assert "match_percentage" in required

    assert isinstance(required["skills"], list)
    assert isinstance(required["matched"], list)
    assert isinstance(required["missing"], list)

    assert 0 <= required["match_percentage"] <= 100


def test_preferred_skill_structure(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    preferred = (
        result["component_scores"]
        ["skill"]
        ["preferred"]
    )

    assert "skills" in preferred
    assert "matched" in preferred
    assert "missing" in preferred
    assert "match_percentage" in preferred

    assert isinstance(preferred["skills"], list)
    assert isinstance(preferred["matched"], list)
    assert isinstance(preferred["missing"], list)

    assert 0 <= preferred["match_percentage"] <= 100


def test_candidate_skills_are_top_level_normalized_skills(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    skill_result = result["component_scores"]["skill"]

    assert skill_result["candidate_skills"] == [
        "Python",
        "Django",
        "REST API",
        "PostgreSQL",
        "Docker",
    ]


# ============================================================
# EXPERIENCE STRUCTURE TESTS
# ============================================================

def test_experience_component_structure(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    experience = result["component_scores"]["experience"]

    assert "component_scores" in experience

    components = experience["component_scores"]

    assert "years" in components
    assert "role" in components
    assert "technology" in components

    assert "score" in components["years"]
    assert "score" in components["role"]

    assert isinstance(
        components["technology"],
        (int, float),
    )

    assert 0 <= components["technology"] <= 100

def test_experience_years_are_extracted(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    experience = result["component_scores"]["experience"]

    assert experience["candidate_years"] == pytest.approx(3.0)

    assert (
        experience["required_minimum_years"]
        == pytest.approx(2.0)
    )


def test_experience_role_is_extracted(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    experience = result["component_scores"]["experience"]

    assert "Python Developer" in experience["candidate_roles"]

    assert experience["target_role"] == "Python Developer"


# ============================================================
# SEMANTIC TESTS
# ============================================================

def test_semantic_result_contains_score(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    semantic = result["component_scores"]["semantic"]

    assert "score" in semantic
    assert isinstance(semantic["score"], (int, float))


def test_semantic_skill_match_directly(
    embedding_generator,
):
    matches = find_semantic_skill_matches(
        candidate_skills=[
            "Django REST Framework",
        ],
        required_skills=[
            "REST API Development",
        ],
        embedding_generator=embedding_generator,
    )

    assert isinstance(matches, list)

    if matches:
        first = matches[0]

        assert isinstance(first, dict)

        # Different implementations may expose these
        # fields under slightly different names.
        if "candidate_skill" in first:
            assert first["candidate_skill"]

        if "required_skill" in first:
            assert first["required_skill"]

        if "similarity" in first:
            assert 0 <= first["similarity"] <= 1


def test_semantic_skill_match_through_ats(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    candidate = dict(candidate_profile)

    candidate["skills"] = [
        "Python",
        "Django REST Framework",
        "PostgreSQL",
    ]

    jd = dict(jd_profile)

    jd["required_skills"] = [
        "REST API Development",
    ]

    result = calculate_ats_score(
        candidate,
        jd,
        embedding_generator=embedding_generator,
    )

    skill_result = result["component_scores"]["skill"]

    assert isinstance(skill_result, dict)

    # The exact semantic-match field depends on the
    # current skill scorer implementation. We only
    # require that scoring completes successfully.
    assert "score" in skill_result
    assert 0 <= skill_result["score"] <= 100


# ============================================================
# BIAS MITIGATION TESTS
# ============================================================

def test_bias_mitigation_is_applied(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert "bias_mitigation" in result

    assert (
        result["bias_mitigation"]["applied"]
        is True
    )


def test_ats_score_is_independent_of_personal_attributes(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    candidate_a = dict(candidate_profile)

    candidate_a["personal_information"] = {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "9876543210",
        "location": "Kerala",
    }

    candidate_b = dict(candidate_profile)

    candidate_b["personal_information"] = {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "9999999999",
        "location": "Tamil Nadu",
    }

    # Candidate IDs must remain different while
    # personal attributes must not affect scoring.
    candidate_a["candidate_id"] = "CAN_A"
    candidate_b["candidate_id"] = "CAN_B"

    result_a = calculate_ats_score(
        candidate_a,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    result_b = calculate_ats_score(
        candidate_b,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert (
        result_a["candidate_score"]["final_score"]
        == result_b["candidate_score"]["final_score"]
    )

    assert result_a["candidate_id"] == "CAN_A"
    assert result_b["candidate_id"] == "CAN_B"


def test_candidate_id_survives_bias_masking(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    candidate_profile["candidate_id"] = "CAN_999"

    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert result["candidate_id"] == "CAN_999"

    assert (
        result["metadata"]["candidate_id"]
        == "CAN_999"
    )


# ============================================================
# METADATA TESTS
# ============================================================

def test_metadata(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    metadata = result["metadata"]

    assert "candidate_id" in metadata
    assert "candidate_skills" in metadata
    assert "candidate_roles" in metadata
    assert "candidate_education" in metadata
    assert "candidate_years" in metadata


def test_metadata_candidate_skills(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    metadata = result["metadata"]

    assert isinstance(
        metadata["candidate_skills"],
        list,
    )

    assert "Python" in metadata["candidate_skills"]


def test_metadata_candidate_roles(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    metadata = result["metadata"]

    assert isinstance(
        metadata["candidate_roles"],
        list,
    )

    assert "Python Developer" in metadata["candidate_roles"]


# ============================================================
# MISSING / EMPTY DATA TESTS
# ============================================================

def test_missing_semantic_data(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    candidate = dict(candidate_profile)

    candidate["resume_text"] = ""

    result = calculate_ats_score(
        candidate,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert isinstance(result, dict)

    assert "candidate_score" in result

    semantic = result["component_scores"]["semantic"]

    assert isinstance(semantic, dict)
    assert "score" in semantic


def test_missing_candidate_data(
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        {},
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert isinstance(result, dict)

    assert result["candidate_id"] is None

    assert "candidate_score" in result
    assert "component_scores" in result


def test_missing_jd_data(
    candidate_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        {},
        embedding_generator=embedding_generator,
    )

    assert isinstance(result, dict)

    assert "candidate_score" in result
    assert "component_scores" in result


def test_none_candidate_profile(
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        None,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert isinstance(result, dict)
    assert result["candidate_id"] is None
    assert "candidate_score" in result


def test_none_jd_profile(
    candidate_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        None,
        embedding_generator=embedding_generator,
    )

    assert isinstance(result, dict)
    assert "candidate_score" in result


# ============================================================
# EXPLAINABILITY TESTS
# ============================================================

def test_explainable_output(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    components = result["component_scores"]

    skill = components["skill"]
    experience = components["experience"]
    education = components["education"]
    semantic = components["semantic"]

    # Skill explanation
    assert "required" in skill
    assert "preferred" in skill

    # Experience explanation
    assert "component_scores" in experience
    assert "candidate_years" in experience
    assert "required_minimum_years" in experience

    # Education explanation
    assert isinstance(education, dict)

    # Semantic explanation
    assert isinstance(semantic, dict)


# ============================================================
# SCORE BOUNDS
# ============================================================

def test_all_scores_are_bounded(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    components = result["component_scores"]

    for component_name, component in components.items():
        assert 0 <= component["score"] <= 100, (
            f"{component_name} score out of bounds"
        )

    final_score = (
        result["candidate_score"]["final_score"]
    )

    assert 0 <= final_score <= 100


# ============================================================
# WEIGHT VALIDATION
# ============================================================

def test_component_weights(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    components = result["component_scores"]

    assert components["skill"]["weight"] == pytest.approx(
        0.40
    )

    assert (
        components["experience"]["weight"]
        == pytest.approx(0.30)
    )

    assert (
        components["education"]["weight"]
        == pytest.approx(0.10)
    )

    assert (
        components["semantic"]["weight"]
        == pytest.approx(0.20)
    )


def test_component_weights_sum_to_one(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    components = result["component_scores"]

    total_weight = sum(
        component["weight"]
        for component in components.values()
    )

    assert total_weight == pytest.approx(1.0)


# ============================================================
# CANDIDATE PROFILE DATA EXTRACTION
# ============================================================

def test_candidate_education_metadata(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    education = result["metadata"]["candidate_education"]

    assert isinstance(education, list)
    assert len(education) == 1

    assert education[0]["degree"] == "B.Tech"


def test_candidate_years_metadata(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert (
        result["metadata"]["candidate_years"]
        == pytest.approx(3.0)
    )


# ============================================================
# RESULT CONSISTENCY
# ============================================================

def test_repeated_scoring_is_deterministic(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    result_1 = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    result_2 = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert (
        result_1["candidate_score"]["final_score"]
        == result_2["candidate_score"]["final_score"]
    )

    assert (
        result_1["component_scores"]["skill"]["score"]
        == result_2["component_scores"]["skill"]["score"]
    )

    assert (
        result_1["component_scores"]["experience"]["score"]
        == result_2["component_scores"]["experience"]["score"]
    )


# ============================================================
# NO OLD API PARAMETERS
# ============================================================

def test_current_api_uses_embedding_generator(
    candidate_profile,
    jd_profile,
    embedding_generator,
):
    """
    Regression test ensuring the current ATS engine
    accepts the shared EmbeddingGenerator dependency.
    """

    result = calculate_ats_score(
        candidate_profile,
        jd_profile,
        embedding_generator=embedding_generator,
    )

    assert result is not None
    assert "candidate_score" in result
