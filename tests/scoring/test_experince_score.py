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

def test_extract_required_years_range():

    experience = [
        "2 - 4 Years",
        "Minimum 2 years of Python development experience."
    ]

    result = extract_required_years(
        experience
    )

    assert result["minimum_years"] == 2.0
    assert result["maximum_years"] == 4.0


# ============================================================
# Test 2: Extract minimum experience
# ============================================================

def test_extract_minimum_years():

    experience = [
        "Minimum 3 years of Python development experience."
    ]

    result = extract_required_years(
        experience
    )

    assert result["minimum_years"] == 3.0
    assert result["maximum_years"] == 0.0


# ============================================================
# Test 3: Candidate meets minimum experience
# ============================================================

def test_candidate_meets_required_years():

    result = calculate_year_score(
        candidate_years=3.0,
        required_years=2.0
    )

    assert result == 100.0


# ============================================================
# Test 4: Candidate exceeds minimum experience
# ============================================================

def test_candidate_exceeds_required_years():

    result = calculate_year_score(
        candidate_years=5.0,
        required_years=2.0
    )

    assert result == 100.0


# ============================================================
# Test 5: Candidate has insufficient experience
# ============================================================

def test_candidate_has_insufficient_experience():

    result = calculate_year_score(
        candidate_years=1.0,
        required_years=2.0
    )

    assert result == 50.0


# ============================================================
# Test 6: No experience requirement
# ============================================================

def test_no_experience_requirement():

    result = calculate_year_score(
        candidate_years=2.0,
        required_years=0.0
    )

    assert result == 100.0


# ============================================================
# Test 7: Exact job-title match
# ============================================================

def test_exact_role_match():

    result = calculate_role_relevance(
        candidate_roles=[
            "Python Developer"
        ],
        target_job_title="Python Developer"
    )

    assert result == 100.0


# ============================================================
# Test 8: Partial job-title match
# ============================================================

def test_partial_role_match():

    result = calculate_role_relevance(
        candidate_roles=[
            "Senior Python Developer"
        ],
        target_job_title="Python Developer"
    )

    assert result == 100.0


# ============================================================
# Test 9: No job-title match
# ============================================================

def test_no_role_match():

    result = calculate_role_relevance(
        candidate_roles=[
            "Java Developer"
        ],
        target_job_title="Python Developer"
    )

    assert result == 50.0


# ============================================================
# Test 10: Required technology matching
# ============================================================

def test_technology_relevance():

    candidate_skills = [
        "Python",
        "Django",
        "PostgreSQL",
        "REST API"
    ]

    required_skills = [
        "Python",
        "Django",
        "PostgreSQL",
        "REST API"
    ]

    result = calculate_technology_relevance(
        candidate_skills,
        required_skills
    )

    assert result == 100.0


# ============================================================
# Test 11: Partial technology matching
# ============================================================

def test_partial_technology_relevance():

    candidate_skills = [
        "Python",
        "Django"
    ]

    required_skills = [
        "Python",
        "Django",
        "PostgreSQL",
        "REST API"
    ]

    result = calculate_technology_relevance(
        candidate_skills,
        required_skills
    )

    assert result == 50.0


# ============================================================
# Test 12: No technology match
# ============================================================

def test_no_technology_match():

    candidate_skills = [
        "Java",
        "Spring Boot"
    ]

    required_skills = [
        "Python",
        "Django"
    ]

    result = calculate_technology_relevance(
        candidate_skills,
        required_skills
    )

    assert result == 0.0


# ============================================================
# Test 13: Full experience score
# ============================================================

def test_full_experience_score():

    candidate_profile = {
        "resume_text": {
            "experience": [
                {
                    "title": "Python Developer",
                    "total_experience": {
                        "total_years": 2.5
                    },
                    "skills": [
                        "Python",
                        "Django",
                        "Django REST Framework",
                        "REST API",
                        "PostgreSQL",
                        "Git"
                    ]
                }
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "job_title": "Python Developer",

            "experience": [
                "2 - 4 Years",
                "Minimum 2 years of Python development experience.",
                "Experience with Django framework is mandatory.",
                "Experience with REST API development is required."
            ],

            "required_skills": [
                "Python",
                "Django",
                "Django REST Framework",
                "REST API",
                "PostgreSQL",
                "Git"
            ]
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 100.0

    assert result["years_score"] == 100.0
    assert result["role_relevance_score"] == 100.0
    assert result["technology_relevance_score"] == 100.0

    assert result["candidate_years"] == 2.5
    assert result["required_minimum_years"] == 2.0

    assert result["candidate_roles"] == [
        "Python Developer"
    ]

    assert result["status"] == "calculated"


# ============================================================
# Test 14: Partial experience score
# ============================================================

def test_partial_experience_score():

    candidate_profile = {
        "resume_text": {
            "experience": [
                {
                    "title": "Python Developer",
                    "total_experience": {
                        "total_years": 1.0
                    },
                    "skills": [
                        "Python",
                        "Django"
                    ]
                }
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "job_title": "Python Developer",

            "experience": [
                "2 - 4 Years"
            ],

            "required_skills": [
                "Python",
                "Django",
                "PostgreSQL",
                "REST API"
            ]
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile
    )

    # Years = 50
    # Role = 100
    # Technology = 50
    #
    # Final:
    # 50 * 0.35
    # + 100 * 0.25
    # + 50 * 0.40
    #
    # = 62.5

    assert result["years_score"] == 50.0
    assert result["role_relevance_score"] == 100.0
    assert result["technology_relevance_score"] == 50.0
    assert result["score"] == 62.5


# ============================================================
# Test 15: Missing candidate experience
# ============================================================

def test_missing_candidate_experience():

    candidate_profile = {
        "resume_text": {
            "experience": []
        }
    }

    jd_profile = {
        "resume_text": {
            "job_title": "Python Developer",

            "experience": [
                "Minimum 2 years"
            ],

            "required_skills": [
                "Python",
                "Django"
            ]
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile
    )

    assert result["candidate_years"] == 0.0
    assert result["candidate_roles"] == []
    assert result["experience_skills"] == []

    assert result["years_score"] == 0.0
    assert result["role_relevance_score"] == 0.0
    assert result["technology_relevance_score"] == 0.0

    assert result["status"] == "no_data"


# ============================================================
# Test 16: Missing JD experience requirement
# ============================================================

def test_missing_jd_experience_requirement():

    candidate_profile = {
        "resume_text": {
            "experience": [
                {
                    "title": "Python Developer",
                    "total_experience": {
                        "total_years": 3.0
                    },
                    "skills": [
                        "Python",
                        "Django"
                    ]
                }
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "job_title": "Python Developer",
            "experience": [],
            "required_skills": [
                "Python",
                "Django"
            ]
        }
    }

    result = calculate_experience_score(
        candidate_profile,
        jd_profile
    )

    assert result["candidate_years"] == 3.0
    assert result["required_minimum_years"] == 0.0

    assert result["years_score"] == 100.0
    assert result["role_relevance_score"] == 100.0
    assert result["technology_relevance_score"] == 100.0

    assert result["score"] == 100.0
    assert result["status"] == "no_requirement"


# ============================================================
# Test 17: Empty profiles
# ============================================================

def test_empty_profiles():

    candidate_profile = {}
    jd_profile = {}

    result = calculate_experience_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 100.0
    assert result["candidate_years"] == 0.0
    assert result["candidate_roles"] == []
    assert result["experience_skills"] == []
    assert result["status"] == "no_data"