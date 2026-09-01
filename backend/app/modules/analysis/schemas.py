import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.modules.compatibility.schemas import BundleUpgrade, CompatibilityResult
from app.modules.performance.enums import GraphicsQuality, Resolution, WorkloadType
from app.modules.performance.schemas import BottleneckAnalysisResult
from app.modules.recommendation.enums import UpgradeProfile
from app.modules.recommendation.schemas import ComponentRecommendation, SystemSnapshot


class AnalysisRequest(BaseModel):
    system: SystemSnapshot
    profile: UpgradeProfile
    resolution: Resolution | None = None
    graphics_quality: GraphicsQuality | None = None
    target_fps: int | None = None
    workload_type: WorkloadType = WorkloadType.GAMING


class AnalysisReport(BaseModel):
    """Relatório de diagnóstico completo: visão geral, compatibilidade do sistema atual,
    gargalo e recomendações — a junção exigida pela etapa de relatório final do produto."""

    system: SystemSnapshot
    profile: UpgradeProfile
    current_compatibility: list[CompatibilityResult] = []
    bottleneck: BottleneckAnalysisResult | None = None
    bottleneck_note: str | None = None
    recommendations: list[ComponentRecommendation] = []
    bundle: BundleUpgrade | None = None
    summary: str


class AnalysisHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    profile: UpgradeProfile
    created_at: dt.datetime
    report: AnalysisReport
