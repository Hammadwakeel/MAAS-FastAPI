from fastapi import APIRouter, HTTPException
from app.keywords.model import BusinessDescription, KeywordsResponse
from app.keywords.keywords_service import generate_keywords_service

router = APIRouter(prefix="/keywords", tags=["keywords"])

@router.post("/generate", response_model=KeywordsResponse)
async def generate_keywords(business: BusinessDescription):
    try:
        response = generate_keywords_service(business)
        return response
    except Exception as e:
        # Log exception if you have logging set up
        raise HTTPException(status_code=500, detail=str(e))