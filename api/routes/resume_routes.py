from fastapi import APIRouter,UploadFile,File
from api.service.resume_service import save_resume

router=APIRouter(prefix="/api/v1/resumes", tags=["Resumes"])

@router.post("")
async def upload_resume(file:UploadFile=File(...)):
    return save_resume(file)
    