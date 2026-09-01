from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientDataError, NotFoundError
from app.modules.catalog import models as catalog_models
from app.modules.catalog import service as catalog_service
from app.modules.performance.enums import (
    BottleneckVerdict,
    ConfidenceLevel,
    GraphicsQuality,
    Resolution,
    WorkloadType,
)
from app.modules.performance.schemas import BottleneckAnalysisRequest, BottleneckAnalysisResult

# Quanto maior a resolução/qualidade gráfica, mais cedo a GPU vira o fator limitante — então
# aumentamos o quanto a GPU "precisa estar à frente" da CPU antes de considerarmos CPU-bound.
_RESOLUTION_BIAS = {Resolution.R_1080P: 0, Resolution.R_1440P: 8, Resolution.R_4K: 16}
_QUALITY_BIAS = {
    GraphicsQuality.LOW: 0,
    GraphicsQuality.MEDIUM: 4,
    GraphicsQuality.HIGH: 8,
    GraphicsQuality.ULTRA: 12,
}
_HIGH_FPS_TARGET = 144
_HIGH_FPS_BIAS = -10  # metas de FPS muito altas cobram mais da CPU (mais frames/s a preparar)
_GAP_THRESHOLD = 15  # limiar mínimo de diferença relativa para considerar um lado "limitante"


def analyze_bottleneck(
    cpu: catalog_models.CpuModel,
    gpu: catalog_models.GpuModel,
    request: BottleneckAnalysisRequest,
) -> BottleneckAnalysisResult:
    if cpu.performance_tier is None or gpu.performance_tier is None:
        raise InsufficientDataError(
            "Dado insuficiente para determinar gargalo: o catálogo não tem um nível de "
            "desempenho relativo (performance_tier) cadastrado para a CPU e/ou a GPU "
            "informadas."
        )

    # tier_gap > 0 => GPU está à frente da CPU na escala relativa do catálogo (e vice-versa).
    # Essa escala é ordinal/curada, não um benchmark real — nunca é exposta ao usuário.
    tier_gap = gpu.performance_tier - cpu.performance_tier

    if request.workload_type in (WorkloadType.PRODUCTIVITY, WorkloadType.CONTENT_CREATION):
        return _analyze_non_gaming_workload(tier_gap, request)
    return _analyze_gaming_workload(tier_gap, request)


def _analyze_non_gaming_workload(
    tier_gap: int, request: BottleneckAnalysisRequest
) -> BottleneckAnalysisResult:
    factors = [
        f"Carga de trabalho '{request.workload_type.value}' depende primariamente de CPU "
        "(e RAM) — a GPU tende a influenciar menos o desempenho percebido nesse cenário, "
        "exceto em tarefas específicas com aceleração por GPU."
    ]

    if tier_gap > _GAP_THRESHOLD:
        return BottleneckAnalysisResult(
            verdict=BottleneckVerdict.CPU_BOUND,
            limiting_component="cpu",
            explanation=(
                "Sua GPU está bem à frente da sua CPU na escala relativa do catálogo, e "
                "para este tipo de carga é a CPU que tende a limitar o desempenho primeiro."
            ),
            contributing_factors=factors,
            confidence=ConfidenceLevel.MEDIA,
        )

    return BottleneckAnalysisResult(
        verdict=BottleneckVerdict.BALANCED,
        limiting_component=None,
        explanation=(
            "CPU e GPU parecem razoavelmente equilibradas para este tipo de carga, mas "
            "lembre-se que produtividade e criação de conteúdo dependem mais de CPU e RAM "
            "do que de GPU na maioria dos casos."
        ),
        contributing_factors=factors,
        confidence=ConfidenceLevel.BAIXA,
    )


def _analyze_gaming_workload(
    tier_gap: int, request: BottleneckAnalysisRequest
) -> BottleneckAnalysisResult:
    resolution_bias = _RESOLUTION_BIAS[request.resolution]
    quality_bias = _QUALITY_BIAS[request.graphics_quality]
    fps_bias = _HIGH_FPS_BIAS if (request.target_fps or 0) >= _HIGH_FPS_TARGET else 0

    adjusted_gap = tier_gap - resolution_bias - quality_bias - fps_bias

    factors = [
        f"Resolução alvo: {request.resolution.value}",
        f"Qualidade gráfica: {request.graphics_quality.value}",
    ]
    if request.target_fps:
        factors.append(f"Meta de FPS: {request.target_fps}")

    if adjusted_gap > _GAP_THRESHOLD:
        return BottleneckAnalysisResult(
            verdict=BottleneckVerdict.CPU_BOUND,
            limiting_component="cpu",
            explanation=(
                "Sua GPU tem folga de desempenho relativo em relação à sua CPU nesta "
                "configuração — em cenários com forte dependência de CPU (jogos "
                "competitivos, simulações com muitas entidades, ou metas de FPS muito "
                "altas), a CPU tende a limitar a taxa de quadros antes da GPU."
            ),
            contributing_factors=factors,
            confidence=ConfidenceLevel.MEDIA,
        )

    if adjusted_gap < -_GAP_THRESHOLD:
        return BottleneckAnalysisResult(
            verdict=BottleneckVerdict.GPU_BOUND,
            limiting_component="gpu",
            explanation=(
                "Sua CPU tem folga de desempenho relativo em relação à sua GPU nesta "
                "configuração — nessa resolução/qualidade gráfica, a GPU tende a ser o "
                "fator limitante antes da CPU, o que é o cenário mais comum em resoluções "
                "mais altas."
            ),
            contributing_factors=factors,
            confidence=ConfidenceLevel.MEDIA,
        )

    return BottleneckAnalysisResult(
        verdict=BottleneckVerdict.BALANCED,
        limiting_component=None,
        explanation=(
            "CPU e GPU parecem razoavelmente equilibradas para esta resolução e qualidade "
            "gráfica — nenhum dos dois componentes deve limitar o outro de forma "
            "significativa na maioria dos cenários."
        ),
        contributing_factors=factors,
        confidence=ConfidenceLevel.BAIXA,
    )


def run_bottleneck_analysis(
    db: Session, request: BottleneckAnalysisRequest
) -> BottleneckAnalysisResult:
    cpu = catalog_service.get_cpu_by_model_name(db, request.cpu_model_name)
    if cpu is None:
        raise NotFoundError(f"CPU '{request.cpu_model_name}' não encontrada no catálogo.")

    gpu = catalog_service.get_gpu_by_model_name(db, request.gpu_model_name)
    if gpu is None:
        raise NotFoundError(f"GPU '{request.gpu_model_name}' não encontrada no catálogo.")

    return analyze_bottleneck(cpu, gpu, request)
