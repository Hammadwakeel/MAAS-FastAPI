# models.py
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging

# Optionally create a logger here if you need to log model-related events
model_logger = logging.getLogger(__name__)

class ContentRelevanceRequest(BaseModel):
    data: Dict[str, Any]

    def __init__(self, **data):
        super().__init__(**data)
        model_logger.debug("Initialized ContentRelevanceRequest with data: %s", self.data)

class ContentRelevanceResponse(BaseModel):
    success: bool
    report: str
    priorities: Dict[str, Any]

    def __init__(self, **data):
        super().__init__(**data)
        model_logger.debug(
            "Initialized ContentRelevanceResponse with success=%s, keys: %s",
            self.success,
            list(self.priorities.keys()) if self.priorities else []
        )
