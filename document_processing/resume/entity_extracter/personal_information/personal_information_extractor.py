"""
personal_information_extractor.py

Responsibilities
----------------
1. Extract candidate name
2. Extract email
3. Extract phone
4. Extract location
5. Extract LinkedIn
6. Extract GitHub
7. Extract portfolio
"""

from document_processing.resume.entity_extracter.personal_information.name_extractor import extract_name
from document_processing.resume.entity_extracter.personal_information.email_extractor import extract_email
from document_processing.resume.entity_extracter.personal_information.phone_extractor import extract_phone
from document_processing.resume.entity_extracter.personal_information.location_extractor import extract_location
from document_processing.resume.entity_extracter.personal_information.linkedin_extractor import extract_linkedin
from document_processing.resume.entity_extracter.personal_information.github_extractor import extract_github
from document_processing.resume.entity_extracter.personal_information.portfolio_extractor import extract_portfolio


def extract_personal_information(text):

    return {

        "name": extract_name(text),

        "email": extract_email(text),

        "phone": extract_phone(text),

        "location": extract_location(text),

        "linkedin": extract_linkedin(text),

        "github": extract_github(text),

        "portfolio": extract_portfolio(text)

    }