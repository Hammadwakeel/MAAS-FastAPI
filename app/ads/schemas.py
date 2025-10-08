# app/ads/schemas.py
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class GoalEnum(str, Enum):
    GET_MORE_WEBSITE_VISITORS = (
        "Get more website visitors",
        "Drive quality traffic to your website and increase page views"
    )
    GENERATE_LEADS = (
        "Generate Leads",
        "Collect contact information from potential customers"
    )
    INCREASE_SALES = (
        "Increase Sales",
        "Drive purchases and boost your revenue"
    )
    BRAND_AWARENESS = (
        "Brand Awareness",
        "Increase visibility and recognition of your brand"
    )

    def __new__(cls, value, description):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj

class Persona(BaseModel):
    name: str
    headline: str
    age_range: str
    location: str
    interests: List[str]
    description: str

class BusinessInput(BaseModel):
    business_name: str = Field(..., example="GrowthAspired")
    business_category: str = Field(..., example="Software House")
    business_description: str
    promotion_type: str
    offer_description: str
    value: str
    main_goal: GoalEnum = Field(..., description="Primary marketing goal (enum)", example=GoalEnum.GENERATE_LEADS.value)
    serving_clients_info: str
    serving_clients_location: str
    num_personas: int = 3


class RegenerateRequest(BusinessInput):
    """
    Request model for regenerating personas:
    - includes the same business inputs as BusinessInput
    - plus previous_personas (list of Persona objects) to inform regeneration
    """
    previous_personas: List[Persona]


class HeadingsRequest(BaseModel):
    business_name: str = Field(..., example="GrowthAspired")
    business_category: str = Field(..., example="Software House")
    business_description: str
    promotion_type: str
    offer_description: str
    value: str
    main_goal: GoalEnum = Field(..., description="Primary marketing goal (enum)")
    serving_clients_info: str
    serving_clients_location: str
    # list of previously generated or selected persona objects (use Persona model)
    selected_personas: List[Persona] = Field(..., description="List of selected persona objects to target")
    # optional: prefer number of headings (defaults to 4)
    num_headings: Optional[int] = Field(4, description="How many headings to generate")


class DescriptionsRequest(BaseModel):
    business_name: str = Field(..., example="GrowthAspired")
    business_category: str = Field(..., example="Software House")
    business_description: str
    promotion_type: str
    offer_description: str
    value: str
    main_goal: GoalEnum = Field(..., description="Primary marketing goal (enum)")
    serving_clients_info: str
    serving_clients_location: str
    selected_personas: List[Persona] = Field(..., description="List of selected persona objects to target")
    num_descriptions: Optional[int] = Field(4, description="How many ad descriptions to generate (default 4)")


class ImageRequest(BaseModel):
    business_name: str = Field(..., example="GrowthAspired")
    business_category: str = Field(..., example="Software House")
    business_description: str
    promotion_type: str
    offer_description: str
    value: str
    main_goal: GoalEnum = Field(..., description="Primary marketing goal (enum)")
    serving_clients_info: str
    serving_clients_location: str
    selected_personas: List[Persona] = Field(..., description="List of selected persona objects to target")
    # optional style/size params
    style: Optional[str] = Field("modern", description="Desired art style or mood (e.g. modern, minimal, illustrative)")
    width: Optional[int] = Field(1200, description="Image width in px")
    height: Optional[int] = Field(628, description="Image height in px")
