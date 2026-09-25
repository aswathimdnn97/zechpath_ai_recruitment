from pydantic import BaseModel


class ScoreRequest(BaseModel):
    jd_id: str
    job_id: str