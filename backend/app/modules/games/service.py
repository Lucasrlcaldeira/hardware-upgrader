from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientDataError, NotFoundError
from app.modules.catalog import service as catalog_service
from app.modules.games import models
from app.modules.games.schemas import GameFpsRequest, GameFpsResult

# Mesmo limiar de diferença de performance_tier usado pelo motor de gargalo (performance
# module) para considerar um lado "à frente" do outro — reaproveitado aqui só para decidir
# se vale a pena mostrar o aviso qualitativo de possível limitação por CPU.
_TIER_GAP_THRESHOLD = 15


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

    benchmark = db.scalar(
        select(models.GameBenchmark).where(
            models.GameBenchmark.game_id == game.id,
            models.GameBenchmark.gpu_id == gpu.id,
            models.GameBenchmark.resolution == request.resolution.value,
        )
    )
    if benchmark is None:
        raise InsufficientDataError(
            f"Dado insuficiente para determinar o FPS: não há benchmark real cadastrado "
            f"para '{game.title}' com a GPU '{gpu.model_name}' em {request.resolution.value}."
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
        cpu_bottleneck_caveat=_cpu_bottleneck_caveat(db, request.cpu_model_name, gpu),
    )
