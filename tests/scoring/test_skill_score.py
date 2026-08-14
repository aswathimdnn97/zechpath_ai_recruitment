from scoring.skill_score import calculate_skill_score


# ============================================================
# Test 1: All required skills matched
# ============================================================

def test_all_required_skills_matched():

    candidate_profile = {
        "resume_text": {
            "skills": [
                {"skill": "Python"},
                {"skill": "Django"},
                {"skill": "PostgreSQL"},
                {"skill": "Git"},
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "required_skills": [
                "Python",
                "Django",
                "PostgreSQL",
                "Git",
            ],
            "preferred_skills": []
        }
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 100.0
    assert result["required_score"] == 100.0
    assert result["required_matched"] == 4
    assert result["missing_required_skills"] == []

    # Matching output is normalized
    assert set(
        result["matched_required_skills"]
    ) == {
        "python",
        "django",
        "postgresql",
        "git"
    }


# ============================================================
# Test 2: Some required skills are missing
# ============================================================

def test_some_required_skills_missing():

    candidate_profile = {
        "resume_text": {
            "skills": [
                {"skill": "Python"},
                {"skill": "Django"},
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "required_skills": [
                "Python",
                "Django",
                "PostgreSQL",
                "Git",
            ],
            "preferred_skills": []
        }
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    assert result["required_score"] == 50.0
    assert result["required_matched"] == 2

    assert set(
        result["missing_required_skills"]
    ) == {
        "postgresql",
        "git"
    }


# ============================================================
# Test 3: Preferred skills affect final score
# ============================================================

def test_preferred_skills():

    candidate_profile = {
        "resume_text": {
            "skills": [
                {"skill": "Python"},
                {"skill": "Django"},
                {"skill": "Docker"},
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "required_skills": [
                "Python",
                "Django",
            ],
            "preferred_skills": [
                "Docker",
                "AWS",
                "Redis",
                "Kubernetes",
            ]
        }
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    # Required = 100
    # Preferred = 25
    #
    # Final:
    # 100 * 0.80 + 25 * 0.20
    # = 85

    assert result["required_score"] == 100.0
    assert result["preferred_score"] == 25.0
    assert result["score"] == 85.0

    assert result["matched_preferred_skills"] == [
        "docker"
    ]


# ============================================================
# Test 4: Case-insensitive matching
# ============================================================

def test_skill_matching_is_case_insensitive():

    candidate_profile = {
        "resume_text": {
            "skills": [
                {"skill": "PYTHON"},
                {"skill": "Django"},
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "required_skills": [
                "python",
                "django",
            ]
        }
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 100.0
    assert result["required_matched"] == 2

    assert set(
        result["matched_required_skills"]
    ) == {
        "python",
        "django"
    }


# ============================================================
# Test 5: Duplicate candidate skills
# ============================================================

def test_duplicate_candidate_skills():

    candidate_profile = {
        "resume_text": {
            "skills": [
                {"skill": "Python"},
                {"skill": "python"},
                {"skill": " Python "},
                {"skill": "Django"},
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "required_skills": [
                "Python",
                "Django",
            ]
        }
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 100.0
    assert result["required_matched"] == 2

    # Python duplicates should be removed
    assert result["candidate_skill_count"] == 2


# ============================================================
# Test 6: No candidate skills
# ============================================================

def test_no_candidate_skills():

    candidate_profile = {
        "resume_text": {
            "skills": []
        }
    }

    jd_profile = {
        "resume_text": {
            "required_skills": [
                "Python",
                "Django",
            ],
            "preferred_skills": [
                "Docker"
            ]
        }
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 0.0
    assert result["required_score"] == 0.0
    assert result["preferred_score"] == 0.0
    assert result["required_matched"] == 0
    assert result["status"] == "no_data"


# ============================================================
# Test 7: No JD skill requirements
# ============================================================

def test_no_jd_skill_requirements():

    candidate_profile = {
        "resume_text": {
            "skills": [
                {"skill": "Python"},
                {"skill": "Django"},
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "required_skills": [],
            "preferred_skills": []
        }
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 0.0
    assert result["status"] == "no_requirements"


# ============================================================
# Test 8: Candidate skills as strings
# ============================================================

def test_candidate_skills_as_strings():

    candidate_profile = {
        "resume_text": {
            "skills": [
                "Python",
                "Django",
                "PostgreSQL"
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "required_skills": [
                "Python",
                "Django",
                "PostgreSQL"
            ]
        }
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 100.0


# ============================================================
# Test 9: Missing required skills are correctly reported
# ============================================================

def test_missing_required_skills():

    candidate_profile = {
        "resume_text": {
            "skills": [
                {"skill": "Python"}
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "required_skills": [
                "Python",
                "Django",
                "PostgreSQL"
            ]
        }
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    assert result["missing_required_skills"] == [
        "django",
        "postgresql"
    ]


# ============================================================
# Test 10: Empty profiles
# ============================================================

def test_empty_profiles():

    candidate_profile = {}

    jd_profile = {}

    result = calculate_skill_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 0.0
    assert result["status"] == "no_data"