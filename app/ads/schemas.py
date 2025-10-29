# app/ads/schemas.py
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import uuid4

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

class ToneEnum(str, Enum):
    PROFESSIONAL = "Professional"
    CASUAL_FRIENDLY = "Casual / Friendly"
    BOLD_PERSUASIVE = "Bold / Persuasive"
    INSPIRING_VISIONARY = "Inspiring / Visionary"

class Persona(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier for this persona")
    flag: bool = Field(False, description="Boolean flag for client use (defaults to False)")
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
    tone: Optional[ToneEnum] = Field(ToneEnum.PROFESSIONAL, description="Tone to use when generating content. Defaults to 'Professional'.")

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
    selected_personas: List[Persona] = Field(..., description="List of selected persona objects to target")
    num_headings: Optional[int] = Field(4, description="How many headings to generate")
    tone: Optional[ToneEnum] = Field(ToneEnum.PROFESSIONAL, description="Tone to use for headings. Defaults to 'Professional'.")

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
    tone: Optional[ToneEnum] = Field(ToneEnum.PROFESSIONAL, description="Tone to use for descriptions. Defaults to 'Professional'.")

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
    style: Optional[str] = Field("modern", description="Desired art style or mood (e.g. modern, minimal, illustrative)")
    width: Optional[int] = Field(1200, description="Image width in px")
    height: Optional[int] = Field(628, description="Image height in px")
    tone: Optional[ToneEnum] = Field(ToneEnum.PROFESSIONAL, description="Tone for image copy or captions. Optional.")

    # --- NEW FIELDS TO ADD ---
    cta_text: Optional[str] = Field(
        None, 
        description="The exact call-to-action text for the banner (e.g., 'Learn More', 'Get Free Call').", 
        example="Get Your Free Strategy Call"
    )
    brand_colors: Optional[List[str]] = Field(
        None, 
        description="A list of primary brand color hex codes.", 
        example=["#0D47A1", "#FFC107"]
    )
    visual_preference: Optional[str] = Field(
        None, 
        description="Specific request for the main visual (e.g., 'Show a graph of growth', 'Show a professional consultant').", 
        example="Show a graph representing website traffic growth"
    )
    
class BudgetType(str, Enum):
    daily = "daily"
    lifetime = "lifetime"

class BudgetPlan(BaseModel):
    type: BudgetType
    budget: str
    duration: str

class BudgetRequest(BaseModel):
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
    num_options: Optional[int] = Field(2, description="Number of budget option groups to return (default 2)")
    tone: Optional[ToneEnum] = Field(ToneEnum.PROFESSIONAL, description="Tone for budget explanations (optional).")
