# app/models.py

"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any, List

class PageSpeedRequest(BaseModel):
    """Request model for fetching PageSpeed data."""
    url: HttpUrl = Field(
        ...,
        description="The URL to analyze for PageSpeed insights",
        example="https://www.example.com"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.ocoya.com/"
            }
        }

class PageSpeedDataResponse(BaseModel):
    """Response model that returns only the raw PageSpeed data."""
    success: bool = Field(
        ...,
        description="Whether the PageSpeed fetch was successful"
    )
    url: str = Field(
        ...,
        description="The analyzed URL"
    )
    pagespeed_data: Optional[Dict[Any, Any]] = Field(
        None,
        description="Raw PageSpeed Insights data"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if fetching failed"
    )

class ReportRequest(BaseModel):
    """
    Request model for generating a Gemini report.
    Expects the entire raw PageSpeed JSON payload in the body.
    """
    pagespeed_data: Dict[Any, Any] = Field(
        ...,
        description="Raw PageSpeed Insights data (JSON) previously fetched",
    )

    class Config:
        schema_extra = {
            "example": {
                "pagespeed_data": {
                    # (Truncated example; in practice this would be
                    # the full runPagespeed v5 JSON structure)
                    "lighthouseResult": {
                        "audits": {
                            "first-contentful-paint": {"numericValue": 1234},
                            "largest-contentful-paint": {"numericValue": 2345}
                        }
                    },
                    "loadingExperience": {
                        "metrics": {
                            "FIRST_CONTENTFUL_PAINT_MS": {"percentile": 1200, "category": "FAST"}
                        }
                    }
                    # …etc.
                }
            }
        }

class ReportResponse(BaseModel):
    """Response model that returns only the Gemini-generated report."""
    success: bool = Field(
        ...,
        description="Whether report generation was successful"
    )
    report: Optional[str] = Field(
        None,
        description="Gemini-generated performance optimization report"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if report generation failed"
    )

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(
        ...,
        description="Health status of the API"
    )
    version: str = Field(
        ...,
        description="API version"
    )
    uptime: str = Field(
        ...,
        description="API uptime"
    )

class PriorityRequest(BaseModel):
    report: str


class PriorityResponse(BaseModel):
    success: bool
    priorities: Optional[Dict[str, List[str]]] = None
    error: Optional[str] = None

class AnalyzeRequest(BaseModel):
    url: HttpUrl

class AnalyzeResponse(BaseModel):
    success: bool
    url: HttpUrl
    report: str | None
    priorities: dict | None
    error: str | None