from pydantic import BaseModel

from app.modules.performance.enums import Resolution


class GameFpsRequest(BaseModel):
    game_title: str
    gpu_model_name: str
    cpu_model_name: str | None = None
    resolution: Resolution = Resolution.R_1080P


class GameFpsResult(BaseModel):
    game_title: str
    gpu_model_name: str
    resolution: Resolution
    avg_fps: int
    test_cpu_model: str
    source_name: str
    source_url: str
    quality_preset_note: str
    cpu_bottleneck_caveat: str | None = None
