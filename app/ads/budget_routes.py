# app/routes/budget_routes.py
import logging
from fastapi import APIRouter, HTTPException
from typing import List

from app.ads.schemas import BudgetRequest, BudgetPlan
from app.ads.budget_service import generate_budget_plans

router = APIRouter(prefix="/Ads", tags=["Ads"])
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@router.post("/price", response_model=List[BudgetPlan])
def create_budget_options(payload: BudgetRequest):
    """
    Generate two budget options (daily & lifetime) for ad campaigns based on business inputs.
    Returns a list of two objects:
      [
        {"type":"daily","budget":"25$/day","duration":"7 days"},
        {"type":"lifetime","budget":"15$/day","duration":"62 days"}
      ]
    """
    try:
        plans = generate_budget_plans(payload)
        return plans
    except Exception as e:
        logger.exception("Failed to generate budget plans: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
