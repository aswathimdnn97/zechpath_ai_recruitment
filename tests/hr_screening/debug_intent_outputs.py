
from pprint import pprint

from api.service.intent_classification_service import (
    extract_skills,
    extract_experience_intent,
    extract_availability_intent,
    extract_salary_expectation_intent,
    assess_answer_quality,
    detect_off_topic_response,
)

print("\n--- SKILLS ---")
pprint(extract_skills(
    "I have worked with Python, Django, FastAPI and SQL."
))

print("\n--- EXPERIENCE ---")
pprint(extract_experience_intent(
    "I have 3 years of experience as a Python developer."
))

print("\n--- AVAILABILITY ---")
pprint(extract_availability_intent(
    "I can join immediately."
))

print("\n--- NOTICE PERIOD ---")
pprint(extract_availability_intent(
    "My notice period is 30 days."
))

print("\n--- SALARY ---")
pprint(extract_salary_expectation_intent(
    "My expected salary is 5-7 LPA."
))

print("\n--- MISSING ANSWER ---")
pprint(assess_answer_quality(
    question_text="SKILLS",
    answer_text="",
))

print("\n--- OFF-TOPIC ---")
pprint(detect_off_topic_response(
    question_text="SKILLS",
    answer_text="I like watching movies.",
))
