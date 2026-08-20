from scoring.bias_mitigation.personal_attribute_masker import (
    mask_personal_attributes,
)


def test_original_profile_is_not_modified_for_direct_attributes():

    candidate = {
        "first_name": "John",
        "email": "john@example.com",
        "skill": [
            {
                "skill_name": "Python"
            }
        ],
    }

    masked = mask_personal_attributes(candidate)

    assert "first_name" in candidate
    assert "email" in candidate

    assert "first_name" not in masked
    assert "email" not in masked


def test_job_relevant_attributes_are_preserved():

    candidate = {
        "first_name": "John",
        "email": "john@example.com",

        "skill": [
            {
                "skill_name": "Python",
            }
        ],

        "experience": [
            {
                "company_name": "ABC Technologies",
                "technologies": [
                    "Python",
                    "Django",
                ],
            }
        ],

        "education": [
            {
                "degree": "B.Tech",
                "specialization": "Computer Science",
            }
        ],

        "certification": [
            {
                "certification_name": "AWS Certified Developer",
            }
        ],

        "projects": [
            {
                "project_name": "Recruitment System",
            }
        ],
    }

    masked = mask_personal_attributes(
        candidate
    )

    assert masked["skill"] == candidate["skill"]
    assert masked["experience"] == candidate["experience"]
    assert masked["education"] == candidate["education"]
    assert masked["certification"] == candidate["certification"]
    assert masked["projects"] == candidate["projects"]


def test_original_profile_is_not_modified():

    candidate = {
        "first_name": "John",
        "email": "john@example.com",
        "skill": [
            {
                "skill_name": "Python"
            }
        ],
    }

    masked = mask_personal_attributes(
        candidate
    )

    assert "first_name" in candidate
    assert "email" in candidate

    assert "first_name" not in masked
    assert "email" not in masked
    

def test_nested_resume_profile():

    candidate = {
        "resume_text": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "1234567890",

            "skills": [
                "Python",
                "Django",
            ],

            "experience": [
                {
                    "title": "Python Developer"
                }
            ],
        }
    }

    masked = mask_personal_attributes(
        candidate
    )

    resume = masked["resume_text"]

    assert "first_name" not in resume
    assert "last_name" not in resume
    assert "email" not in resume
    assert "phone" not in resume

    assert resume["skills"] == [
        "Python",
        "Django",
    ]
    
def test_personal_information_is_removed():

    profile = {
        "candidate_id": "CAN_001",
        "personal_information": {
            "name": "Rahul",
            "email": "rahul@example.com",
            "phone": "9999999999",
            "linkedin": "linkedin.com/rahul",
        },
        "skills": [
            {
                "skill": "Python"
            }
        ]
    }

    masked = mask_personal_attributes(profile)

    assert "personal_information" not in masked

    assert masked["candidate_id"] == "CAN_001"

    assert "skills" in masked
    

def test_original_profile_is_not_modified():

    profile = {
        "personal_information": {
            "name": "Rahul"
        }
    }

    masked = mask_personal_attributes(profile)

    assert "personal_information" in profile
    assert "personal_information" not in masked