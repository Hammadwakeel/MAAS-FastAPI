# app/services/descriptions_service.py
import os
import json
import logging
import time
from typing import List

import google.generativeai as genai

from app.ads.schemas import DescriptionsRequest, Persona

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Ensure genai configured (harmless if already configured elsewhere)
API_KEY = os.getenv("GEMINI_API_KEY")
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        logger.debug("Configured google.generativeai in descriptions service")
    except Exception:
        logger.exception("Failed to configure google.generativeai in descriptions service")


def _extract_json_array(raw: str) -> str:
    start = raw.find('[')
    end = raw.rfind(']')
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]
    return raw


def _build_descriptions_prompt(req: DescriptionsRequest) -> str:
    """
    Build prompt asking Gemini to return ONLY a JSON array of strings (ad descriptions).
    """
    try:
        personas_json = json.dumps([p.dict() for p in req.selected_personas], indent=2)
    except Exception:
        personas_json = json.dumps(req.selected_personas, indent=2)

    main_goal_value = req.main_goal.value
    main_goal_desc = getattr(req.main_goal, "description", "")

    prompt = f"""
You are an expert ad copywriter specialized in short, high-converting ad descriptions for digital ads.

Task:
Produce exactly {req.num_descriptions} ad descriptions (each 1-2 short sentences) tailored to the business and the selected persona(s). RETURN ONLY a JSON array of strings (e.g. ["Desc 1", "Desc 2", ...]) and nothing else.

Requirements:
- Each description should be concise (max ~140 characters preferred), benefit-focused, and aligned with the business value and main goal.
- Vary tone across descriptions (e.g., urgent, aspirational, trust-building, practical).
- Include the main value or offer where appropriate (e.g., "MVP development", "AI integration", "fast time-to-market", "trusted SaaS partner").
- If the selected personas have different priorities, generate descriptions that address those priorities.
- Goal: "{main_goal_value}" — {main_goal_desc}

Business inputs:
- Business name: {req.business_name}
- Business category: {req.business_category}
- Business description: {req.business_description}
- Promotion type: {req.promotion_type}
- Offer description: {req.offer_description}
- Value proposition: {req.value}
- Main goal: {main_goal_value} — {main_goal_desc}
- Serving clients info: {req.serving_clients_info}
- Serving clients location: {req.serving_clients_location}

Selected persona(s) (use these to shape descriptions):
{personas_json}

Now generate exactly {req.num_descriptions} unique ad descriptions as a JSON array of strings. No explanation, no extra text.
"""
    logger.debug("Built descriptions prompt (len=%d) for business '%s'", len(prompt), req.business_name)
    return prompt.strip()


def generate_descriptions(req: DescriptionsRequest) -> List[str]:
    prompt = _build_descriptions_prompt(req)

    model_name = "gemini-2.5-pro"
    logger.info("Generating %d descriptions for business '%s' using model %s",
                req.num_descriptions, req.business_name, model_name)

    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        logger.exception("Failed to init Gemini model for descriptions: %s", e)
        raise RuntimeError(f"Gemini model init failed: {e}")

    try:
        start = time.perf_counter()
        response = model.generate_content(prompt)
        duration = time.perf_counter() - start
        logger.info("Gemini generate_content (descriptions) completed in %.2fs", duration)
    except Exception as e:
        logger.exception("Gemini generate_content failed for descriptions")
        raise RuntimeError(f"Gemini request failed: {e}")

    # extract raw text
    raw = None
    try:
        if response and hasattr(response, "text") and response.text:
            raw = response.text
            logger.debug("Received response.text (len=%d) for descriptions", len(raw))
        elif response and getattr(response, "candidates", None):
            first = response.candidates[0]
            if getattr(first, "finish_reason", "").upper() == "SAFETY":
                msg = "Gemini descriptions generation blocked by safety filter"
                logger.error(msg)
                raise RuntimeError(msg)
            raw = getattr(first, "content", None) or getattr(first, "text", None) or str(response)
            logger.debug("Received candidate response for descriptions (len=%d)", len(raw) if raw else 0)
        else:
            raw = str(response)
            logger.debug("Converted descriptions response to string (len=%d)", len(raw))
    except Exception as e:
        logger.exception("Failed to extract raw text from Gemini descriptions response")
        raise RuntimeError(f"Failed to extract Gemini response text: {e}")

    if not raw:
        logger.error("Empty response from Gemini when generating descriptions")
        raise RuntimeError("Empty response from Gemini")

    snippet = _extract_json_array(raw)
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        logger.exception("Failed to parse JSON from descriptions response. Raw response: %s", raw)
        raise RuntimeError(f"Failed to parse Gemini response as JSON array of strings.\nRaw: {raw}")

    if not isinstance(parsed, list) or not all(isinstance(i, str) for i in parsed):
        logger.error("Parsed descriptions JSON is not a list of strings. Parsed type: %s", type(parsed))
        raise RuntimeError("Gemini did not return a JSON array of strings as expected.")

    descriptions = parsed
    if len(descriptions) < req.num_descriptions:
        logger.warning("Gemini returned %d descriptions; expected %d. Returning what we have.",
                       len(descriptions), req.num_descriptions)
    elif len(descriptions) > req.num_descriptions:
        descriptions = descriptions[: req.num_descriptions]
        logger.debug("Trimmed descriptions to requested num_descriptions=%d", req.num_descriptions)

    descriptions = [d.strip() for d in descriptions]
    logger.info("Generated %d descriptions for business '%s'", len(descriptions), req.business_name)
    return descriptions
