# app/content_relevance/models.py
"""
Pydantic models for Content Relevance requests and recommendations (mirroring SEO logic).
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List


class ContentRelevanceRequest(BaseModel):
    """Payload for incoming content relevance data."""
    data: Dict[str, Any] = Field(
        ..., description="Raw metrics and keyword data for relevance analysis."
    )


class PrioritySuggestions(BaseModel):
    """Categorized content relevance suggestions by effort level."""
    high: List[str] = Field(
        ..., description="High-effort content relevance suggestion strings."
    )
    medium: List[str] = Field(
        ..., description="Medium-effort content relevance suggestion strings."
    )
    low: List[str] = Field(
        ..., description="Low-effort content relevance suggestion strings."
    )


class Recommendation(BaseModel):
    """Wrapper for prioritized content relevance suggestions."""
    priority_suggestions: PrioritySuggestions = Field(
        ..., description="All content relevance suggestions categorized by effort level."
    )


class ContentRelevanceResponse(BaseModel):
    """Response model for the combined content relevance endpoint."""
    success: bool = Field(..., description="Indicates if the operation was successful.")
    report: str = Field(..., description="Markdown-formatted content relevance report.")
    priorities: PrioritySuggestions = Field(
        ..., description="Categorized priority suggestions."
    )