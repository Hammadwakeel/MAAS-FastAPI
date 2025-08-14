"""
Main FastAPI application module.
"""
import os
import time
import logging
import json
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import warnings

from app.page_speed.config import settings
from app.page_speed.models import HealthResponse
from app.rag.routes import router as rag_router
from app.seo import routes as seo_routes
from app.page_speed import routes as page_speed_routes
from app.content_relevence import routes as content_relevance_routes
from app.keywords.routes import router as keywords_router
from app.uiux import routes as uiux_routes
from app.mobile_usability import routes as mobile_usability

# ─────────────────────────────────────────────
# Suppress warnings
# ─────────────────────────────────────────────
warnings.filterwarnings(
    "ignore",
    message="Valid config keys have changed in V2:*",
    category=UserWarning,
    module="pydantic._internal._config",
)
warnings.filterwarnings("ignore", category=FutureWarning)
try:
    from langchain_core._api.deprecation import LangChainDeprecationWarning
    warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
except ImportError:
    pass

# ─────────────────────────────────────────────
# Logging setup
# ─────────────────────────────────────────────
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

startup_time = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_time
    startup_time = time.time()
    logger.info("🚀 Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("📊 Server will run on %s:%s", settings.host, settings.port)
    yield
    logger.info("📊 Shutting down %s", settings.app_name)

# ─────────────────────────────────────────────
# FastAPI app creation
# ─────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
app.include_router(rag_router)
app.include_router(seo_routes.router)
app.include_router(content_relevance_routes.router)
app.include_router(page_speed_routes.router)
app.include_router(keywords_router)
app.include_router(uiux_routes.router)
app.include_router(mobile_usability.router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/", response_model=dict)
async def root():
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "description": settings.app_description,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
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

@app.exception_handler(404)
async def not_found_handler(request, exc):
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
    logger.error("500 Internal Server Error: %s %s -> %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )

# ─────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    import os

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port
    )

