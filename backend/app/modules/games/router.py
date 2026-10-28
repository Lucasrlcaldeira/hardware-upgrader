from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.games import schemas, service
from app.modules.games.steam_client import SteamStoreClient, get_steam_client

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/search", response_model=list[schemas.SteamGameSummary])
def search_games(
    q: str = Query(min_length=2, max_length=200),
    steam: SteamStoreClient = Depends(get_steam_client),
):
    """Busca jogos na loja da Steam por nome (aceita também o link da loja ou o ID do app)."""
    return service.search_games(steam, q)


@router.post("/requirements-check", response_model=schemas.GameRequirementsCheckResult)
def check_requirements(
    payload: schemas.GameRequirementsCheckRequest,
    db: Session = Depends(get_db),
    steam: SteamStoreClient = Depends(get_steam_client),
):
    """Compara o PC do usuário com os requisitos mínimos e recomendados publicados na Steam."""
    return service.check_requirements(db, steam, payload)
