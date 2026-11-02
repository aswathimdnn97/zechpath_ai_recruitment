import pytest

from api.service.experience_intent_service import (
    extract_experience_intent,
)


def test_extract_numeric_experience():

    result = extract_experience_intent(
        "I have 2 years of experience."
    )

    assert result["total_experience_years"] == 2.0
    assert result["experience_level"] == "EXPERIENCED"


def test_extract_word_duration():

    result = extract_experience_intent(
        "I have two years of experience."
    )

    assert result["total_experience_years"] == 2.0


def test_extract_years_and_months():

    result = extract_experience_intent(
        "I have one year and six months of experience."
    )

    assert result["total_experience_years"] == 1.5


def test_extract_relevant_experience():

    result = extract_experience_intent(
        "I have two years of relevant experience."
    )

    assert result["relevant_experience_years"] == 2.0


def test_extract_employment_status():

    result = extract_experience_intent(
        "I have three years of experience. "
        "Currently working."
    )

    assert result["employment_status"] == "CURRENTLY_WORKING"


def test_detect_fresher():

    result = extract_experience_intent(
        "I am a fresher with no professional experience."
    )

    assert result["experience_level"] == "FRESHER"
    assert result["total_experience_years"] == 0.0


def test_detect_vague_experience():

    result = extract_experience_intent(
        "I have some experience in software development."
    )

    assert "experience_duration" in result["vague_fields"]


def test_detect_missing_answer():

    result = extract_experience_intent("")

    assert result["status"] == "MISSING"
    assert result["experience_level"] == "UNKNOWN"


def test_extract_role():

    result = extract_experience_intent(
        "I worked as a Python Developer for two years."
    )

    assert len(result["job_roles"]) >= 1

    assert (
        result["job_roles"][0]["title"]
        == "Python Developer"
    )