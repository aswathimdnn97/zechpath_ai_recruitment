from utils.logger import logger
from document_processing.resume.resume_pipeline import resume_pipeline
from document_processing.job_description.job_description_pipeline import job_description_pipeline
from pipelines.recruiter_pipeline import recruitment_pipeline
from matching.matcher import Matcher
logger.info("Resume Uploaded")

"""Resume parsing"""
resume_file="data/resume/pdf/python_django.pdf"
resume_json=resume_pipeline(resume_file)


"""JD Parsing"""
job_description_file="data/job_descriptions/jd_python_developer.pdf"
jd_json=job_description_pipeline(job_description_file)
print("----jd_json")
print(jd_json)


# Matching
matcher=Matcher()
result=matcher.match(resume_json,jd_json)
print(result)


