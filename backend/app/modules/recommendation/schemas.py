from pydantic import BaseModel

from app.modules.compatibility.enums import CompatibilityStatus
from app.modules.compatibility.schemas import BundleUpgrade
from app.modules.performance.enums import GraphicsQuality, Resolution, WorkloadType
from app.modules.performance.schemas import BottleneckAnalysisResult
from app.modules.recommendation.enums import ComponentSlot, RecommendationPriority, UpgradeProfile


class SystemSnapshot(BaseModel):
    """model_name (do catálogo) de cada componente atual do usuário.

    Mesma convenção de `CompatibilityCheckRequest`: campos omitidos apenas
    pulam as análises que dependeriam deles.
    """

    cpu_model_name: str | None = None
    gpu_model_name: str | None = None
    motherboard_model_name: str | None = None
    ram_model_name: str | None = None
    storage_model_name: str | None = None
    psu_model_name: str | None = None
    case_model_name: str | None = None
    cooler_model_name: str | None = None


class RecommendationRequest(BaseModel):
    system: SystemSnapshot
    profile: UpgradeProfile
    resolution: Resolution | None = None
    graphics_quality: GraphicsQuality | None = None
    target_fps: int | None = None
    workload_type: WorkloadType = WorkloadType.GAMING


class ComponentRecommendation(BaseModel):
    slot: ComponentSlot
    current_model_name: str | None = None
    problem: str
    recommended_model_name: str
    expected_gain: str
    compatibility_status: CompatibilityStatus
    additional_required_components: list[ComponentSlot] = []
    remaining_limitations: list[str] = []
    priority: RecommendationPriority
    cost_benefit: str


class RecommendationResponse(BaseModel):
    profile: UpgradeProfile
    bottleneck: BottleneckAnalysisResult | None = None
    bottleneck_note: str | None = None
    recommendations: list[ComponentRecommendation] = []
    bundle: BundleUpgrade | None = None
    summary: str
