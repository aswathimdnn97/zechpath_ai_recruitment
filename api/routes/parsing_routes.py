from fastapi import APIRouter

from api.service.parsing_service import parse_resume_by_id


router = APIRouter(
    prefix="/api/v1/resumes",
    tags=["Resume Parsing"]
)


@router.post("/{resume_id}/parse")
async def parse_resume(resume_id: str):

    return parse_resume_by_id(resume_id)