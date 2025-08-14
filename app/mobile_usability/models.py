# app/mobile_usability/models.py
from pydantic import BaseModel, Field
from typing import Any, Dict, List


class MobileUsabilityRequest(BaseModel):
    """
    Payload for incoming Mobile Usability data.
    """
    mobile_data: Dict[str, Any]


class PrioritySuggestions(BaseModel):
    """Categorized suggestions by effort level for mobile usability."""
    high: List[str] = Field(..., description="High-effort suggestion strings.")
    medium: List[str] = Field(..., description="Medium-effort suggestion strings.")
    low: List[str] = Field(..., description="Low-effort suggestion strings.")


class Recommendation(BaseModel):
    """Wrapper for prioritized suggestions returned by the LLM parser."""
    priority_suggestions: PrioritySuggestions = Field(
        ..., description="All suggestions categorized by effort level."
    )
