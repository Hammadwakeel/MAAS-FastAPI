import io
import logging
from typing import Tuple, List, Optional
from google import genai
from google.genai import types

# Assuming this is your schema file
from app.ads.schemas import ImageRequest, Persona, ToneEnum, GoalEnum

logger = logging.getLogger(__name__)

def _persona_to_text(persona: Persona) -> str:
    """Return a one-line description for a Persona model."""
    interests = ", ".join(persona.interests) if persona.interests else "no listed interests"
    return f"{persona.name} (age: {persona.age_range}, location: {persona.location}, interests: {interests})"

def generate_image(req: ImageRequest) -> Tuple[bytes, str]:
    """
    Generate an Ad image using Gemini with a highly-structured prompt.
    """
    # --- 1. Prepare dynamic prompt components ---

    # Safely convert Persona objects into strings
    if req.selected_personas and len(req.selected_personas) > 0:
        personas_text = "; ".join(_persona_to_text(p) for p in req.selected_personas)
    else:
        personas_text = "general target audience"

    # Define aspect ratio
    aspect_ratio_str = f"{req.width}:{req.height}"
    if aspect_ratio_str == "1200:628":
        aspect_ratio_desc = "1.91:1 (Landscape Link Ad)"
    elif aspect_ratio_str == "1080:1080":
        aspect_ratio_desc = "1:1 (Square Feed Ad)"
    elif aspect_ratio_str == "1080:1920":
        aspect_ratio_desc = "9:16 (Vertical Story Ad)"
    else:
        aspect_ratio_desc = f"{aspect_ratio_str} (Custom)"

    # Create strings for optional fields
    brand_color_str = ""
    if req.brand_colors:
        brand_color_str = f"* **Color Palette:** Strictly use this palette as the primary and accent colors: {', '.join(req.brand_colors)}."
    else:
        brand_color_str = f"* **Color Palette:** Use a professional color palette (e.g., blues, greys, with one strong accent color) that matches the '{req.tone.value}' tone."

    visual_pref_text = ""
    if req.visual_preference:
        visual_pref_text = f"The main visual *must* be: **'{req.visual_preference}'**. This should be the element that catches the eye first."
    else:
        visual_pref_text = "Create a single, strong, and uncluttered focal point that represents the offer (e.g., an abstract graphic of growth, a clean icon, or a person matching the persona)."

    cta_text_str = ""
    if req.cta_text:
        cta_text_str = f"The banner *must* also include the *exact* phrase: **'{req.cta_text}'**. This can be in a button-like shape or as clear, bold text."


    # --- 2. The New, Detailed, and Structured Prompt ---

    prompt = f'''
**ROLE:** You are an expert Art Director at a world-class advertising agency.
**YOUR GOAL:** To generate a *single*, professional, and high-conversion ad banner for a Meta (Facebook/Instagram) campaign.
**YOUR TASK:** Generate one (1) image file based *only* on the strict hierarchy, components, and constraints below.

---

### 1. HIERARCHY OF IMPORTANCE (Strict Priority)

This is the order of what the user MUST see. Your design must follow this.

* **P1: FOCAL POINT (The Visual):**
    * This is the **most important** element. It must stop the user from scrolling.
    * It must be a single, clean, high-quality, professional image or graphic.
    * **Visual Content:** {visual_pref_text}
    * It must be the primary focus of the entire banner.

* **P2: HEADLINE (The Offer):**
    * This is the **second most important** element. It is the primary text.
    * It must be bold, clear, and easy to read in 1 second.
    * **Text Content:** It must be the *exact* phrase: **'{req.offer_description}'**

* **P3: CALL-TO-ACTION (The Instruction):**
    * This is the **third most important** element. It tells the user what to do next.
    * It must be visually distinct (e.g., a button shape or contrasting bold text).
    * **Text Content:** {cta_text_str}

* **P4: BRANDING (The Signature):**
    * This is the **least important** element. It is for brand recognition only.
    * It must be small, clean, and placed in a corner (e.g., bottom-left or top-right).
    * **Text Content:** **'{req.business_name}'** (Render this as clean text, not a complex logo).

---

### 2. DESIGN & LAYOUT MANDATES

* **ASPECT RATIO:** **{aspect_ratio_desc} ({req.width}x{req.height}px).** This is a non-negotiable technical requirement.
* **STYLE & TONE:** **{req.style}, {req.tone.value}.**
* **TARGET AUDIENCE CONTEXT:** The entire design (font choice, imagery, colors) must feel professional and trustworthy to this user: **{personas_text}**.
* **COLOR PALETTE:** {brand_color_str}

---

### 3. WHAT TO AVOID (CRITICAL FAILURES)

* **DO NOT** add *any text* not explicitly listed in P2, P3, or P4.
* **DO NOT** clutter the image. White space is essential. The design must be **minimalist** and **clean**.
* **DO NOT** use generic, cheesy, or low-quality stock photos.
* **DO NOT** use hard-to-read, cursive, or overly-stylized fonts. Readability is the top priority for text.
* **DO NOT** make the branding (P4) large or the main focus. It must be subtle.

---

### FINAL OUTPUT

Generate *only* the final, polished ad banner image. Do not respond with text, questions, or comments.
'''

    # --- 3. Execute the API Call ---

    logger.info("Requesting Gemini image generation for business '%s'", req.business_name)
    logger.debug("Full prompt:\n%s", prompt)  # Good for debugging

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
                raise RuntimeError(f"Gemini returned text only: {part.text[:300]}...")

        raise RuntimeError("No image data found in Gemini response.")

    except AttributeError as e:
        logger.exception(f"Failed to parse Gemini response. It's possible the API response structure is unexpected. {e}")
        raise RuntimeError(f"Failed to parse Gemini response: {e}")
    except Exception as e:
        logger.exception("Gemini image generation failed: %s", e)
        raise RuntimeError(f"Gemini image generation failed: {e}")