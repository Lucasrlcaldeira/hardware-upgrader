import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.modules.catalog.enums import CoolerType, FormFactor, MemoryType, PsuModular, StorageType


class _CatalogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PriceRangeMixin(BaseModel):
    price_range_brl_min: int | None = None
    price_range_brl_max: int | None = None


# ---------------------------------------------------------------- CPU
class CpuBase(PriceRangeMixin):
    manufacturer: str
    model_name: str
    generation: str | None = None
    socket: str
    cores: int | None = None
    threads: int | None = None
    base_clock_ghz: float | None = None
    boost_clock_ghz: float | None = None
    tdp_watts: int | None = None
    integrated_gpu: str | None = None
    pcie_version: str | None = None
    memory_types_supported: list[str] = []
    max_memory_speed_mhz: int | None = None
    performance_tier: int | None = None
    release_date: dt.date | None = None
    notes: str | None = None


class CpuCreate(CpuBase):
    substitute_ids: list[int] = []


class CpuRead(_CatalogBase, CpuBase):
    id: int


# ---------------------------------------------------------------- GPU
class GpuBase(PriceRangeMixin):
    manufacturer: str
    model_name: str
    architecture: str | None = None
    vram_gb: int | None = None
    memory_type: str | None = None
    tdp_watts: int | None = None
    recommended_psu_watts: int | None = None
    pcie_version: str | None = None
    length_mm: int | None = None
    performance_tier: int | None = None
    release_date: dt.date | None = None
    notes: str | None = None


class GpuCreate(GpuBase):
    substitute_ids: list[int] = []


class GpuRead(_CatalogBase, GpuBase):
    id: int


# ---------------------------------------------------------------- Motherboard
class MotherboardBase(PriceRangeMixin):
    manufacturer: str
    model_name: str
    socket: str
    chipset: str
    form_factor: FormFactor | None = None
    memory_type: MemoryType
    memory_slots: int | None = None
    max_memory_gb: int | None = None
    max_memory_speed_mhz: int | None = None
    pcie_slots: list[dict] = []
    m2_slots: int | None = None
    supports_cpu_generations: list[str] = []
    bios_notes: str | None = None
    release_date: dt.date | None = None
    notes: str | None = None


class MotherboardCreate(MotherboardBase):
    pass


class MotherboardRead(_CatalogBase, MotherboardBase):
    id: int


# ---------------------------------------------------------------- RAM
class RamKitBase(PriceRangeMixin):
    manufacturer: str | None = None
    model_name: str
    memory_type: MemoryType
    speed_mhz: int
    capacity_gb_per_module: int
    modules_in_kit: int
    cas_latency: int | None = None
    release_date: dt.date | None = None
    notes: str | None = None


class RamKitCreate(RamKitBase):
    pass


class RamKitRead(_CatalogBase, RamKitBase):
    id: int


# ---------------------------------------------------------------- Storage
class StorageBase(PriceRangeMixin):
    manufacturer: str | None = None
    model_name: str
    storage_type: StorageType
    interface: str | None = None
    form_factor: str | None = None
    capacity_gb: int | None = None
    read_speed_mbps: int | None = None
    write_speed_mbps: int | None = None
    release_date: dt.date | None = None
    notes: str | None = None


class StorageCreate(StorageBase):
    pass


class StorageRead(_CatalogBase, StorageBase):
    id: int


# ---------------------------------------------------------------- PSU
class PsuBase(PriceRangeMixin):
    manufacturer: str | None = None
    model_name: str
    wattage: int
    efficiency_rating: str | None = None
    modular: PsuModular | None = None
    form_factor: FormFactor | None = None
    release_date: dt.date | None = None
    notes: str | None = None


class PsuCreate(PsuBase):
    pass


class PsuRead(_CatalogBase, PsuBase):
    id: int


# ---------------------------------------------------------------- Case
class CaseBase(PriceRangeMixin):
    manufacturer: str | None = None
    model_name: str
    supported_form_factors: list[FormFactor] = []
    max_gpu_length_mm: int | None = None
    max_cooler_height_mm: int | None = None
    release_date: dt.date | None = None
    notes: str | None = None


class CaseCreate(CaseBase):
    pass


class CaseRead(_CatalogBase, CaseBase):
    id: int


# ---------------------------------------------------------------- Cooler
class CoolerBase(PriceRangeMixin):
    manufacturer: str | None = None
    model_name: str
    cooler_type: CoolerType
    supported_sockets: list[str] = []
    height_mm: int | None = None
    radiator_size_mm: int | None = None
    tdp_rating_watts: int | None = None
    release_date: dt.date | None = None
    notes: str | None = None


class CoolerCreate(CoolerBase):
    pass


class CoolerRead(_CatalogBase, CoolerBase):
    id: int
