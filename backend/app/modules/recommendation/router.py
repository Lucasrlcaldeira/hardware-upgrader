from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.recommendation import schemas, service

router = APIRouter(prefix="/recommendation", tags=["recommendation"])


@router.post("/generate", response_model=schemas.RecommendationResponse)
def generate_recommendation(
    payload: schemas.RecommendationRequest, db: Session = Depends(get_db)
) -> schemas.RecommendationResponse:
    return service.generate_recommendations(db, payload)
