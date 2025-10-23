# app/services/budget_service.py
import os
import json
import logging
import time
from typing import List

import google.generativeai as genai
from pydantic import ValidationError

from app.ads.schemas import BudgetRequest, BudgetPlan, BudgetType, GoalEnum

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Configure Gemini SDK (harmless if configured elsewhere)
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    logger.error("GEMINI_API_KEY not set; Gemini budget generation will fail if called without configuration.")
else:
    try:
        genai.configure(api_key=API_KEY)
        logger.debug("Configured google.generativeai in budget service")
    except Exception as e:
        logger.exception("Failed to configure google.generativeai in budget service: %s", e)


def _extract_json_array(raw: str) -> str:
    """
    Return the first JSON array substring from raw (from '[' to ']').
    Falls back to returning raw string when brackets are not found.
    """
    start = raw.find('[')
    end = raw.rfind(']')
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]
    return raw


def _build_budget_prompt(req: BudgetRequest) -> str:
    """
    Build a prompt that asks Gemini to produce TWO conservative, low-cost budget plan objects.
    NOTE: literal JSON braces in the example are escaped ({{ }}) because this is an f-string.
    """
    main_goal_value = req.main_goal.value
    main_goal_desc = getattr(req.main_goal, "description", "")

    try:
        personas_json = json.dumps([p.dict() for p in req.selected_personas], indent=2)
    except Exception:
        personas_json = json.dumps(req.selected_personas, indent=2)

    prompt = f"""
You are an experienced Facebook Ads strategist for B2B SaaS / AI services. Produce EXACTLY TWO budget plan objects as a JSON array and NOTHING ELSE.

Output rules (strict):
- Return ONLY a JSON array with two objects (no explanation, no metadata, no commentary).
- Objects must appear in this exact order:
   1) the DAILY plan (type = "daily")
   2) the LIFETIME plan (type = "lifetime")
- Each object must contain exactly these keys in this exact order:
   1. type (string)  — "daily" or "lifetime"
   2. budget (string) — for "daily" use "$XX/day"; for "lifetime" use "$YYY total"
   3. duration (string) — integer days, formatted like "14 days"
- Do NOT add, omit or rename keys. Do NOT include numbers with commas (use plain digits).
- Use whole-dollar amounts unless cents are strictly needed.

Business context (use this to pick realistic numbers):
- Business name: {req.business_name}
- Category: {req.business_category}
- Description: {req.business_description}
- Promotion type: {req.promotion_type}
- Offer: {req.offer_description}
- Value: {req.value}
- Main goal: {main_goal_value} — {main_goal_desc}
- Serving clients: {req.serving_clients_info}
- Locations: {req.serving_clients_location}

Persona context:
{personas_json}

Cost-savings / "less expensive" constraints (MUST follow):
- This is for a new or low-data business. Prioritize conservative, budget-friendly plans.
- DAILY plan (short test):
    • Duration: choose between 7 and 14 days.
    • Daily budget: choose between $10/day and $30/day (prefer values at or below $20/day for new accounts).
- LIFETIME plan (scaling/run):
    • Duration: choose between 15 and 60 days.
    • Lifetime budget: choose between $300 total and $1200 total.
    • Lifetime total must be consistent with a daily-equivalent that does NOT exceed $30/day.
- Do NOT propose daily budgets above $30/day or lifetime totals above $1200.
- Prefer round, whole-dollar amounts and conservative choices when in doubt.

Formatting example (escaped so this f-string compiles):
[
  {{ "type":"daily","budget":"$15/day","duration":"10 days" }},
  {{ "type":"lifetime","budget":"$600 total","duration":"30 days" }}
]

Now generate the two-budget JSON array that strictly follows the rules above.
"""
    logger.debug("Built conservative/low-cost budget prompt for business '%s' (len=%d)", req.business_name, len(prompt))
    return prompt.strip()

def generate_budget_plans(req: BudgetRequest) -> List[BudgetPlan]:
    """
    Call Gemini to generate two budget plans, parse and validate them into BudgetPlan objects.
    Returns a list of two BudgetPlan instances.
    """
    prompt = _build_budget_prompt(req)

    model_name = "gemini-2.5-pro"
    logger.info("Generating budget plans for business '%s' using model %s", req.business_name, model_name)

    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        logger.exception("Failed to create GenerativeModel: %s", e)
        raise RuntimeError(f"Gemini model init failed: {e}")

    try:
        start = time.perf_counter()
        response = model.generate_content(prompt)
        duration = time.perf_counter() - start
        logger.info("Gemini generate_content (budgets) completed in %.2fs", duration)
    except Exception as e:
        logger.exception("Gemini generate_content failed for budgets")
        raise RuntimeError(f"Gemini request failed: {e}")

    # Extract raw text from response
    raw = None
    try:
        if response and hasattr(response, "text") and response.text:
            raw = response.text
            logger.debug("Received response.text (len=%d) for budgets", len(raw))
        elif response and getattr(response, "candidates", None):
            first = response.candidates[0]
            # check safety block
            if getattr(first, "finish_reason", "").upper() == "SAFETY":
                msg = "Gemini budget generation blocked by safety filter"
                logger.error(msg)
                raise RuntimeError(msg)
            # try to find textual content inside candidate
            content = getattr(first, "content", None)
            if content:
                # content.parts may exist
                parts = getattr(content, "parts", None) or []
                texts = []
                for part in parts:
                    t = getattr(part, "text", None)
                    if t:
                        texts.append(t)
                raw = "\n\n".join(texts) if texts else str(first)
            else:
                raw = getattr(first, "text", None) or str(response)
            logger.debug("Received candidate-based response for budgets (len=%d)", len(raw) if raw else 0)
        else:
            raw = str(response)
            logger.debug("Converted budgets response to string (len=%d)", len(raw))
    except Exception as e:
        logger.exception("Failed to extract raw text from Gemini budgets response")
        raise RuntimeError(f"Failed to extract Gemini response text: {e}")

    if not raw:
        logger.error("Empty response from Gemini when generating budgets")
        raise RuntimeError("Empty response from Gemini")

    # Robust JSON extraction & parsing
    snippet = _extract_json_array(raw)
    try:
        parsed = json.loads(snippet)
        # If model wrapped array inside object keys, find it
        if isinstance(parsed, dict):
            for key in ("items", "plans", "data", "results"):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
    except json.JSONDecodeError:
        logger.exception("Failed to parse JSON from budgets response. Raw response: %s", raw)
        raise RuntimeError(f"Failed to parse Gemini response as JSON array of budget objects.\nRaw: {raw}")

    # Validate structure
    if not isinstance(parsed, list):
        logger.error("Parsed budgets JSON is not a list. Parsed type: %s", type(parsed))
        raise RuntimeError("Gemini did not return a JSON array as expected for budgets.")

    # Optionally trim or require exactly 2 objects
    if len(parsed) < 2:
        logger.warning("Gemini returned fewer than 2 budget objects (%d).", len(parsed))
    # Attempt to convert each into BudgetPlan
    plans: List[BudgetPlan] = []
    for idx, obj in enumerate(parsed[:2]):  # only parse up to 2 objects
        try:
            plan = BudgetPlan.parse_obj(obj)
            # Ensure type is one of enums by casting/validating
            if plan.type not in (BudgetType.daily, BudgetType.lifetime):
                logger.debug("Plan %d has non-standard type '%s' — attempting to normalize", idx, plan.type)
                # try to normalize common variants
                t_lower = str(plan.type).lower()
                if "daily" in t_lower:
                    plan.type = BudgetType.daily
                elif "life" in t_lower or "lifetime" in t_lower:
                    plan.type = BudgetType.lifetime
                else:
                    # last resort: set daily for first and lifetime for second based on index
                    plan.type = BudgetType.daily if idx == 0 else BudgetType.lifetime
            plans.append(plan)
        except ValidationError as ve:
            logger.error("BudgetPlan validation failed for item %s: %s\nRaw item: %s", idx, ve, obj)
            raise RuntimeError(f"Failed to validate budget plan item {idx}: {ve}")

    if not plans:
        logger.error("No valid budget plans parsed from Gemini response. Raw: %s", raw)
        raise RuntimeError("No valid budget plans parsed from Gemini response.")

    logger.info("Successfully generated %d budget plan(s) for business '%s'", len(plans), req.business_name)
    return plans
