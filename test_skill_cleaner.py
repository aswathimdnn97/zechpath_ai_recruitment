#!/usr/bin/env python3
"""Test script for the skill cleaner"""

from document_processing.common.skill_cleaner import clean_skills

# Test cases
test_cases = {
    "preferred_skills": [
        "Docker",
        "AWS",
        "Redis",
        "Celery",
        "Kubernetes",
        "Experience with CI/CD pipelines",
        "Knowledge of Microservices",
        "Linux administration",
        "Unit Testing using PyTest"
    ],
    "required_skills": [
        "Python",
        "Django",
        "Django REST Framework",
        "REST API",
        "PostgreSQL",
        "Git",
        "Object-Oriented Programming",
        "SQL"
    ],
    "complex_phrases": [
        "Proficiency in Docker and Kubernetes",
        "Experience with AWS cloud services",
        "Knowledge of microservices architecture",
        "Hands-on experience with CI/CD pipelines",
        "Good understanding of Linux administration",
        "Familiar with Unit Testing using PyTest"
    ]
}

print("=" * 60)
print("SKILL CLEANER TEST RESULTS")
print("=" * 60)

for category, skills in test_cases.items():
    print(f"\n{category.upper()}:")
    print("-" * 60)
    print("BEFORE:")
    for i, skill in enumerate(skills, 1):
        print(f"  {i}. {skill}")
    
    cleaned = clean_skills(skills)
    print("\nAFTER:")
    for i, skill in enumerate(cleaned, 1):
        print(f"  {i}. {skill}")
    
    print()

print("=" * 60)
print("Test complete!")
