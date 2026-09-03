from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientDataError, NotFoundError
from app.modules.catalog import models as catalog_models
from app.modules.catalog import service as catalog_service
from app.modules.games import models
from app.modules.games.schemas import GameFpsRequest, GameFpsResult

# Mesmo limiar de diferença de performance_tier usado pelo motor de gargalo (performance
# module) para considerar um lado "à frente" do outro — reaproveitado aqui só para decidir
# se vale a pena mostrar o aviso qualitativo de possível limitação por CPU.
_TIER_GAP_THRESHOLD = 15

# Limiar de diferença de performance_tier para aceitar o benchmark de outra GPU como
# aproximação quando a GPU pedida não tem dado próprio — mesmo valor do limiar acima, mas é
# uma decisão de produto separada (o que conta como "próxima o suficiente pra mostrar"), não
# a mesma pergunta que _TIER_GAP_THRESHOLD responde.
_FALLBACK_TIER_GAP_THRESHOLD = 15


def get_game_by_title(db: Session, title: str) -> models.Game | None:
    return db.scalar(select(models.Game).where(models.Game.title.ilike(title)))


def list_game_titles(db: Session) -> list[str]:
    return list(db.scalars(select(models.Game.title).order_by(models.Game.title)).all())


def _cpu_bottleneck_caveat(db: Session, cpu_model_name: str | None, gpu) -> str | None:
    if not cpu_model_name:
        return None
    cpu = catalog_service.get_cpu_by_model_name(db, cpu_model_name)
    if cpu is None or cpu.performance_tier is None or gpu.performance_tier is None:
        return None

    tier_gap = gpu.performance_tier - cpu.performance_tier
    if tier_gap <= _TIER_GAP_THRESHOLD:
        return None

    # O número de FPS abaixo é dado real medido pela fonte citada — nunca ajustado por esta
    # comparação. Isso só adiciona um aviso qualitativo, no mesmo espírito do motor de
    # gargalo: nunca inventamos um número ajustado para uma combinação CPU/GPU não testada.
    return (
        "Sua CPU tem desempenho relativo bem abaixo dessa GPU — ela pode ser o fator "
        "limitante nesta configuração, então o FPS real pode ficar abaixo do valor medido "
        "abaixo (que reflete o teto de desempenho da própria GPU, testada com uma CPU mais "
        "forte que a sua)."
    )


def _benchmark_for_gpu(
    db: Session, game_id: int, resolution: str, gpu: catalog_models.GpuModel
) -> models.GameBenchmark | None:
    return db.scalar(
        select(models.GameBenchmark).where(
            models.GameBenchmark.game_id == game_id,
            models.GameBenchmark.gpu_id == gpu.id,
            models.GameBenchmark.resolution == resolution,
        )
    )


def _closest_benchmarked_gpu(
    db: Session, game_id: int, resolution: str, target_gpu: catalog_models.GpuModel
) -> tuple[catalog_models.GpuModel, models.GameBenchmark] | tuple[None, None]:
    """Entre as GPUs com benchmark real cadastrado pra esse jogo/resolução, acha a de
    performance_tier mais próximo da GPU pedida — pra usar como aproximação transparente
    quando a GPU exata não tem dado. Nunca calcula um FPS novo: sempre reaproveita um número
    real medido, só troca qual GPU esse número descreve.
    """
    if target_gpu.performance_tier is None:
        return None, None

    candidates = db.execute(
        select(models.GameBenchmark, catalog_models.GpuModel)
        .join(catalog_models.GpuModel, catalog_models.GpuModel.id == models.GameBenchmark.gpu_id)
        .where(
            models.GameBenchmark.game_id == game_id,
            models.GameBenchmark.resolution == resolution,
            catalog_models.GpuModel.performance_tier.is_not(None),
        )
    ).all()

    best: tuple[int, models.GameBenchmark, catalog_models.GpuModel] | None = None
    for benchmark, gpu in candidates:
        gap = abs(gpu.performance_tier - target_gpu.performance_tier)
        if gap > _FALLBACK_TIER_GAP_THRESHOLD:
            continue
        if best is None or gap < best[0]:
            best = (gap, benchmark, gpu)

    if best is None:
        return None, None
    return best[2], best[1]


def get_fps_estimate(db: Session, request: GameFpsRequest) -> GameFpsResult:
    game = get_game_by_title(db, request.game_title)
    if game is None:
        raise NotFoundError(
            f"Jogo '{request.game_title}' não encontrado na base de benchmarks — só "
            "retornamos FPS para jogos com dado real cadastrado, nunca uma estimativa "
            "inventada."
        )

    gpu = catalog_service.get_gpu_by_model_name(db, request.gpu_model_name)
    if gpu is None:
        raise NotFoundError(f"GPU '{request.gpu_model_name}' não encontrada no catálogo.")

    resolution = request.resolution.value
    benchmark = _benchmark_for_gpu(db, game.id, resolution, gpu)
    benchmarked_gpu = gpu
    approximation_note = None

    if benchmark is None:
        substitute_gpu, substitute_benchmark = _closest_benchmarked_gpu(
            db, game.id, resolution, gpu
        )
        if substitute_benchmark is not None:
            benchmark = substitute_benchmark
            benchmarked_gpu = substitute_gpu
            approximation_note = (
                f"Não há benchmark real cadastrado para a '{gpu.model_name}' neste jogo/"
                f"resolução. O valor abaixo é um dado real medido com a '{substitute_gpu.model_name}'"
                ", a GPU de desempenho mais próximo entre as que têm benchmark cadastrado — "
                "não é um número calculado para a sua GPU, é o resultado medido para essa outra "
                "placa."
            )

    if benchmark is None:
        raise InsufficientDataError(
            f"Dado insuficiente para determinar o FPS: não há benchmark real cadastrado "
            f"para '{game.title}' com a GPU '{gpu.model_name}' (nem com uma GPU de desempenho "
            f"próximo) em {resolution}."
        )

    return GameFpsResult(
        game_title=game.title,
        gpu_model_name=gpu.model_name,
        resolution=request.resolution,
        avg_fps=benchmark.avg_fps,
        test_cpu_model=benchmark.test_cpu_model,
        source_name=benchmark.source_name,
        source_url=benchmark.source_url,
        quality_preset_note=benchmark.quality_preset_note,
        cpu_bottleneck_caveat=_cpu_bottleneck_caveat(db, request.cpu_model_name, benchmarked_gpu),
        approximation_note=approximation_note,
    )
