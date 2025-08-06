from fastapi import APIRouter, HTTPException
from app.uiux.models import UIUXRequest
from app.uiux.service import UIUXService

router = APIRouter(prefix="/uiux", tags=["UIUX"])
uiux_service = UIUXService()

@router.post("/generate-full-report")
def generate_full_uiux_analysis(request: UIUXRequest):
    """
    Generate full UI/UX analysis: report + prioritized suggestions.
    """
    try:
        report = uiux_service.generate_uiux_report(request.uiux_data)
        priority_suggestions = uiux_service.generate_uiux_priority(report)
        return {
            "success": True,
            "report": report,
            "priority_suggestions": priority_suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))