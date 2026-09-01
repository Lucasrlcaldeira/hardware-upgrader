from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.performance import schemas, service

router = APIRouter(prefix="/performance", tags=["performance"])


@router.post("/bottleneck", response_model=schemas.BottleneckAnalysisResult)
def check_bottleneck(
    payload: schemas.BottleneckAnalysisRequest, db: Session = Depends(get_db)
) -> schemas.BottleneckAnalysisResult:
    return service.run_bottleneck_analysis(db, payload)
