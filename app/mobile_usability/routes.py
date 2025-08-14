# app/mobile_usability/routes.py
from fastapi import APIRouter, HTTPException
from app.mobile_usability.service import MobileUsabilityService
from app.mobile_usability.models import MobileUsabilityRequest

router = APIRouter(prefix="/mobile_usability", tags=["MobileUsability"])

service = MobileUsabilityService()


@router.post("/generate-full-report")
def generate_full_mobile_analysis(request: MobileUsabilityRequest):
    """
    Generate full Mobile Usability analysis using Gemini: report + prioritized suggestions.
    """
    try:
        # 1) Generate report (string) via LLM
        report = service.generate_mobile_report(request.mobile_data)

        # 2) Generate prioritized suggestions via LLM (Pydantic parser)
        priority_suggestions = service.generate_mobile_priority(report)

        return {
            "success": True,
            "report": report,
            "priority_suggestions": priority_suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
