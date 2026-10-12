from typing import Optional

from pydantic import BaseModel


class ScoreRequest(BaseModel):
    jd_id: str
    job_id: Optional[str] = None