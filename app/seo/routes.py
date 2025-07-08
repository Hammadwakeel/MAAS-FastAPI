from fastapi import APIRouter, HTTPException
from .seo_service import SEOService
from .models import SEORequest

router = APIRouter(prefix="/seo", tags=["SEO"])

seo_service = SEOService()

@router.post("/generate-full-report")
def generate_full_seo_analysis(request: SEORequest):
    """
    Generate full SEO analysis: report + prioritized suggestions.
    """
    try:
        # Step 1: Generate SEO report (as a string)
        report = seo_service.generate_seo_report(request.seo_data)

        # Step 2: Generate prioritized SEO suggestions from the report
        priority_suggestions = seo_service.generate_seo_priority(report)

        return {
            "success": True,
            "report": report,
            "priority_suggestions": priority_suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
