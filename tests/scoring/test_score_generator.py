import pytest

from scoring.score_generator import generate_candidate_score


# ============================================================
# Helper
# ============================================================

def make_result(
    score,
    status="calculated"
):
    return {
        "score": score,
        "status": status,
    }


# ============================================================
# Test 1: Perfect candidate
# ============================================================

def test_perfect_candidate_score():

    skill_result = make_result(100.0)
    experience_result = make_result(100.0)
    education_result = make_result(100.0)
    semantic_result = make_result(100.0)

    result = generate_candidate_score(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        semantic_result=semantic_result,
        job_title="Python Developer",
    )

    assert result["final_score"] == 100.0

    assert result["status"] == "calculated"

    assert result["role_category"] == "backend"

    assert result["weight_source"] == "role_category"


# ============================================================
# Test 2: Zero candidate score
# ============================================================

def test_zero_candidate_score():

    skill_result = make_result(0.0)
    experience_result = make_result(0.0)
    education_result = make_result(0.0)
    semantic_result = make_result(0.0)

    result = generate_candidate_score(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        semantic_result=semantic_result,
        job_title="Python Developer",
    )

    assert result["final_score"] == 0.0
    assert result["status"] == "calculated"


# ============================================================
# Test 3: Python Developer weighted score
# ============================================================

def test_python_developer_weighted_score():

    skill_result = make_result(75.0)
    experience_result = make_result(50.0)
    education_result = make_result(100.0)
    semantic_result = make_result(80.0)

    result = generate_candidate_score(
        skill_result=skill_result,
        experience_result=experience_result,
        education_result=education_result,
        semantic_result=semantic_result,
        job_title="Python Developer",
    )

    # Backend weights:
    #
    # Skill       = 45%
    # Experience  = 30%
    # Education   = 10%
    # Semantic    = 15%
    #
    # 75 * .45 = 33.75
    # 50 * .30 = 15.00
    # 100 * .10 = 10.00
    # 80 * .15 = 12.00
    #
    # Final = 70.75

    assert result["final_score"] == 70.75


# ============================================================
# Test 4: Contribution calculation
# ============================================================

def test_component_contributions():

    skill_result = make_result(80.0)
    experience_result = make_result(60.0)
    education_result = make_result(100.0)
    semantic_result = make_result(90.0)

    result = generate_candidate_score(
        skill_result,
        experience_result,
        education_result,
        semantic_result,
        "Python Developer",
    )

    assert (
        result["contributions"]["skill"]["contribution"]
        == 36.0
    )

    assert (
        result["contributions"]["experience"]["contribution"]
        == 18.0
    )

    assert (
        result["contributions"]["education"]["contribution"]
        == 10.0
    )

    assert (
        result["contributions"]["semantic"]["contribution"]
        == 13.5
    )


# ============================================================
# Test 5: Weight percentages
# ============================================================

def test_weight_percentages():

    result = generate_candidate_score(
        make_result(100),
        make_result(100),
        make_result(100),
        make_result(100),
        "Python Developer",
    )

    assert (
        result["contributions"]["skill"]
        ["weight_percentage"]
        == 45.0
    )

    assert (
        result["contributions"]["experience"]
        ["weight_percentage"]
        == 30.0
    )

    assert (
        result["contributions"]["education"]
        ["weight_percentage"]
        == 10.0
    )

    assert (
        result["contributions"]["semantic"]
        ["weight_percentage"]
        == 15.0
    )


# ============================================================
# Test 6: Custom weights
# ============================================================

def test_custom_weights():

    custom_weights = {
        "skill": 0.50,
        "experience": 0.25,
        "education": 0.05,
        "semantic": 0.20,
    }

    result = generate_candidate_score(
        skill_result=make_result(80),
        experience_result=make_result(60),
        education_result=make_result(100),
        semantic_result=make_result(90),
        job_title="Python Developer",
        custom_weights=custom_weights,
    )

    # 80 * .50 = 40
    # 60 * .25 = 15
    # 100 * .05 = 5
    # 90 * .20 = 18
    #
    # Final = 78

    assert result["final_score"] == 78.0

    assert result["weight_source"] == "custom"

    assert result["weights"] == custom_weights


# ============================================================
# Test 7: Missing education data
# ============================================================

def test_missing_education_data():

    skill_result = make_result(80)
    experience_result = make_result(60)
    education_result = make_result(
        None,
        status="no_data"
    )
    semantic_result = make_result(90)

    result = generate_candidate_score(
        skill_result,
        experience_result,
        education_result,
        semantic_result,
        "Python Developer",
    )

    # Available weights:
    #
    # Skill       = .45
    # Experience  = .30
    # Semantic    = .15
    #
    # Total = .90
    #
    # Weighted:
    # 80*.45 + 60*.30 + 90*.15
    # = 36 + 18 + 13.5
    # = 67.5
    #
    # Normalized:
    # 67.5 / .90 = 75

    assert result["final_score"] == 75.0

    assert result["status"] == "partial_data"

    assert (
        "education"
        in result["missing_components"]
    )

    assert result["available_weight"] == 0.90


# ============================================================
# Test 8: Missing semantic data
# ============================================================

def test_missing_semantic_data():

    result = generate_candidate_score(
        make_result(80),
        make_result(60),
        make_result(100),
        make_result(
            None,
            status="no_data"
        ),
        "Python Developer",
    )

    # Available weights:
    #
    # .45 + .30 + .10 = .85
    #
    # Weighted:
    # 80*.45 + 60*.30 + 100*.10
    # = 36 + 18 + 10
    # = 64
    #
    # Normalized:
    # 64 / .85 = 75.294...

    assert result["final_score"] == pytest.approx(
        75.29,
        abs=0.01
    )

    assert result["status"] == "partial_data"

    assert (
        "semantic"
        in result["missing_components"]
    )


# ============================================================
# Test 9: All components missing
# ============================================================

def test_all_components_missing():

    result = generate_candidate_score(
        make_result(None, "no_data"),
        make_result(None, "no_data"),
        make_result(None, "no_data"),
        make_result(None, "no_data"),
        "Python Developer",
    )

    assert result["final_score"] is None

    assert result["status"] == "no_data"

    assert set(
        result["missing_components"]
    ) == {
        "skill",
        "experience",
        "education",
        "semantic",
    }


# ============================================================
# Test 10: Frontend role gets frontend weights
# ============================================================

def test_frontend_role_weights():

    result = generate_candidate_score(
        make_result(80),
        make_result(70),
        make_result(90),
        make_result(85),
        "React Developer",
    )

    assert result["role_category"] == "frontend"

    assert (
        result["weights"]["skill"]
        == 0.45
    )

    assert (
        result["weights"]["experience"]
        == 0.25
    )

    assert (
        result["weights"]["education"]
        == 0.10
    )

    assert (
        result["weights"]["semantic"]
        == 0.20
    )


# ============================================================
# Test 11: Data scientist role
# ============================================================

def test_data_scientist_role():

    result = generate_candidate_score(
        make_result(80),
        make_result(70),
        make_result(90),
        make_result(85),
        "Data Scientist",
    )

    assert result["role_category"] == "data_ml"

    assert result["weights"] == {
        "skill": 0.40,
        "experience": 0.25,
        "education": 0.15,
        "semantic": 0.20,
    }


# ============================================================
# Test 12: Unknown role uses general category
# ============================================================

def test_unknown_role():

    result = generate_candidate_score(
        make_result(80),
        make_result(70),
        make_result(90),
        make_result(85),
        "Blockchain Architect",
    )

    assert result["role_category"] == "general"

    assert result["weight_source"] == "role_category"

    assert result["weights"] == {
        "skill": 0.40,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.20,
    }


# ============================================================
# Test 13: Component scores are preserved
# ============================================================

def test_component_scores():

    result = generate_candidate_score(
        make_result(85),
        make_result(70),
        make_result(90),
        make_result(75),
        "Python Developer",
    )

    assert (
        result["component_scores"]["skill"]["score"]
        == 85.0
    )

    assert (
        result["component_scores"]["experience"]["score"]
        == 70.0
    )

    assert (
        result["component_scores"]["education"]["score"]
        == 90.0
    )

    assert (
        result["component_scores"]["semantic"]["score"]
        == 75.0
    )


# ============================================================
# Test 14: Explanation is generated
# ============================================================

def test_explanation_is_generated():

    result = generate_candidate_score(
        make_result(80),
        make_result(70),
        make_result(90),
        make_result(85),
        "Python Developer",
    )

    assert isinstance(
        result["explanation"],
        list
    )

    assert len(
        result["explanation"]
    ) == 4


# ============================================================
# Test 15: Partial data explanation
# ============================================================

def test_partial_data_explanation():

    result = generate_candidate_score(
        make_result(80),
        make_result(70),
        make_result(
            None,
            "no_data"
        ),
        make_result(85),
        "Python Developer",
    )

    assert result["status"] == "partial_data"

    explanation = " ".join(
        result["explanation"]
    )

    assert "Missing components" in explanation

    assert "education" in explanation