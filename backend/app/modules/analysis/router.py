from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.analysis import schemas, service
from app.modules.users.models import User
from app.modules.users.router import get_current_user

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/run", response_model=schemas.AnalysisHistoryRead)
def run_analysis(
    payload: schemas.AnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.run_analysis(db, current_user, payload)


@router.get("/history", response_model=list[schemas.AnalysisHistoryRead])
def get_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return service.list_history(db, current_user)


@router.get("/history/{history_id}", response_model=schemas.AnalysisHistoryRead)
def get_history_entry(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_history_entry(db, current_user, history_id)
