import pytest

from scoring.bias_mitigation.bias_indicator_detector import (
    detect_bias_indicators,
)


# ============================================================
# Age Detection
# ============================================================

def test_detect_age_indicator():

    resume = {
        "first_name": "John",
        "date_of_birth": "12-05-1998",
        "skill": [ "Python","Django"],
    }

    result = detect_bias_indicators(resume)

    print("AGE RESULT:", result)

    assert result["bias_detected"] is True
    assert result["risk_level"] == "high"
    assert result["status"] == "detected"

    indicators = [
        item["indicator"]
        for item in result["indicators"]
    ]

    assert "age" in indicators


# ============================================================
# Gender Detection
# ============================================================

def test_detect_gender_indicator():

    resume = {
        "first_name": "John",
        "gender": "Male",
        "skill": [
            "Python",
            "Django",
        ],
    }

    result = detect_bias_indicators(resume)

    print("GENDER RESULT:", result)

    assert result["bias_detected"] is True
    assert result["risk_level"] == "high"

    indicators = [
        item["indicator"]
        for item in result["indicators"]
    ]

    assert "gender" in indicators


# ============================================================
# Religion Detection
# ============================================================

def test_detect_religion_indicator():

    resume = {
        "first_name": "John",
        "religion": "Christian",
        "skill": [
            "Python",
            "Django",
        ],
    }

    result = detect_bias_indicators(resume)

    print("RELIGION RESULT:", result)

    assert result["bias_detected"] is True
    assert result["risk_level"] == "high"

    indicators = [
        item["indicator"]
        for item in result["indicators"]
    ]

    assert "religion" in indicators


# ============================================================
# Marital Status Detection
# ============================================================

def test_detect_marital_status():

    resume = {
        "first_name": "John",
        "marital_status": "Married",
        "skill": [
            "Python",
        ],
    }

    result = detect_bias_indicators(resume)

    print("MARITAL RESULT:", result)

    assert result["bias_detected"] is True
    assert result["risk_level"] == "high"

    indicators = [
        item["indicator"]
        for item in result["indicators"]
    ]

    assert "marital_status" in indicators


# ============================================================
# Nationality Detection
# ============================================================

def test_detect_nationality():

    resume = {
        "first_name": "John",
        "nationality": "Indian",
        "skill": [
            "Python",
        ],
    }

    result = detect_bias_indicators(resume)

    print("NATIONALITY RESULT:", result)

    assert result["bias_detected"] is True
    assert result["risk_level"] == "high"

    indicators = [
        item["indicator"]
        for item in result["indicators"]
    ]

    assert "nationality" in indicators


# ============================================================
# Photograph Detection
# ============================================================

def test_detect_photograph():

    resume = {
        "first_name": "John",
        "photograph": "profile_photo.jpg",
        "skill": [
            "Python",
        ],
    }

    result = detect_bias_indicators(resume)

    print("PHOTO RESULT:", result)

    assert result["bias_detected"] is True

    indicators = [
        item["indicator"]
        for item in result["indicators"]
    ]

    assert "photograph" in indicators


# ============================================================
# Full Address Detection
# ============================================================

def test_detect_full_address():

    resume = {
        "first_name": "John",
        "full_address": (
            "123 Main Street, Kochi, Kerala"
        ),
        "skill": [
            "Python",
        ],
    }

    result = detect_bias_indicators(resume)

    print("ADDRESS RESULT:", result)

    assert result["bias_detected"] is True

    indicators = [
        item["indicator"]
        for item in result["indicators"]
    ]

    assert "full_address" in indicators


# ============================================================
# Multiple Bias Indicators
# ============================================================

def test_detect_multiple_bias_indicators():

    resume = {
        "first_name": "John",
        "date_of_birth": "12-05-1998",
        "gender": "Male",
        "religion": "Christian",
        "marital_status": "Married",
        "nationality": "Indian",
        "skill": [
            "Python",
            "Django",
        ],
    }

    result = detect_bias_indicators(resume)

    print("MULTIPLE INDICATORS:", result)

    assert result["bias_detected"] is True
    assert result["risk_level"] == "high"
    assert result["status"] == "detected"

    assert result["indicator_count"] >= 5

    indicators = {
        item["indicator"]
        for item in result["indicators"]
    }

    assert "age" in indicators
    assert "gender" in indicators
    assert "religion" in indicators
    assert "marital_status" in indicators
    assert "nationality" in indicators


# ============================================================
# Clean Resume
# ============================================================

def test_clean_resume_has_no_bias_indicators():

    resume = {
        "candidate_id": "CAN_001",

        "skill": [
            "Python",
            "Django",
            "PostgreSQL",
        ],

        "experience": [
            {
                "company_name": "ABC Technologies",
                "employment_type": "Full-time",
                "start_date": "2021",
                "end_date": "2024",
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
            }
        ],
    }

    result = detect_bias_indicators(resume)

    print("CLEAN RESULT:", result)

    assert result["bias_detected"] is False
    assert result["risk_level"] == "none"
    assert result["indicator_count"] == 0
    assert result["indicators"] == []
    assert result["status"] == "clear"


# ============================================================
# Empty Profile
# ============================================================

def test_empty_profile():

    result = detect_bias_indicators({})

    print("EMPTY RESULT:", result)

    assert result["bias_detected"] is False
    assert result["risk_level"] == "none"
    assert result["indicator_count"] == 0
    assert result["indicators"] == []
    assert result["status"] == "no_data"


# ============================================================
# Invalid Input
# ============================================================

@pytest.mark.parametrize(
    "profile",
    [
        None,
        [],
        123,
        "",
    ],
)
def test_invalid_or_empty_input(profile):

    result = detect_bias_indicators(profile)

    print(
        "INVALID INPUT:",
        profile,
        result,
    )

    assert result["bias_detected"] is False
    assert result["risk_level"] == "none"
    assert result["indicator_count"] == 0


# ============================================================
# Candidate ID Should Not Be a Bias Indicator
# ============================================================

def test_candidate_id_is_not_bias_indicator():

    resume = {
        "candidate_id": "CAN_001",
        "skill": [
            "Python",
            "Django",
        ],
    }

    result = detect_bias_indicators(resume)

    print(
        "CANDIDATE ID RESULT:",
        result,
    )

    assert result["bias_detected"] is False
    assert result["indicator_count"] == 0
    assert result["status"] == "clear"