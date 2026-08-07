from utils.logger import logger
from document_processing.resume.resume_pipeline import resume_pipeline
from document_processing.job_description.job_description_pipeline import job_description_pipeline
from pipelines.recruiter_pipeline import recruitment_pipeline

logger.info("Resume Uploaded")

"""Resume parsing"""
resume_file="data/resume/pdf/syzfjbzwjncs.pdf"
resume_text=resume_pipeline(resume_file)
# print(resume_text)

"""JD Parsing"""
job_description_file="data/job_descriptions/jd_python_developer.pdf"
jd_text=job_description_pipeline(job_description_file)
# print(jd_text)


result = recruitment_pipeline(
    resume_text,
    jd_text
)

print(result)
 

