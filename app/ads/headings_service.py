# app/services/headings_service.py
import os
import json
import logging
import time
from typing import List

import google.generativeai as genai

from app.ads.schemas import HeadingsRequest, Persona

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Ensure Gemini SDK is configured (harmless if already configured elsewhere)
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logger.error("GEMINI_API_KEY not set; headings generation will fail if called without configuration.")
else:
    try:
        genai.configure(api_key=API_KEY)
        logger.debug("Configured google.generativeai in headings service")
    except Exception as e:
        logger.exception("Failed to configure google.generativeai in headings service: %s", e)


def _extract_json_array(raw: str) -> str:
    """
    Return the first JSON array substring from raw (from '[' to ']') to be robust
    against extra commentary in model output.
    """
    start = raw.find('[')
    end = raw.rfind(']')
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]
    return raw


def _build_headings_prompt(req: HeadingsRequest) -> str:
    """
    Build a clear prompt asking Gemini to return ONLY a JSON array of strings (headings).
    """
    # Convert selected_personas to compact JSON for context
    personas_json = json.dumps([p.dict() for p in req.selected_personas], indent=2)

    main_goal_value = req.main_goal.value
    main_goal_desc = getattr(req.main_goal, "description", "")

    prompt = f"""
You are an expert copywriter specialized in short, high-converting ad headlines for digital ads.

Task:
Produce exactly {req.num_headings} short, punchy ad headings (strings) for a paid ad campaign that target the selected personas and align with the business goal. RETURN ONLY a JSON array of strings (e.g. ["Heading 1", "Heading 2", ...]) and nothing else.

Requirements:
- Each heading should be concise (max ~60 characters), benefit-focused, and tailored to the provided personas and business goal.
- Use active language and mention the key value when appropriate (e.g., "scale", "AI", "launch", "MVP", "secure funding", "reduce time-to-market").
- Vary the tone across the 4 headings (e.g., urgent, aspirational, trust-building, and practical).
- Avoid punctuation-only headlines, and do not include numbering in text.
- If the main goal is "{main_goal_value}", use that intention as a primary framing. Goal description: {main_goal_desc}

Business Inputs:
- Business name: {req.business_name}
- Business category: {req.business_category}
- Business description: {req.business_description}
- Promotion type: {req.promotion_type}
- Offer description: {req.offer_description}
- Value proposition: {req.value}
- Main goal: {main_goal_value} — {main_goal_desc}
- Serving clients info: {req.serving_clients_info}
- Serving clients location: {req.serving_clients_location}

Selected persona(s) (use these to shape headings):
{personas_json}

Now generate exactly {req.num_headings} unique ad headings as a JSON array of strings. No explanation, no extra text.
"""
    logger.debug("Built headings prompt (len=%d) for business '%s'", len(prompt), req.business_name)
    return prompt.strip()


def generate_headings(req: HeadingsRequest) -> List[str]:
    """
    Call Gemini to generate ad headings and return list[str].
    """
    prompt = _build_headings_prompt(req)

    model_name = "gemini-2.5-pro"
    logger.info("Generating %d headings for business '%s' using model %s",
                req.num_headings, req.business_name, model_name)

    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        logger.exception("Failed to create GenerativeModel: %s", e)
        raise RuntimeError(f"Gemini model init failed: {e}")

    try:
        start = time.perf_counter()
        response = model.generate_content(prompt)
        duration = time.perf_counter() - start
        logger.info("Gemini generate_content (headings) completed in %.2fs", duration)
    except Exception as e:
        logger.exception("Gemini generate_content failed for headings")
        raise RuntimeError(f"Gemini request failed: {e}")

    # Extract raw text from response
    raw = None
    try:
        if response and hasattr(response, "text") and response.text:
            raw = response.text
            logger.debug("Received response.text (len=%d) for headings", len(raw))
        elif response and getattr(response, "candidates", None):
            first = response.candidates[0]
            if getattr(first, "finish_reason", "").upper() == "SAFETY":
                msg = "Gemini headings generation blocked by safety filter"
                logger.error(msg)
                raise RuntimeError(msg)
            raw = getattr(first, "content", None) or getattr(first, "text", None) or str(response)
            logger.debug("Received candidate response for headings (len=%d)", len(raw) if raw else 0)
        else:
            raw = str(response)
            logger.debug("Converted headings response to string (len=%d)", len(raw))
    except Exception as e:
        logger.exception("Failed to extract raw text from Gemini headings response")
        raise RuntimeError(f"Failed to extract Gemini response text: {e}")

    if not raw:
        logger.error("Empty response from Gemini when generating headings")
        raise RuntimeError("Empty response from Gemini")

    # Robust JSON extraction & parsing
    snippet = _extract_json_array(raw)
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        logger.exception("Failed to parse JSON from headings response. Raw response: %s", raw)
        raise RuntimeError(f"Failed to parse Gemini response as JSON array of strings.\nRaw: {raw}")

    if not isinstance(parsed, list) or not all(isinstance(i, str) for i in parsed):
        logger.error("Parsed headings JSON is not a list of strings. Parsed type: %s", type(parsed))
        raise RuntimeError("Gemini did not return a JSON array of strings as expected.")

    # Normalize: ensure exactly num_headings items
    headings = parsed
    if len(headings) < req.num_headings:
        logger.warning("Gemini returned %d headings; expected %d. Returning what we have.",
                       len(headings), req.num_headings)
    elif len(headings) > req.num_headings:
        headings = headings[: req.num_headings]
        logger.debug("Trimmed headings to requested num_headings=%d", req.num_headings)

    # Final basic cleanup (strip whitespace)
    headings = [h.strip() for h in headings]

    logger.info("Generated %d headings for business '%s'", len(headings), req.business_name)
    return headings
