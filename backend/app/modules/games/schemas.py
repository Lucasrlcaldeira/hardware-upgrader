from pydantic import BaseModel, Field

from app.modules.detection.schemas import HardwareSnapshotBase
from app.modules.games.enums import CheckStatus, GameVerdict, RequirementComponent, RequirementTier
from app.modules.recommendation.schemas import SystemSnapshot


class SteamGameSummary(BaseModel):
    app_id: int
    name: str
    image_url: str | None = None


class GameRequirementsCheckRequest(BaseModel):
    """`system` traz as peças escolhidas no catálogo (têm prioridade, são o que o usuário
    confirmou); `detected` traz o que o Windows detectou, usado para o que não está no
    catálogo (ex: uma CPU antiga) e para dados que só a detecção tem (RAM total, espaço
    livre, sistema operacional)."""

    app_id: int
    system: SystemSnapshot = Field(default_factory=SystemSnapshot)
    detected: HardwareSnapshotBase | None = None
    # Mesmo PC com os upgrades recomendados aplicados — permite responder "e se eu trocar
    # a placa de vídeo, passo a rodar no recomendado?".
    upgraded_system: SystemSnapshot | None = None


class RequirementLineRead(BaseModel):
    label: str
    value: str


class RequirementCheck(BaseModel):
    component: RequirementComponent
    required: str
    yours: str | None = None
    status: CheckStatus
    explanation: str
    # Armazenamento e sistema operacional aparecem como aviso, mas não decidem se o jogo
    # "roda": falta de espaço se resolve liberando disco, e não com upgrade de peça.
    counts_for_verdict: bool = True


class TierEvaluation(BaseModel):
    tier: RequirementTier
    status: CheckStatus
    checks: list[RequirementCheck]


class SystemEvaluation(BaseModel):
    verdict: GameVerdict
    verdict_text: str
    minimum: TierEvaluation | None = None
    recommended: TierEvaluation | None = None


class GameRequirementsCheckResult(BaseModel):
    app_id: int
    name: str
    store_url: str
    header_image: str | None = None
    minimum_requirements: list[RequirementLineRead] = []
    recommended_requirements: list[RequirementLineRead] = []
    current: SystemEvaluation
    upgraded: SystemEvaluation | None = None
    disclaimer: str
