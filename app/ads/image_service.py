import io
import logging
from typing import Tuple
from google import genai
from google.genai import types

from app.ads.schemas import ImageRequest, Persona

logger = logging.getLogger(__name__)

def _persona_to_text(persona: Persona) -> str:
    """Return a one-line description for a Persona model."""
    interests = ", ".join(persona.interests) if persona.interests else "no listed interests"
    return f"{persona.name} (age: {persona.age_range}, location: {persona.location}, interests: {interests})"

def generate_image(req: ImageRequest) -> Tuple[bytes, str]:
    """
    Generate an Ad image using Gemini 2.0 flash experimental image model.
    Falls back to returning text prompts if Gemini returns only text.
    """
    # Safely convert Persona objects into strings
    if req.selected_personas and len(req.selected_personas) > 0:
        personas_text = "; ".join(_persona_to_text(p) for p in req.selected_personas)
    else:
        personas_text = "general target audience"

    prompt = (
        f"Create a professional advertisement image for the business '{req.business_name}'. "
        f"Category: {req.business_category}. "
        f"Description: {req.business_description}. "
        f"Promotion type: {req.promotion_type}. "
        f"Offer details: {req.offer_description}. "
        f"Value proposition: {req.value}. "
        f"Main goal: {req.main_goal.value}. "
        f"Serving clients info: {req.serving_clients_info}. "
        f"Location: {req.serving_clients_location}. "
        f"Target persona(s): {personas_text}. "
        "The image should be modern, vibrant, and suitable for a social media advertisement."
    )

    logger.info("Requesting Gemini image generation for business '%s'", req.business_name)

    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=(prompt
            ),
            config=types.GenerateContentConfig(
                response_modalities=["text", "Image"]
            ),
        )

        # Parse Gemini response for images
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                image_bytes = part.inline_data.data
                return image_bytes, "image/png"

        # Fallback: Gemini returned text (prompt or explanation)
        for part in response.candidates[0].content.parts:
            if getattr(part, "text", None):
                logger.warning("Gemini returned text instead of image: %s", part.text[:300])
                raise RuntimeError("Gemini returned text only, no image data found.")

        raise RuntimeError("No image data found in Gemini response.")

    except Exception as e:
        logger.exception("Gemini image generation failed: %s", e)
        raise RuntimeError(f"Gemini image generation failed: {e}")
