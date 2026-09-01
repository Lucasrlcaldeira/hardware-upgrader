from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog import models


def list_cpus(
    db: Session,
    socket: str | None = None,
    manufacturer: str | None = None,
    model_name: str | None = None,
):
    stmt = select(models.CpuModel)
    if socket:
        stmt = stmt.where(models.CpuModel.socket == socket)
    if manufacturer:
        stmt = stmt.where(models.CpuModel.manufacturer.ilike(manufacturer))
    if model_name:
        stmt = stmt.where(models.CpuModel.model_name.ilike(model_name))
    return db.scalars(stmt.order_by(models.CpuModel.performance_tier)).all()


def list_gpus(db: Session, manufacturer: str | None = None, model_name: str | None = None):
    stmt = select(models.GpuModel)
    if manufacturer:
        stmt = stmt.where(models.GpuModel.manufacturer.ilike(manufacturer))
    if model_name:
        stmt = stmt.where(models.GpuModel.model_name.ilike(model_name))
    return db.scalars(stmt.order_by(models.GpuModel.performance_tier)).all()


def list_motherboards(
    db: Session,
    socket: str | None = None,
    chipset: str | None = None,
    model_name: str | None = None,
):
    stmt = select(models.MotherboardModel)
    if socket:
        stmt = stmt.where(models.MotherboardModel.socket == socket)
    if chipset:
        stmt = stmt.where(models.MotherboardModel.chipset.ilike(chipset))
    if model_name:
        stmt = stmt.where(models.MotherboardModel.model_name.ilike(model_name))
    return db.scalars(stmt).all()


def list_ram_kits(db: Session, memory_type: str | None = None, model_name: str | None = None):
    stmt = select(models.RamKitModel)
    if memory_type:
        stmt = stmt.where(models.RamKitModel.memory_type == memory_type)
    if model_name:
        stmt = stmt.where(models.RamKitModel.model_name.ilike(model_name))
    return db.scalars(stmt).all()


def list_storage(db: Session, storage_type: str | None = None, model_name: str | None = None):
    stmt = select(models.StorageModel)
    if storage_type:
        stmt = stmt.where(models.StorageModel.storage_type == storage_type)
    if model_name:
        stmt = stmt.where(models.StorageModel.model_name.ilike(model_name))
    return db.scalars(stmt).all()


def list_psus(db: Session, model_name: str | None = None):
    stmt = select(models.PsuModel)
    if model_name:
        stmt = stmt.where(models.PsuModel.model_name.ilike(model_name))
    return db.scalars(stmt.order_by(models.PsuModel.wattage)).all()


def list_cases(db: Session, model_name: str | None = None):
    stmt = select(models.CaseModel)
    if model_name:
        stmt = stmt.where(models.CaseModel.model_name.ilike(model_name))
    return db.scalars(stmt).all()


def list_coolers(db: Session, model_name: str | None = None):
    stmt = select(models.CoolerModel)
    if model_name:
        stmt = stmt.where(models.CoolerModel.model_name.ilike(model_name))
    return db.scalars(stmt).all()


def get_cpu_by_model_name(db: Session, model_name: str) -> models.CpuModel | None:
    return db.scalar(select(models.CpuModel).where(models.CpuModel.model_name == model_name))


def get_gpu_by_model_name(db: Session, model_name: str) -> models.GpuModel | None:
    return db.scalar(select(models.GpuModel).where(models.GpuModel.model_name == model_name))


def get_motherboard_by_model_name(db: Session, model_name: str) -> models.MotherboardModel | None:
    return db.scalar(
        select(models.MotherboardModel).where(models.MotherboardModel.model_name == model_name)
    )


def get_ram_kit_by_model_name(db: Session, model_name: str) -> models.RamKitModel | None:
    return db.scalar(
        select(models.RamKitModel).where(models.RamKitModel.model_name == model_name)
    )


def get_storage_by_model_name(db: Session, model_name: str) -> models.StorageModel | None:
    return db.scalar(
        select(models.StorageModel).where(models.StorageModel.model_name == model_name)
    )


def get_psu_by_model_name(db: Session, model_name: str) -> models.PsuModel | None:
    return db.scalar(select(models.PsuModel).where(models.PsuModel.model_name == model_name))


def get_case_by_model_name(db: Session, model_name: str) -> models.CaseModel | None:
    return db.scalar(select(models.CaseModel).where(models.CaseModel.model_name == model_name))


def get_cooler_by_model_name(db: Session, model_name: str) -> models.CoolerModel | None:
    return db.scalar(
        select(models.CoolerModel).where(models.CoolerModel.model_name == model_name)
    )


_MODEL_BY_TYPE: dict[str, type] = {
    "ram": models.RamKitModel,
    "storage": models.StorageModel,
    "psu": models.PsuModel,
    "case": models.CaseModel,
    "cooler": models.CoolerModel,
}


def upsert_simple(db: Session, catalog_type: str, data: dict[str, Any]):
    """Upsert por model_name para catálogos sem relação de substitutos (ram/storage/psu)."""
    model = _MODEL_BY_TYPE[catalog_type]
    existing = db.scalar(select(model).where(model.model_name == data["model_name"]))
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        return existing
    obj = model(**data)
    db.add(obj)
    return obj


def upsert_cpu(db: Session, data: dict[str, Any]) -> models.CpuModel:
    """Upsert de CPU sem tocar em `substitutes` (ver `set_cpu_substitutes`).

    Nomes em `substitute_names` podem se referir a CPUs ainda não inseridas
    nesta mesma leva de import — resolver isso exige um segundo passe depois
    que todas as CPUs já existem no banco.
    """
    data = {k: v for k, v in data.items() if k != "substitute_names"}
    existing = get_cpu_by_model_name(db, data["model_name"])
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        return existing
    obj = models.CpuModel(**data)
    db.add(obj)
    return obj


def set_cpu_substitutes(db: Session, model_name: str, substitute_names: list[str]) -> None:
    cpu = get_cpu_by_model_name(db, model_name)
    if cpu is None or not substitute_names:
        return
    cpu.substitutes = [
        c for name in substitute_names if (c := get_cpu_by_model_name(db, name)) is not None
    ]


def upsert_gpu(db: Session, data: dict[str, Any]) -> models.GpuModel:
    """Upsert de GPU sem tocar em `substitutes` (ver `set_gpu_substitutes`)."""
    data = {k: v for k, v in data.items() if k != "substitute_names"}
    existing = get_gpu_by_model_name(db, data["model_name"])
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        return existing
    obj = models.GpuModel(**data)
    db.add(obj)
    return obj


def set_gpu_substitutes(db: Session, model_name: str, substitute_names: list[str]) -> None:
    gpu = get_gpu_by_model_name(db, model_name)
    if gpu is None or not substitute_names:
        return
    gpu.substitutes = [
        g for name in substitute_names if (g := get_gpu_by_model_name(db, name)) is not None
    ]


def upsert_motherboard(db: Session, data: dict[str, Any]) -> models.MotherboardModel:
    existing = get_motherboard_by_model_name(db, data["model_name"])
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        return existing
    obj = models.MotherboardModel(**data)
    db.add(obj)
    return obj
