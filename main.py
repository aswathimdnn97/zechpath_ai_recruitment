from utils.logger import logger
from document_processing.resume.resume_pipeline import resume_pipeline
from document_processing.job_description.job_description_pipeline import job_description_pipeline
from pipelines.recruiter_pipeline import recruitment_pipeline
from matching.matcher import Matcher
from scoring.ats_scoring_engine import calculate_ats_score
from embeddings.embedding_generator import EmbeddingGenerator
logger.info("Resume Uploaded")

# ============================================================
# 1. Resume Parsing
# ============================================================

resume_file = "data/resume/pdf/python_django.pdf"

resume_json = resume_pipeline(
    resume_file
)

print("\n================ RESUME JSON ================")
print(resume_json)


# ============================================================
# 2. Job Description Parsing
# ============================================================

job_description_file = (
    "data/job_descriptions/jd_python_developer.pdf"
)

jd_json = job_description_pipeline(
    job_description_file
)

print("\n================ JD JSON ================")
print(jd_json)


# ============================================================
# 3. Existing Matching
# ============================================================

matcher = Matcher()

matching_result = matcher.match(
    resume_json,
    jd_json
)

print("\n================ MATCHING RESULT ================")
print(matching_result)

embedding_generator=EmbeddingGenerator()
resume_embedding = embedding_generator.generate_embedding(resume_json)
jd_embedding = embedding_generator.generate_embedding(jd_json)

# ============================================================
# 4. ATS Scoring Engine
# ============================================================

ats_result = calculate_ats_score(
    candidate_profile=resume_json,
    jd_profile=jd_json,
    resume_embedding=resume_embedding,
    jd_embedding=jd_embedding
)


# ============================================================
# 5. ATS Result
# ============================================================

print("\n================ ATS SCORE ================")

print(
    "Final ATS Score:",
    ats_result["candidate_score"]["final_score"]
)

print("\nComponent Scores:")

print(
    "Skill:",
    ats_result["component_scores"]["skill"]["score"]
)

print(
    "Experience:",
    ats_result["component_scores"]["experience"]["score"]
)

print(
    "Education:",
    ats_result["component_scores"]["education"]["score"]
)

print(
    "Semantic:",
    ats_result["component_scores"]["semantic"]["score"]
)

print("\n================ ATS RESULT ================")

print(ats_result)

