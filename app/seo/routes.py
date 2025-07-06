from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from .seo_service import SEOService


router = APIRouter(prefix="/seo", tags=["SEO"])

seo_service = SEOService()


class SEORequest(BaseModel):
    seo_data: Dict[str, Any]

class SEOPriorityRequest(BaseModel):
    report: str

@router.post("/generate-report")
def generate_seo_report(request: SEORequest):
    """
    Generate SEO report via Gemini.
    """
    try:
        report = seo_service.generate_seo_report(request.seo_data)
        return {"success": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/generate-priority")
def generate_seo_priority(request: SEOPriorityRequest):
    """
    Generate prioritized SEO suggestions from the report.
    """
    try:
        priority_suggestions = seo_service.generate_seo_priority(request.report)
        return {"success": True, "priority_suggestions": priority_suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
