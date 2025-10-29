# app/services/persona_service.py
import os
import json
import logging
import time
from typing import List
import google.generativeai as genai
from pydantic import ValidationError

from app.ads.schemas import Persona, BusinessInput

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# initialize client (reads GEMINI_API_KEY from environment)
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logger.error("GEMINI_API_KEY environment variable not set")
    raise RuntimeError("Please set the GEMINI_API_KEY environment variable")

try:
    genai.configure(api_key=API_KEY)
    logger.info("Configured google.generativeai with provided API key")
except Exception as e:
    logger.exception("Failed to configure google.generativeai: %s", e)
    raise

def _build_prompt(b: BusinessInput) -> str:
    examples_json = [
        {
            "name": "Startup Founders",
            "headline": "Entrepreneurs launching new businesses",
            "age_range": "25-40",
            "location": "United Kingdom",
            "interests": [
                "Entrepreneurship",
                "Startups",
                "Business coaching",
                "Tech tools"
            ],
            "description": "Likely to need professional websites to establish credibility; motivated by investor/customer trust and fast go-to-market. Prefer outreach via LinkedIn, Twitter, and startup meetups."
        },
        {
            "name": "Local Shop Owners",
            "headline": "Owners of brick-and-mortar retail shops",
            "age_range": "35-55",
            "location": "London and Midlands",
            "interests": [
                "Small business",
                "Retail management",
                "Local advertising"
            ],
            "description": "They want affordable websites to attract local customers and show store hours/offers. Respond well to local ads, Facebook community groups, and in-store flyers."
        },
        {
            "name": "Freelancers & Consultants",
            "headline": "Independent professionals offering services online",
            "age_range": "22-45",
            "location": "United Kingdom",
            "interests": [
                "Personal branding",
                "Online marketing",
                "Networking",
                "LinkedIn"
            ],
            "description": "Need personal websites to showcase expertise, attract clients and build credibility; motivated by lead generation and portfolio presentation. Prefer LinkedIn, industry communities, and content marketing."
        }
    ]

    main_goal_value = b.main_goal.value
    main_goal_desc = getattr(b.main_goal, "description", "")
    tone_enum = getattr(b, "tone", None)
    tone_value = tone_enum.value if tone_enum is not None else "Professional"

    prompt = f'''
You are a senior marketing strategist specialized in creating *ideal-customer / target-audience personas* for businesses. Produce exactly {b.num_personas} distinct IDEAL-CUSTOMER personas tailored to the business described below.

**Tone:** Use a "{tone_value}" tone for all persona text (including descriptions and headlines). Apply the tone consistently. If tone is "Professional", use a formal, trustworthy voice. If "Casual / Friendly", be approachable and conversational. If "Bold / Persuasive", use urgency and strong calls-to-action. If "Inspiring / Visionary", use motivating, future-focused language.

**Output format (required):** Return ONLY a JSON array of objects. Each object must contain these properties in this exact order:
  1. name (string)
  2. headline (string; 3-6 words)
  3. age_range (string; numeric range like "25-40")
  4. location (string)
  5. interests (array of short strings; 3-6 items)
  6. description (string; 1-3 sentences)

**Description field requirements:** The `description` must summarize the persona as an *ideal customer*:
- who they are (role / brief demographic),
- top 1–2 pain points or needs,
- primary buying trigger or motivation,
- preferred channels to reach them (e.g., Instagram, LinkedIn, email, local events),
- why they would choose this business / how the offer solves their need.
- Use the requested tone when phrasing motivations and channels.

**Do NOT include any extra top-level keys, comments, or explanation text. JSON array only.**

EXAMPLE PERSONAS (format example):
{json.dumps(examples_json, indent=2)}

Business inputs:
- Business name: {b.business_name}
- Business category: {b.business_category}
- Business description: {b.business_description}
- Promotion type: {b.promotion_type}
- Offer description: {b.offer_description}
- Value proposition: {b.value}
- Main goal: {main_goal_value} — {main_goal_desc}
- Serving clients info: {b.serving_clients_info}
- Serving clients location: {b.serving_clients_location}

Generate the {b.num_personas} personas now as a JSON array that exactly matches the schema and style shown above.
'''
    built = prompt.strip()
    logger.debug("Built persona prompt (goal=%s; tone=%s): %s", main_goal_value, tone_value, built[:400] + ("…" if len(built) > 400 else ""))
    return built

def _extract_json_array(raw: str) -> str:
    start = raw.find('[')
    end = raw.rfind(']')
    if start != -1 and end != -1 and end > start:
        snippet = raw[start:end + 1]
        logger.debug("Extracted JSON array snippet from raw response (length=%d)", len(snippet))
        return snippet
    logger.debug("No JSON array brackets found in raw response; returning full raw text for parsing")
    return raw

def generate_personas(b: BusinessInput) -> List[Persona]:
    prompt = _build_prompt(b)

    try:
        model_name = "gemini-2.5-pro"
        logger.info("Initializing Gemini model: %s", model_name)
        model = genai.GenerativeModel(model_name)

        logger.info("Sending generation request to Gemini for business '%s'", b.business_name)
        start_ts = time.perf_counter()
        response = model.generate_content(prompt)
        duration = time.perf_counter() - start_ts
        logger.info("Gemini generate_content completed in %.2fs", duration)

    except Exception as e:
        logger.exception("Gemini request failed for business '%s': %s", b.business_name, e)
        raise RuntimeError(f"Gemini request failed: {e}")

    raw = None
    try:
        if response and hasattr(response, "text") and response.text:
            raw = response.text
            logger.debug("Received response.text (length=%d)", len(raw))
        elif response and getattr(response, "candidates", None):
            first = response.candidates[0]
            if getattr(first, "finish_reason", "").upper() == "SAFETY":
                msg = "Gemini generation blocked by safety filter"
                logger.error(msg)
                raise RuntimeError(msg)
            raw = getattr(first, "content", None) or getattr(first, "text", None) or str(response)
            logger.debug("Received candidate-based response (length=%d)", len(raw) if raw else 0)
        else:
            raw = str(response)
            logger.debug("Converted response object to string (length=%d)", len(raw))
    except Exception as e:
        logger.exception("Failed to extract raw text from Gemini response for business '%s'", b.business_name)
        raise RuntimeError(f"Failed to extract Gemini response text: {e}")

    if not raw:
        logger.error("Empty response received from Gemini for business '%s'", b.business_name)
        raise RuntimeError("Empty response received from Gemini")

    json_snippet = _extract_json_array(raw)
    logger.info("Attempting to parse JSON snippet for business '%s' (snippet length=%d)", b.business_name, len(json_snippet))

    try:
        parsed = json.loads(json_snippet)

        if isinstance(parsed, dict):
            for key in ("items", "personas", "data", "results"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    logger.debug("Found persona list inside wrapper key '%s'", key)
                    break

        if not isinstance(parsed, list):
            logger.error("Parsed JSON is not a list for business '%s' (type=%s)", b.business_name, type(parsed))
            raise ValueError("Expected top-level JSON array of persona objects")

        personas: List[Persona] = []
        for idx, obj in enumerate(parsed):
            try:
                persona = Persona.parse_obj(obj)
                personas.append(persona)
                logger.debug("Validated persona %d: %s", idx, persona.name)
            except ValidationError as ve:
                logger.error("Persona validation failed for item %s: %s\nRaw item: %s", idx, ve, obj)
                raise

        logger.info("Successfully generated and validated %d personas for business '%s'", len(personas), b.business_name)
        return personas

    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        logger.exception("Failed to parse/validate Gemini JSON output for business '%s'", b.business_name)
        raise RuntimeError(
            f"Failed to parse Gemini response as JSON Personas: {e}\n\nRaw Gemini response:\n{raw}"
        )

def regenerate_personas(b: BusinessInput, previous_personas: List[Persona]) -> List[Persona]:
    base_prompt = _build_prompt(b)

    try:
        prev_list = [p.dict() if hasattr(p, "dict") else p for p in previous_personas]
    except Exception:
        prev_list = previous_personas

    prev_json = json.dumps(prev_list, indent=2)
    tone_enum = getattr(b, "tone", None)
    tone_value = tone_enum.value if tone_enum is not None else "Professional"

    extra_instructions = f"""
Previous personas provided (do NOT repeat these exactly):
{prev_json}

Tone: Use a "{tone_value}" tone consistently in names and descriptions. If tone is "Professional" use a formal voice; if "Casual / Friendly" be conversational; if "Bold / Persuasive" be urgency-driven; if "Inspiring / Visionary" be motivational.

Instructions:
- Produce exactly {b.num_personas} personas tailored to the same business inputs above.
- **Do not duplicate** persona names or core audience segments included in the previous list.
- If a previous persona should be refined, produce a refined version but change the name slightly
  and mention in the description what was improved.
- Aim for personas that are distinct, actionable, and aligned with the business's main goal:
  "{getattr(b, 'main_goal', '')}".
- Output MUST be ONLY a JSON array of persona objects matching the schema:
  name, headline, age_range, location, interests, description (in that order).
"""
    prompt = base_prompt + "\n\n" + extra_instructions

    logger.info("Regenerating personas for business '%s' with %d previous personas (tone=%s)",
                b.business_name, len(prev_list), tone_value)

    try:
        model_name = "gemini-2.5-pro"
        model = genai.GenerativeModel(model_name)

        start_ts = time.perf_counter()
        response = model.generate_content(prompt)
        duration = time.perf_counter() - start_ts
        logger.info("Gemini regenerate_content completed in %.2fs", duration)

    except Exception as e:
        logger.exception("Gemini regenerate request failed for business '%s': %s", b.business_name, e)
        raise RuntimeError(f"Gemini regenerate request failed: {e}")

    raw = None
    try:
        if response and hasattr(response, "text") and response.text:
            raw = response.text
            logger.debug("Regenerate response.text length=%d", len(raw))
        elif response and getattr(response, "candidates", None):
            first = response.candidates[0]
            if getattr(first, "finish_reason", "").upper() == "SAFETY":
                msg = "Gemini regeneration blocked by safety filter"
                logger.error(msg)
                raise RuntimeError(msg)
            raw = getattr(first, "content", None) or getattr(first, "text", None) or str(response)
            logger.debug("Regenerate candidate response length=%d", len(raw) if raw else 0)
        else:
            raw = str(response)
            logger.debug("Regenerate response converted to string length=%d", len(raw))
    except Exception as e:
        logger.exception("Failed to extract raw text from Gemini regenerate response")
        raise RuntimeError(f"Failed to extract Gemini response text: {e}")

    if not raw:
        logger.error("Empty regenerate response from Gemini for business '%s'", b.business_name)
        raise RuntimeError("Empty response received from Gemini")

    json_snippet = _extract_json_array(raw)
    logger.info("Attempting to parse regenerated JSON snippet for business '%s' (len=%d)",
                b.business_name, len(json_snippet))

    try:
        parsed = json.loads(json_snippet)

        if isinstance(parsed, dict):
            for key in ("items", "personas", "data", "results"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    logger.debug("Found regenerated persona list inside wrapper key '%s'", key)
                    break

        if not isinstance(parsed, list):
            logger.error("Parsed regenerated JSON is not a list (type=%s)", type(parsed))
            raise ValueError("Expected top-level JSON array of persona objects (regenerate)")

        personas: List[Persona] = []
        for idx, obj in enumerate(parsed):
            try:
                persona = Persona.parse_obj(obj)
                personas.append(persona)
                logger.debug("Validated regenerated persona %d: %s", idx, persona.name)
            except ValidationError as ve:
                logger.error("Regenerated persona validation failed for index %d: %s\nRaw item: %s",
                             idx, ve, obj)
                raise

        logger.info("Successfully regenerated %d personas for business '%s'", len(personas), b.business_name)
        return personas

    except (json.JSONDecodeError, ValidationError, ValueError) as e:
        logger.exception("Failed to parse/validate regenerated Gemini JSON output for business '%s'", b.business_name)
        raise RuntimeError(
            f"Failed to parse Gemini regenerate response as JSON Personas: {e}\n\nRaw Gemini response:\n{raw}"
        )
