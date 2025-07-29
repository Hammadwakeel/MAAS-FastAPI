# routes.py
from fastapi import APIRouter, HTTPException, Request
import logging
from .content_relevance_service import ContentRelevanceService
from .models import ContentRelevanceRequest, ContentRelevanceResponse

# Create a module-level logger
router_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content-relevance", tags=["ContentRelevance"])
service = ContentRelevanceService()

@router.post("/report", response_model=ContentRelevanceResponse)
async def generate_full_content_relevance(request: Request, payload: ContentRelevanceRequest):
    """
    Generate a full Content Relevance report and corresponding prioritized suggestions.
    """
    router_logger.info("Received content relevance request from %s", request.client.host)
    router_logger.debug("Payload data: %s", payload.data)

    try:
        report = service.generate_content_relevance_report(payload.data)
        router_logger.info("Report generated successfully")

        priorities = service.generate_content_priority(report)
        router_logger.info("Priorities extracted successfully")

        return ContentRelevanceResponse(success=True, report=report, priorities=priorities)

    except Exception as e:
        router_logger.error("Error during content relevance processing: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
