from pydantic import BaseModel

from app.modules.performance.enums import (
    BottleneckVerdict,
    ConfidenceLevel,
    GraphicsQuality,
    Resolution,
    WorkloadType,
)


class BottleneckAnalysisRequest(BaseModel):
    cpu_model_name: str
    gpu_model_name: str
    resolution: Resolution
    graphics_quality: GraphicsQuality
    target_fps: int | None = None
    workload_type: WorkloadType = WorkloadType.GAMING


class BottleneckAnalysisResult(BaseModel):
    verdict: BottleneckVerdict
    limiting_component: str | None = None
    explanation: str
    contributing_factors: list[str] = []
    confidence: ConfidenceLevel
