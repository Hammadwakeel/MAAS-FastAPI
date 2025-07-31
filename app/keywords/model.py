from pydantic import BaseModel, Field
from typing import List

class BusinessDescription(BaseModel):
    description: str = Field(..., description="The business description to base keywords on.")

class KeywordsResponse(BaseModel):
    keywords: List[str] = Field(
        ..., description="A list of relevant keywords generated from the business description."
    )