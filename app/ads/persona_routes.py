# app/routes/persona_routes.py
from fastapi import APIRouter, HTTPException
from typing import List
from fastapi.responses import StreamingResponse

from app.ads.schemas import BusinessInput, Persona, RegenerateRequest, HeadingsRequest, DescriptionsRequest, ImageRequest
import io
import app.ads.image_service as image_service
import app.ads.headings_service as headings_service
import app.ads.descriptions_service as descriptions_service
from app.ads.persona_service import generate_personas , regenerate_personas

router = APIRouter(prefix="/Ads", tags=["Ads"])

@router.post("/create", response_model=List[Persona])
def create_personas(payload: BusinessInput):
    try:
        personas = generate_personas(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return personas

@router.post("/regenerate", response_model=List[Persona])
def regenerate_personas_endpoint(payload: RegenerateRequest):
    """
    Regenerate personas given all business inputs AND a list of previous personas.
    The endpoint returns a new list of personas (same schema).
    """
    try:
        personas = regenerate_personas(payload, payload.previous_personas)
    except Exception as e:
        # return the error message to the client for quick debugging
        raise HTTPException(status_code=500, detail=str(e))
    return personas

@router.post("/Headings", response_model=List[str])
def create_headings(payload: HeadingsRequest):
    """
    Generate ad headings (returns list[str]).
    """
    try:
        return headings_service.generate_headings(payload)
    except Exception as e:
        # Log error server-side; return HTTP 500 with message for debugging
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/Descriptions", response_model=List[str])
def create_descriptions(payload: DescriptionsRequest):
    try:
        return descriptions_service.generate_descriptions(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/Image", response_class=StreamingResponse)
def create_image(payload: ImageRequest):
    """
    Generate a marketing image for an ad using Gemini.
    """
    try:
        img_bytes, mime = image_service.generate_image(payload)
        return StreamingResponse(io.BytesIO(img_bytes), media_type=mime)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))