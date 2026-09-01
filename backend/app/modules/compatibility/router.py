from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.compatibility import schemas, service

router = APIRouter(prefix="/compatibility", tags=["compatibility"])


@router.post("/check", response_model=schemas.CompatibilityCheckResponse)
def check_compatibility(
    payload: schemas.CompatibilityCheckRequest, db: Session = Depends(get_db)
) -> schemas.CompatibilityCheckResponse:
    return service.run_compatibility_check(db, payload)
