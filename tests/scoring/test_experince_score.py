"""
Tests for scoring.experince_score

Covers:
    - Required experience extraction
    - Year scoring
    - Role relevance
    - Legacy technology relevance
    - Full experience scoring
    - Partial experience scoring
    - Missing candidate experience
    - Missing JD experience requirement
    - Empty profiles
    - Skill-score integration
"""

from typing import Any, Dict, Optional

import pytest

from scoring.experince_score import (
    extract_required_years,
    calculate_year_score,
    calculate_role_relevance,
    calculate_technology_relevance,
    calculate_experience_score,
)


# ============================================================
# Test 1: Extract experience range from JD
# ============================================================

def test_extract_experience_range():
    experience = "2 - 4 Years"

    result = extract_required_years(experience)

    assert result["minimum_years"] == 2.0
    assert result["maximum_years"] == 4.0


# ============================================================
# Test 2: Extract minimum experience from list
# ============================================================

def test_extract_minimum_years():
    experience = [
        "Minimum 3 years of Python development experience."
    ]

    result = extract_required_years(experience)

    assert result["minimum_years"] == 3.0
    assert result["maximum_years"] is None


# ============================================================
# Test 3: Extract 3+ years
# ============================================================

def test_extract_plus_years():

    result = extract_required_years("3+ years")

    assert result["minimum_years"] == 3.0
    assert result["maximum_years"] is None


# ============================================================
# Test 4: Extract "at least" experience
# ============================================================

def test_extract_at_least_years():

    result = extract_required_years(
        "At least 2 years of Python experience"
    )

    assert result["minimum_years"] == 2.0
    assert result["maximum_years"] is None


# ============================================================
# Test 5: Extract generic years
# ============================================================

def test_extract_generic_years():

    result = extract_required_years(
        "2 years of backend development experience"
    )

    assert result["minimum_years"] == 2.0
    assert result["maximum_years"] is None


# ============================================================
# Test 6: Extract years from dictionary
# ============================================================

def test_extract_years_from_dict():

    experience = {
        "minimum_years": 2,
        "maximum_years": 4,
    }

    result = extract_required_years(experience)

    assert result["minimum_years"] == 2.0
    assert result["maximum_years"] == 4.0


# ============================================================
# Test 7: Extract years from dictionary description
# ============================================================

def test_extract_years_from_dict_description():

    experience = {
        "description": "Minimum 3 years of Python experience"
    }

    result = extract_required_years(experience)

    assert result["minimum_years"] == 3.0
    assert result["maximum_years"] is None


# ============================================================
# Test 8: Candidate meets minimum experience
# ============================================================

def test_candidate_meets_required_years():

    result = calculate_year_score(
        candidate_years=3.0,
        required_years=2.0,
    )

    assert result == 100.0


# ============================================================
# Test 9: Candidate exceeds minimum experience
# ============================================================

def test_candidate_exceeds_required_years():

    result = calculate_year_score(
        candidate_years=5.0,
        required_years=2.0,
    )

    assert result == 100.0


# ============================================================
# Test 10: Candidate has insufficient experience
# ============================================================

def test_candidate_has_insufficient_experience():

    result = calculate_year_score(
        candidate_years=1.0,
        required_years=2.0,
    )

    assert result == 50.0


# ============================================================
# Test 11: No experience requirement
# ============================================================

def test_no_experience_requirement():

    result = calculate_year_score(
        candidate_years=2.0,
        required_years=0.0,
    )

    assert result == 100.0


# ============================================================
# Test 12: Zero candidate experience
# ============================================================

def test_zero_candidate_experience():

    result = calculate_year_score(
        candidate_years=0.0,
        required_years=2.0,
    )

    assert result == 0.0


# ============================================================
# Test 13: Exact job-title match
# ============================================================

def test_exact_role_match():

    result = calculate_role_relevance(
        candidate_roles=[
            "Python Developer"
        ],
        target_role="Python Developer",
    )

    assert result == 100.0


# ============================================================
# Test 14: Partial / senior role match
# ============================================================

def test_partial_role_match():

    result = calculate_role_relevance(
        candidate_roles=[
            "Senior Python Developer"
        ],
        target_role="Python Developer",
    )

    assert result == 100.0


# ============================================================
# Test 15: No job-title match
# ============================================================

def test_no_role_match():

    result = calculate_role_relevance(
        candidate_roles=[
            "Java Developer"
        ],
        target_role="Python Developer",
    )

    assert result == 50.0


# ============================================================
# Test 16: Empty candidate roles
# ============================================================

def test_empty_candidate_roles():

    result = calculate_role_relevance(
        candidate_roles=[],
        target_role="Python Developer",
    )

    assert result == 0.0


# ============================================================
# Test 17: Empty target role
# ============================================================

def test_empty_target_role():

    result = calculate_role_relevance(
        candidate_roles=["Python Developer"],
        target_role="",
    )

    assert result == 0.0


# ============================================================
# Test 18: Required technology matching
#
# This is the legacy technology scorer.
# The main ATS pipeline now gets technology relevance
# from SkillScore.
# ============================================================

def test_technology_relevance():

    candidate_skills = [
        "Python",
        "Django",
        "PostgreSQL",
        "REST API",
    ]

    required_skills = [
        "Python",
        "Django",
        "PostgreSQL",
        "REST API",
    ]

    result = calculate_technology_relevance(
        candidate_skills,
        required_skills,
    )

    assert result == 100.0


# ============================================================
# Test 19: Partial technology matching
# ============================================================

def test_partial_technology_relevance():

    candidate_skills = [
        "Python",
        "Django",
    ]

    required_skills = [
        "Python",
        "Django",
        "PostgreSQL",
        "REST API",
    ]

    result = calculate_technology_relevance(
        candidate_skills,
        required_skills,
    )

    assert result == 50.0


# ============================================================
# Test 20: No technology match
# ============================================================

def test_no_technology_match():

    candidate_skills = [
        "Java",
        "Spring Boot",
    ]

    required_skills = [
        "Python",
        "Django",
    ]

    result = calculate_technology_relevance(
        candidate_skills,
        required_skills,
    )

    assert result == 0.0


# ============================================================
# Test 21: Full experience score
# ============================================================

def test_full_experience_score():

    candidate_profile = {
        "experience": [
            {
                "title": "Python Developer",

                "total_experience": {
                    "total_years": 2.5,
                },

                "skills": [
                    "Python",
                    "Django",
                    "Django REST Framework",
                    "REST API",
                    "PostgreSQL",
                    "Git",
                ],
            }
        ]
    }

    jd_profile = {
        "job_title": "Python Developer",

        "experience": [
            "2 - 4 Years",
            "Minimum 2 years of Python development experience.",
            "Experience with Django framework is mandatory.",
            "Experience with REST API development is required.",
        ],

        "required_skills": [
            "Python",
            "Django",
            "Django REST Framework",
            "REST API",
            "PostgreSQL",
            "Git",
        ],
    }

    # Technology score now comes from SkillScore.
    skill_result = {
        "required": {
            "match_percentage": 100.0,
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile,
        skill_result=skill_result,
    )

    assert result["score"] == 100.0

    assert result["component_scores"]["years"] == 100.0
    assert result["component_scores"]["role"] == 100.0
    assert result["component_scores"]["technology"] == 100.0

    assert result["candidate_years"] == 2.5
    assert result["required_minimum_years"] == 2.0
    assert result["required_maximum_years"] == 4.0

    assert result["candidate_roles"] == [
        "Python Developer"
    ]

    assert result["target_role"] == "Python Developer"

    assert result["experience_skills"] == [
        "Python",
        "Django",
        "Django REST Framework",
        "REST API",
        "PostgreSQL",
        "Git",
    ]

    assert result["required_skills"] == [
        "Python",
        "Django",
        "Django REST Framework",
        "REST API",
        "PostgreSQL",
        "Git",
    ]

    assert result["technology_score_source"] == "skill_score"


# ============================================================
# Test 22: Partial experience score
# ============================================================

def test_partial_experience_score():

    candidate_profile = {
        "experience": [
            {
                "title": "Python Developer",

                "total_experience": {
                    "total_years": 1.0,
                },

                "skills": [
                    "Python",
                    "Django",
                ],
            }
        ]
    }

    jd_profile = {
        "job_title": "Python Developer",

        "experience": [
            "2 - 4 Years",
        ],

        "required_skills": [
            "Python",
            "Django",
            "PostgreSQL",
            "REST API",
        ],
    }

    skill_result = {
        "required": {
            "match_percentage": 50.0,
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile,
        skill_result=skill_result,
    )

    # Years = 50
    # Role = 100
    # Technology = 50
    #
    # Final:
    #
    # 50  * 0.35 = 17.5
    # 100 * 0.25 = 25
    # 50  * 0.40 = 20
    #
    # Total = 62.5

    assert result["component_scores"]["years"] == 50.0
    assert result["component_scores"]["role"] == 100.0
    assert result["component_scores"]["technology"] == 50.0

    assert result["score"] == 62.5

    assert result["technology_score_source"] == "skill_score"


# ============================================================
# Test 23: Technology score comes from SkillScore
#
# This verifies that experience scoring does not independently
# recalculate technology relevance when skill_result is supplied.
# ============================================================

def test_technology_score_comes_from_skill_result():

    candidate_profile = {
        "experience": [
            {
                "title": "Python Developer",

                "total_experience": {
                    "total_years": 2.0,
                },

                "skills": [
                    "Python",
                ],
            }
        ]
    }

    jd_profile = {
        "job_title": "Python Developer",

        "experience": [
            "2 years",
        ],

        "required_skills": [
            "Python",
            "Django",
            "PostgreSQL",
        ],
    }

    skill_result = {
        "required": {
            "match_percentage": 25.0,
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile,
        skill_result=skill_result,
    )

    assert result["component_scores"]["technology"] == 25.0
    assert result["technology_score_source"] == "skill_score"


# ============================================================
# Test 24: Missing candidate experience
# ============================================================

def test_missing_candidate_experience():

    candidate_profile = {
        "experience": []
    }

    jd_profile = {
        "job_title": "Python Developer",

        "experience": [
            "Minimum 2 years"
        ],

        "required_skills": [
            "Python",
            "Django",
        ],
    }

    skill_result = {
        "required": {
            "match_percentage": 0.0,
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile,
        skill_result=skill_result,
    )

    assert result["candidate_years"] == 0.0
    assert result["candidate_roles"] == []
    assert result["experience_skills"] == []

    assert result["component_scores"]["years"] == 0.0
    assert result["component_scores"]["role"] == 0.0
    assert result["component_scores"]["technology"] == 0.0


# ============================================================
# Test 25: Missing JD experience requirement
# ============================================================

def test_missing_jd_experience_requirement():

    candidate_profile = {
        "experience": [
            {
                "title": "Python Developer",

                "total_experience": {
                    "total_years": 3.0,
                },

                "skills": [
                    "Python",
                    "Django",
                ],
            }
        ]
    }

    jd_profile = {
        "job_title": "Python Developer",

        "experience": [],

        "required_skills": [
            "Python",
            "Django",
        ],
    }

    skill_result = {
        "required": {
            "match_percentage": 100.0,
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile,
        skill_result=skill_result,
    )

    assert result["candidate_years"] == 3.0
    assert result["required_minimum_years"] == 0.0

    assert result["component_scores"]["years"] == 100.0
    assert result["component_scores"]["role"] == 100.0
    assert result["component_scores"]["technology"] == 100.0

    assert result["score"] == 100.0


# ============================================================
# Test 26: Empty profiles
# ============================================================

def test_empty_profiles():

    candidate_profile = {}
    jd_profile = {}

    result = calculate_experience_score(
        candidate_profile,
        jd_profile,
        skill_result={
            "required": {
                "match_percentage": 0.0,
            }
        },
    )

    assert result["candidate_years"] == 0.0
    assert result["candidate_roles"] == []
    assert result["experience_skills"] == []

    assert result["required_minimum_years"] == 0.0

    assert result["component_scores"]["years"] == 100.0
    assert result["component_scores"]["role"] == 0.0
    assert result["component_scores"]["technology"] == 0.0

    # 100 * 0.35
    # + 0 * 0.25
    # + 0 * 0.40
    # = 35
    assert result["score"] == 35.0


# ============================================================
# Test 27: Skill result is optional
#
# Backward compatibility:
# If skill_result is not supplied, experience scorer falls
# back to calculate_technology_relevance().
# ============================================================

def test_experience_score_without_skill_result():

    candidate_profile = {
        "experience": [
            {
                "title": "Python Developer",

                "total_experience": {
                    "total_years": 2.0,
                },

                "skills": [
                    "Python",
                    "Django",
                ],
            }
        ]
    }

    jd_profile = {
        "job_title": "Python Developer",

        "experience": [
            "2 years",
        ],

        "required_skills": [
            "Python",
            "Django",
        ],
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile,
    )

    assert result["component_scores"]["years"] == 100.0
    assert result["component_scores"]["role"] == 100.0
    assert result["component_scores"]["technology"] == 100.0

    assert result["technology_score_source"] == "legacy_technology_scorer"

    assert result["score"] == 100.0


# ============================================================
# Test 28: Experience score weights
# ============================================================

def test_experience_score_weights():

    candidate_profile = {
        "experience": [
            {
                "title": "Python Developer",

                "total_experience": {
                    "total_years": 2.0,
                },

                "skills": [
                    "Python",
                ],
            }
        ]
    }

    jd_profile = {
        "job_title": "Python Developer",

        "experience": [
            "2 years",
        ],

        "required_skills": [
            "Python",
            "Django",
        ],
    }

    skill_result = {
        "required": {
            "match_percentage": 50.0,
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile,
        skill_result=skill_result,
    )

    assert result["weights"] == {
        "years": 0.35,
        "role": 0.25,
        "technology": 0.40,
    }


# ============================================================
# Test 29: Candidate years from total_months
# ============================================================

def _candidate_years(candidate_profile: Any) -> float:
    """
    Extract total candidate experience in years.

    Supported structures:

    1. Top-level:
        {
            "total_experience": {
                "total_years": 2.5
            }
        }

    2. Nested inside experience:
        {
            "experience": [
                {
                    "total_experience": {
                        "total_years": 2.5
                    }
                }
            ]
        }

    3. Nested total_months:
        {
            "total_experience": {
                "total_months": 30
            }
        }

    4. Nested inside experience record:
        {
            "experience": [
                {
                    "total_experience": {
                        "total_months": 30
                    }
                }
            ]
        }

    Priority:
        total_months > total_years

    Returns:
        float: candidate experience in years
    """

    if not isinstance(candidate_profile, dict):
        return 0.0

    # ========================================================
    # 1. Top-level total_experience
    # ========================================================

    total_experience = candidate_profile.get(
        "total_experience"
    )

    if isinstance(total_experience, dict):

        total_months = total_experience.get(
            "total_months"
        )

        if total_months is not None:
            try:
                return round(float(total_months) / 12.0, 2)
            except (TypeError, ValueError):
                pass

        total_years = total_experience.get(
            "total_years"
        )

        if total_years is not None:
            try:
                return round(float(total_years), 2)
            except (TypeError, ValueError):
                pass

    # ========================================================
    # 2. Experience records
    # ========================================================

    experience = candidate_profile.get(
        "experience",
        []
    )

    if not isinstance(experience, list):
        return 0.0

    best_years = 0.0

    for record in experience:

        if not isinstance(record, dict):
            continue

        record_total = record.get(
            "total_experience"
        )

        if not isinstance(record_total, dict):
            continue

        # ----------------------------------------------------
        # Prefer total_months
        # ----------------------------------------------------

        total_months = record_total.get(
            "total_months"
        )

        if total_months is not None:

            try:
                years = float(total_months) / 12.0

                if years > best_years:
                    best_years = years

                continue

            except (TypeError, ValueError):
                pass

        # ----------------------------------------------------
        # Fallback to total_years
        # ----------------------------------------------------

        total_years = record_total.get(
            "total_years"
        )

        if total_years is not None:

            try:
                years = float(total_years)

                if years > best_years:
                    best_years = years

            except (TypeError, ValueError):
                pass

    return round(best_years, 2)


# ============================================================
# Test 30: Maximum experience is informational
# ============================================================

def test_maximum_experience_does_not_penalize_candidate():

    candidate_profile = {
        "experience": [
            {
                "title": "Python Developer",

                "total_experience": {
                    "total_years": 7.0,
                },

                "skills": [
                    "Python",
                ],
            }
        ]
    }

    jd_profile = {
        "job_title": "Python Developer",

        "experience": [
            "2 - 4 years",
        ],

        "required_skills": [
            "Python",
        ],
    }

    skill_result = {
        "required": {
            "match_percentage": 100.0,
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile,
        skill_result=skill_result,
    )

    assert result["candidate_years"] == 7.0
    assert result["required_minimum_years"] == 2.0
    assert result["required_maximum_years"] == 4.0

    # Current design is minimum-based.
    # Exceeding the maximum does not reduce the score.
    assert result["component_scores"]["years"] == 100.0