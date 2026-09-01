import pytest

from app.core.exceptions import InsufficientDataError
from app.modules.catalog.models import CpuModel, GpuModel
from app.modules.performance.enums import (
    BottleneckVerdict,
    GraphicsQuality,
    Resolution,
    WorkloadType,
)
from app.modules.performance.schemas import BottleneckAnalysisRequest
from app.modules.performance.service import analyze_bottleneck


def _request(**overrides):
    defaults = dict(
        cpu_model_name="cpu",
        gpu_model_name="gpu",
        resolution=Resolution.R_1080P,
        graphics_quality=GraphicsQuality.MEDIUM,
    )
    defaults.update(overrides)
    return BottleneckAnalysisRequest(**defaults)


def test_raises_insufficient_data_when_cpu_tier_missing():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD", performance_tier=None)
    gpu = GpuModel(model_name="G", manufacturer="AMD", performance_tier=50)
    with pytest.raises(InsufficientDataError):
        analyze_bottleneck(cpu, gpu, _request())


def test_raises_insufficient_data_when_gpu_tier_missing():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD", performance_tier=50)
    gpu = GpuModel(model_name="G", manufacturer="AMD", performance_tier=None)
    with pytest.raises(InsufficientDataError):
        analyze_bottleneck(cpu, gpu, _request())


def test_weak_cpu_strong_gpu_at_low_resolution_is_cpu_bound():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD", performance_tier=15)
    gpu = GpuModel(model_name="G", manufacturer="AMD", performance_tier=80)
    result = analyze_bottleneck(
        cpu, gpu, _request(resolution=Resolution.R_1080P, graphics_quality=GraphicsQuality.LOW)
    )
    assert result.verdict == BottleneckVerdict.CPU_BOUND
    assert result.limiting_component == "cpu"


def test_strong_cpu_weak_gpu_at_4k_ultra_is_gpu_bound():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD", performance_tier=80)
    gpu = GpuModel(model_name="G", manufacturer="AMD", performance_tier=25)
    result = analyze_bottleneck(
        cpu, gpu, _request(resolution=Resolution.R_4K, graphics_quality=GraphicsQuality.ULTRA)
    )
    assert result.verdict == BottleneckVerdict.GPU_BOUND
    assert result.limiting_component == "gpu"


def test_similar_tiers_are_balanced():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD", performance_tier=50)
    gpu = GpuModel(model_name="G", manufacturer="AMD", performance_tier=50)
    result = analyze_bottleneck(cpu, gpu, _request())
    assert result.verdict == BottleneckVerdict.BALANCED
    assert result.limiting_component is None


def test_high_fps_target_pushes_toward_cpu_bound():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD", performance_tier=40)
    gpu = GpuModel(model_name="G", manufacturer="AMD", performance_tier=55)
    balanced = analyze_bottleneck(cpu, gpu, _request(target_fps=60))
    competitive = analyze_bottleneck(cpu, gpu, _request(target_fps=240))
    assert balanced.verdict == BottleneckVerdict.BALANCED
    assert competitive.verdict == BottleneckVerdict.CPU_BOUND


def test_content_creation_ignores_resolution_bias():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD", performance_tier=20)
    gpu = GpuModel(model_name="G", manufacturer="AMD", performance_tier=80)
    result = analyze_bottleneck(
        cpu,
        gpu,
        _request(
            workload_type=WorkloadType.CONTENT_CREATION,
            resolution=Resolution.R_4K,
            graphics_quality=GraphicsQuality.ULTRA,
        ),
    )
    assert result.verdict == BottleneckVerdict.CPU_BOUND
    assert "Carga de trabalho" in result.contributing_factors[0]
