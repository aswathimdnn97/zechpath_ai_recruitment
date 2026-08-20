"""
candidate_profile_builder.py

Responsibilities:
1. Merge all resume entities.
2. Create standard candidate profile.
3. Return ATS-ready JSON.
"""

from datetime import datetime, timezone

from .profile_schema import create_empty_profile
import uuid


def build_candidate_profile(
    personal_information=None,
    education=None,
    experience=None,
    skills=None,
    projects=None,
    certifications=None,
    candidate_id=None,
):

    profile = create_empty_profile()

    # --------------------------------
    # Candidate ID
    # --------------------------------

    if candidate_id:
        profile["candidate_id"] = candidate_id
    else:
        profile["candidate_id"] = generate_candidate_id()

    # --------------------------------
    # Personal Information
    # --------------------------------

    if personal_information:
        profile["personal_information"] = personal_information

    # --------------------------------
    # Skills
    # --------------------------------

    if skills:
        profile["skills"] = skills

    # --------------------------------
    # Education
    # --------------------------------

    if education:
        profile["education"] = education

    # --------------------------------
    # Experience
    # --------------------------------

    if experience:
        profile["experience"] = experience

    # --------------------------------
    # Projects
    # --------------------------------

    if projects:
        profile["projects"] = projects

    # --------------------------------
    # Certifications
    # --------------------------------

    if certifications:
        profile["certifications"] = certifications

    # --------------------------------
    # Metadata
    # --------------------------------

    profile["metadata"]["created_at"] = (
        datetime.now(timezone.utc).isoformat()
    )

    return profile


def generate_candidate_id():
    return f"CAN_{uuid.uuid4().hex[:12].upper()}"