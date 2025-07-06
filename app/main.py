"""
Main FastAPI application module.
"""
import time
import logging
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.models import (
    PageSpeedRequest,
    PageSpeedDataResponse,
    ReportRequest,
    ReportResponse,
    HealthResponse,
    PriorityRequest,
    PriorityResponse
)
from app.services import PageSpeedService
from app.rag.routes import router as rag_router
from app.seo import routes as seo_routes


# ------------------------
# Configure root logger
# ------------------------
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# Global variable to track startup time
startup_time = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global startup_time
    startup_time = time.time()
    logger.info("🚀 Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("📊 Server running on %s:%s", settings.host, settings.port)
    yield
    logger.info("📊 Shutting down %s", settings.app_name)

# Create FastAPI app instance
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount RAG router
app.include_router(rag_router)

app.include_router(seo_routes.router)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get PageSpeed service
def get_pagespeed_service() -> PageSpeedService:
    """Dependency to get a new PageSpeedService instance."""
    return PageSpeedService()


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "description": settings.app_description,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    global startup_time
    
    if startup_time:
        uptime_seconds = time.time() - startup_time
        uptime_str = f"{uptime_seconds:.2f} seconds"
    else:
        uptime_str = "Unknown"
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        uptime=uptime_str
    )


@app.post("/pagespeed", response_model=PageSpeedDataResponse)
async def fetch_pagespeed(
    request: PageSpeedRequest,
    service: PageSpeedService = Depends(get_pagespeed_service)
):
    """
    Fetch raw PageSpeed Insights data for a given URL.

    Request body:
    {
      "url": "https://www.example.com"
    }

    Returns:
    {
      "success": true,
      "url": "https://www.example.com",
      "pagespeed_data": { ... },
      "error": null
    }
    """
    url_str = str(request.url)
    logger.info("Received POST /pagespeed for URL: %s", url_str)
    
    try:
        pagespeed_data = service.get_pagespeed_data(url_str)
        logger.info("Returning PageSpeed data for %s", url_str)
        return PageSpeedDataResponse(
            success=True,
            url=url_str,
            pagespeed_data=pagespeed_data,
            error=None
        )
    except Exception as e:
        logger.error("Error in /pagespeed endpoint for URL %s: %s", url_str, e, exc_info=True)
        return PageSpeedDataResponse(
            success=False,
            url=url_str,
            pagespeed_data=None,
            error=str(e)
        )


@app.post("/generate-report", response_model=ReportResponse)
async def generate_report(
    body: ReportRequest,
    service: PageSpeedService = Depends(get_pagespeed_service)
):
    """
    Generate a Gemini-based optimization report from previously-fetched PageSpeed JSON.

    Request body:
    {
      "pagespeed_data": { …full PageSpeed JSON… }
    }

    Returns:
    {
      "success": true,
      "report": "Gemini-generated analysis…",
      "error": null
    }
    """
    logger.info("Received POST /generate-report")

    try:
        pagespeed_data = body.pagespeed_data
        logger.debug("PageSpeed JSON payload size: %d bytes", len(str(pagespeed_data)))
        
        report_text = service.generate_report_with_gemini(pagespeed_data)
        logger.info("Returning Gemini report.")
        return ReportResponse(
            success=True,
            report=report_text,
            error=None
        )
    except Exception as e:
        logger.error("Error in /generate-report endpoint: %s", e, exc_info=True)
        return ReportResponse(
            success=False,
            report=None,
            error=str(e)
        )


@app.post("/generate-priorities", response_model=PriorityResponse)
async def generate_priorities(
    request: PriorityRequest,
    service: PageSpeedService = Depends(get_pagespeed_service)
):
    """
    Generate a prioritized list of performance improvements from a Gemini report.

    Request body:
    {
      "report": "Full Gemini-generated performance report..."
    }

    Returns:
    {
      "success": true,
      "priorities": {
        "High": ["Optimize TBT by reducing JS execution", ...],
        "Medium": [...],
        "Low": [...]
      },
      "error": null
    }
    """
    logger.info("Received POST /generate-priorities")
    try:
        priorities = service.generate_priority(request.report)
        return PriorityResponse(success=True, priorities=priorities)
    except Exception as e:
        logger.error("Error in /generate-priorities: %s", e, exc_info=True)
        return PriorityResponse(success=False, priorities=None, error=str(e))


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    logger.warning("404 Not Found: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested endpoint was not found",
            "docs": "/docs"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler."""
    logger.error("500 Internal Server Error: %s %s -> %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    # When running directly, uvicorn will print its own logs. We just start it here.
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
