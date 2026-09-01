"""Carrega o dataset curado de jogos + benchmarks reais (JSON nesta pasta) no banco.

Cada linha de benchmarks.json tem uma fonte real e citável (ver source_url) — nunca um
número calculado pelo sistema. Idempotente: roda upsert por título/GPU/resolução.

Uso:
    backend/.venv/Scripts/python -m app.modules.games.seed.load_seed
"""

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.catalog import service as catalog_service
from app.modules.games import models

logger = logging.getLogger(__name__)
SEED_DIR = Path(__file__).parent


def _load_json(filename: str) -> list[dict]:
    with open(SEED_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def _upsert_game(db: Session, title: str, notes: str | None) -> models.Game:
    existing = db.scalar(select(models.Game).where(models.Game.title == title))
    if existing:
        existing.notes = notes
        return existing
    game = models.Game(title=title, notes=notes)
    db.add(game)
    db.flush()
    return game


def run(db: Session | None = None) -> None:
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        games_by_title: dict[str, models.Game] = {}
        for raw in _load_json("games.json"):
            game = _upsert_game(db, raw["title"], raw.get("notes"))
            games_by_title[raw["title"]] = game
        db.flush()

        for raw in _load_json("benchmarks.json"):
            benchmark_game = games_by_title.get(raw["game_title"])
            if benchmark_game is None:
                logger.warning(
                    "Benchmark ignorado: jogo '%s' não está em games.json.", raw["game_title"]
                )
                continue
            gpu = catalog_service.get_gpu_by_model_name(db, raw["gpu_model_name"])
            if gpu is None:
                logger.warning(
                    "Benchmark ignorado: GPU '%s' não encontrada no catálogo.",
                    raw["gpu_model_name"],
                )
                continue

            existing = db.scalar(
                select(models.GameBenchmark).where(
                    models.GameBenchmark.game_id == benchmark_game.id,
                    models.GameBenchmark.gpu_id == gpu.id,
                    models.GameBenchmark.resolution == raw["resolution"],
                )
            )
            fields = {
                "avg_fps": raw["avg_fps"],
                "test_cpu_model": raw["test_cpu_model"],
                "quality_preset_note": raw["quality_preset_note"],
                "source_name": raw["source_name"],
                "source_url": raw["source_url"],
            }
            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
            else:
                db.add(
                    models.GameBenchmark(
                        game_id=benchmark_game.id,
                        gpu_id=gpu.id,
                        resolution=raw["resolution"],
                        **fields,
                    )
                )

        db.commit()
        logger.info("Seed de jogos/benchmarks carregado com sucesso.")
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
