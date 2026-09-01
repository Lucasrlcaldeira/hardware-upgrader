from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.catalog import schemas, service

router = APIRouter(prefix="/catalog", tags=["catalog"])

CatalogType = Literal["cpu", "gpu", "motherboard", "ram", "storage", "psu", "case", "cooler"]


@router.get("/cpus", response_model=list[schemas.CpuRead])
def get_cpus(
    socket: str | None = None,
    manufacturer: str | None = None,
    model_name: str | None = None,
    db: Session = Depends(get_db),
):
    return service.list_cpus(db, socket=socket, manufacturer=manufacturer, model_name=model_name)


@router.get("/gpus", response_model=list[schemas.GpuRead])
def get_gpus(
    manufacturer: str | None = None, model_name: str | None = None, db: Session = Depends(get_db)
):
    return service.list_gpus(db, manufacturer=manufacturer, model_name=model_name)


@router.get("/motherboards", response_model=list[schemas.MotherboardRead])
def get_motherboards(
    socket: str | None = None,
    chipset: str | None = None,
    model_name: str | None = None,
    db: Session = Depends(get_db),
):
    return service.list_motherboards(db, socket=socket, chipset=chipset, model_name=model_name)


@router.get("/ram", response_model=list[schemas.RamKitRead])
def get_ram_kits(
    memory_type: str | None = None, model_name: str | None = None, db: Session = Depends(get_db)
):
    return service.list_ram_kits(db, memory_type=memory_type, model_name=model_name)


@router.get("/storage", response_model=list[schemas.StorageRead])
def get_storage(
    storage_type: str | None = None, model_name: str | None = None, db: Session = Depends(get_db)
):
    return service.list_storage(db, storage_type=storage_type, model_name=model_name)


@router.get("/psus", response_model=list[schemas.PsuRead])
def get_psus(model_name: str | None = None, db: Session = Depends(get_db)):
    return service.list_psus(db, model_name=model_name)


@router.get("/cases", response_model=list[schemas.CaseRead])
def get_cases(model_name: str | None = None, db: Session = Depends(get_db)):
    return service.list_cases(db, model_name=model_name)


@router.get("/coolers", response_model=list[schemas.CoolerRead])
def get_coolers(model_name: str | None = None, db: Session = Depends(get_db)):
    return service.list_coolers(db, model_name=model_name)


class CatalogImportRequest(BaseModel):
    catalog_type: CatalogType
    items: list[dict]


class CatalogImportResponse(BaseModel):
    catalog_type: CatalogType
    imported: int


@router.post("/import", response_model=CatalogImportResponse)
def import_catalog_items(payload: CatalogImportRequest, db: Session = Depends(get_db)):
    """Importa/atualiza itens do catálogo em lote (upsert por model_name).

    Permite crescer o catálogo sem alterar código, conforme exigido pelo produto.
    TODO(etapa 6): restringir a usuários admin quando o módulo de auth existir.
    """
    count = 0
    if payload.catalog_type == "cpu":
        for item in payload.items:
            service.upsert_cpu(db, item)
        db.flush()
        for item in payload.items:
            service.set_cpu_substitutes(db, item["model_name"], item.get("substitute_names", []))
            count += 1
    elif payload.catalog_type == "gpu":
        for item in payload.items:
            service.upsert_gpu(db, item)
        db.flush()
        for item in payload.items:
            service.set_gpu_substitutes(db, item["model_name"], item.get("substitute_names", []))
            count += 1
    else:
        for item in payload.items:
            if payload.catalog_type == "motherboard":
                service.upsert_motherboard(db, item)
            else:
                service.upsert_simple(db, payload.catalog_type, item)
            count += 1
    db.commit()
    return CatalogImportResponse(catalog_type=payload.catalog_type, imported=count)
