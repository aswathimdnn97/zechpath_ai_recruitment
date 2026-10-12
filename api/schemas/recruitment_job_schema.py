from typing import Optional

from pydantic import BaseModel


# ============================================================
# CREATE RECRUITMENT JOB REQUEST
# ============================================================

class RecruitmentJobCreateRequest(BaseModel):
    jd_id: str


# ============================================================
# RECRUITMENT JOB RESPONSE
# ============================================================

class RecruitmentJobResponse(BaseModel):
    job_id: str
    jd_id: str
    status: str
    created_at: Optional[str] = None
    closed_at: Optional[str] = None