from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.games import schemas, service

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/", response_model=list[str])
def list_games(db: Session = Depends(get_db)):
    """Jogos com dado de benchmark real cadastrado — para autocomplete no frontend."""
    return service.list_game_titles(db)


@router.post("/fps-estimate", response_model=schemas.GameFpsResult)
def get_fps_estimate(payload: schemas.GameFpsRequest, db: Session = Depends(get_db)):
    return service.get_fps_estimate(db, payload)
