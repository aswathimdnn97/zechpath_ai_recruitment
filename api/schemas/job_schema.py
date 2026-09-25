from typing import Any, Dict, Optional

from pydantic import BaseModel


class JobResponse(BaseModel):

    task_id: str

    task_type: str

    candidate_id: Optional[str] = None

    jd_id: Optional[str] = None

    recruitment_job_id: Optional[str] = None

    status: str

    progress: int = 0

    result_reference: Optional[str] = None

    error: Optional[Dict[str, Any]] = None