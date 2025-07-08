from fastapi import APIRouter, Depends
from app.page_speed.models import (
    AnalyzeRequest,
    AnalyzeResponse
)

import logging

from app.page_speed.services import PageSpeedService 

router = APIRouter(prefix="/pagespeed", tags=["PageSpeed"])

"""
PageSpeed Insights API routes for analyzing URLs and generating reports.
"""

logger = logging.getLogger("app.page_speed.routes")
logger.setLevel(logging.INFO)


def get_pagespeed_service() -> PageSpeedService:
    """Dependency to get a new PageSpeedService instance."""
    return PageSpeedService()


@router.post("/analyze-url", response_model=AnalyzeResponse)
async def analyze_url(
    request: AnalyzeRequest,
    service: PageSpeedService = Depends(get_pagespeed_service)
):
    """
    One-stop endpoint to fetch PageSpeed data, generate report, and derive priorities.

    - Takes a single 'url' field in the body.
    - Returns pagespeed_data, human-friendly report, and priority lists.
    """
    url_str = str(request.url)
    logger.info("Received POST /analyze-url for URL: %s", url_str)

    try:
        # 1. Fetch raw PageSpeed Insights data
        pagespeed_data = service.get_pagespeed_data(url_str)
        logger.debug("Fetched PageSpeed data (bytes=%d)", len(str(pagespeed_data)))

        # 2. Generate text report via Gemini
        report_text = service.generate_report_with_gemini(pagespeed_data)
        logger.debug("Generated report text (chars=%d)", len(report_text))

        # 3. Produce prioritized improvements
        priorities = service.generate_priority(report_text)
        logger.info("Analysis complete for %s", url_str)

        return AnalyzeResponse(
            success=True,
            url=url_str,
            report=report_text,
            priorities=priorities,
            error=None
        )
    except Exception as e:
        logger.error("Error in /analyze-url: %s", e, exc_info=True)
        return AnalyzeResponse(
            success=False,
            url=url_str,
            report=None,
            priorities=None,
            error=str(e)
        )
