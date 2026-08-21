from pydantic import BaseModel


class ScoreRequest(BaseModel):
    job_id: str