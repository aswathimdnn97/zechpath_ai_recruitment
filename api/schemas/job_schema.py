from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobResponse(BaseModel):
    job_id: str
    job_type: str
    candidate_id: Optional[str] = None
    status: str
    progress: int = 0
    result_reference: Optional[str] = None
    error: Optional[str] = None