# ----------------------------
# app/uiux/models.py
# ----------------------------
from pydantic import BaseModel, Field
from typing import Any, Dict, List


class UIUXRequest(BaseModel):
    """Payload for incoming UI/UX metrics."""
    uiux_data: Dict[str, Any]


class PrioritySuggestions(BaseModel):
    """Categorized UI/UX suggestions by effort level."""
    high: List[str] = Field(..., description="High-effort suggestion strings.")
    medium: List[str] = Field(..., description="Medium-effort suggestion strings.")
    low: List[str] = Field(..., description="Low-effort suggestion strings.")


class Recommendation(BaseModel):
    """Wrapper for prioritized UI/UX suggestions."""
    priority_suggestions: PrioritySuggestions = Field(
        ..., description="All UI/UX suggestions categorized by effort level."
    )
