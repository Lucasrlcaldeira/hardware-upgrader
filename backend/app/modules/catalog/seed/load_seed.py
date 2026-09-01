"""Carrega o dataset curado de hardware (JSON nesta pasta) no banco.

Idempotente: roda upsert por model_name, então pode ser executado de novo
sempre que os arquivos JSON forem atualizados — sem precisar tocar em
código de motor (compatibilidade/gargalo/recomendação).

Uso:
    backend/.venv/Scripts/python -m app.modules.catalog.seed.load_seed
"""

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.catalog import schemas, service

logger = logging.getLogger(__name__)
SEED_DIR = Path(__file__).parent


def _load_json(filename: str) -> list[dict]:
    with open(SEED_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def run(db: Session | None = None) -> None:
    """Carrega o seed na sessão passada, ou cria uma nova (Postgres) se None.

    Aceitar uma sessão injetada permite testar o upsert/vínculo de
    substitutos de verdade contra a fixture SQLite dos testes, em vez de
    só validar os JSONs contra os schemas Pydantic.
    """
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        cpus_raw = _load_json("cpus.json")
        for raw in cpus_raw:
            data = schemas.CpuBase.model_validate(
                {k: v for k, v in raw.items() if k != "substitute_names"}
            ).model_dump()
            service.upsert_cpu(db, data)
        db.flush()
        for raw in cpus_raw:
            service.set_cpu_substitutes(db, raw["model_name"], raw.get("substitute_names", []))

        gpus_raw = _load_json("gpus.json")
        for raw in gpus_raw:
            data = schemas.GpuBase.model_validate(
                {k: v for k, v in raw.items() if k != "substitute_names"}
            ).model_dump()
            service.upsert_gpu(db, data)
        db.flush()
        for raw in gpus_raw:
            service.set_gpu_substitutes(db, raw["model_name"], raw.get("substitute_names", []))

        for raw in _load_json("motherboards.json"):
            data = schemas.MotherboardBase.model_validate(raw).model_dump()
            service.upsert_motherboard(db, data)

        for raw in _load_json("ram.json"):
            data = schemas.RamKitBase.model_validate(raw).model_dump()
            service.upsert_simple(db, "ram", data)

        for raw in _load_json("storage.json"):
            data = schemas.StorageBase.model_validate(raw).model_dump()
            service.upsert_simple(db, "storage", data)

        for raw in _load_json("psus.json"):
            data = schemas.PsuBase.model_validate(raw).model_dump()
            service.upsert_simple(db, "psu", data)

        for raw in _load_json("cases.json"):
            data = schemas.CaseBase.model_validate(raw).model_dump()
            service.upsert_simple(db, "case", data)

        for raw in _load_json("coolers.json"):
            data = schemas.CoolerBase.model_validate(raw).model_dump()
            service.upsert_simple(db, "cooler", data)

        db.commit()
        logger.info("Seed do catálogo carregado com sucesso.")
    except Exception:
        db.rollback()
        raise
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
