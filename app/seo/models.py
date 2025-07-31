# app/seo/models.py
"""
Pydantic models for SEO requests and recommendations.
"""
from pydantic import BaseModel, Field
from typing import Any, Dict, List


class SEORequest(BaseModel):
    """Payload for incoming SEO data."""
    seo_data: Dict[str, Any]


class PrioritySuggestions(BaseModel):
    """Categorized SEO suggestions by effort level."""
    high: List[str] = Field(..., description="High-effort SEO suggestion strings.")
    medium: List[str] = Field(..., description="Medium-effort SEO suggestion strings.")
    low: List[str] = Field(..., description="Low-effort SEO suggestion strings.")


class Recommendation(BaseModel):
    """Wrapper for prioritized SEO suggestions."""
    priority_suggestions: PrioritySuggestions = Field(
        ..., description="All SEO suggestions categorized by effort level."
    )
