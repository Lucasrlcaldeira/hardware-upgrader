import datetime as dt

from sqlalchemy import JSON, Column, Date, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.catalog.enums import CoolerType, FormFactor, MemoryType, PsuModular, StorageType


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(
        default=lambda: dt.datetime.now(dt.UTC)
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        default=lambda: dt.datetime.now(dt.UTC),
        onupdate=lambda: dt.datetime.now(dt.UTC),
    )


class PriceRangeMixin:
    """Faixa de preço em BRL. Ambos nulos = 'dado insuficiente'."""

    price_range_brl_min: Mapped[int | None] = mapped_column(Integer)
    price_range_brl_max: Mapped[int | None] = mapped_column(Integer)


cpu_substitutes = Table(
    "cpu_substitutes",
    Base.metadata,
    Column("cpu_id", ForeignKey("cpu_models.id"), primary_key=True),
    Column("substitute_id", ForeignKey("cpu_models.id"), primary_key=True),
)

gpu_substitutes = Table(
    "gpu_substitutes",
    Base.metadata,
    Column("gpu_id", ForeignKey("gpu_models.id"), primary_key=True),
    Column("substitute_id", ForeignKey("gpu_models.id"), primary_key=True),
)


class CpuModel(TimestampMixin, PriceRangeMixin, Base):
    """Especificação de um modelo de CPU. Dado de referência, não específico de usuário."""

    __tablename__ = "cpu_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str] = mapped_column(String(50), index=True)
    model_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    generation: Mapped[str | None] = mapped_column(String(50))
    socket: Mapped[str] = mapped_column(String(30), index=True)

    cores: Mapped[int | None]
    threads: Mapped[int | None]
    base_clock_ghz: Mapped[float | None]
    boost_clock_ghz: Mapped[float | None]
    tdp_watts: Mapped[int | None]
    integrated_gpu: Mapped[str | None] = mapped_column(String(100))
    pcie_version: Mapped[str | None] = mapped_column(String(10))
    memory_types_supported: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_memory_speed_mhz: Mapped[int | None]

    # Índice ordinal relativo (não percentual, não benchmark absoluto) usado
    # apenas para ranquear CPUs entre si nos motores de gargalo/recomendação.
    performance_tier: Mapped[int | None]

    release_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    substitutes: Mapped[list["CpuModel"]] = relationship(
        "CpuModel",
        secondary=cpu_substitutes,
        primaryjoin=id == cpu_substitutes.c.cpu_id,
        secondaryjoin=id == cpu_substitutes.c.substitute_id,
    )


class GpuModel(TimestampMixin, PriceRangeMixin, Base):
    __tablename__ = "gpu_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str] = mapped_column(String(50), index=True)
    model_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    architecture: Mapped[str | None] = mapped_column(String(50))

    vram_gb: Mapped[int | None]
    memory_type: Mapped[str | None] = mapped_column(String(20))
    tdp_watts: Mapped[int | None]
    recommended_psu_watts: Mapped[int | None]
    pcie_version: Mapped[str | None] = mapped_column(String(10))
    length_mm: Mapped[int | None]

    performance_tier: Mapped[int | None]

    release_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    substitutes: Mapped[list["GpuModel"]] = relationship(
        "GpuModel",
        secondary=gpu_substitutes,
        primaryjoin=id == gpu_substitutes.c.gpu_id,
        secondaryjoin=id == gpu_substitutes.c.substitute_id,
    )


class MotherboardModel(TimestampMixin, PriceRangeMixin, Base):
    __tablename__ = "motherboard_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str] = mapped_column(String(50), index=True)
    model_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    socket: Mapped[str] = mapped_column(String(30), index=True)
    chipset: Mapped[str] = mapped_column(String(30), index=True)
    form_factor: Mapped[FormFactor | None]

    memory_type: Mapped[MemoryType]
    memory_slots: Mapped[int | None]
    max_memory_gb: Mapped[int | None]
    max_memory_speed_mhz: Mapped[int | None]

    # ex: [{"version": "4.0", "lanes": 16, "count": 1}, {"version": "3.0", "lanes": 4, "count": 2}]
    pcie_slots: Mapped[list[dict]] = mapped_column(JSON, default=list)
    m2_slots: Mapped[int | None]

    # gerações de CPU oficialmente suportadas por esse socket+chipset,
    # ex: ["Zen 2", "Zen 3"]. Não confundir com "toda CPU desse socket funciona".
    supports_cpu_generations: Mapped[list[str]] = mapped_column(JSON, default=list)
    # notas sobre exigência de atualização de BIOS/UEFI para gerações específicas
    bios_notes: Mapped[str | None] = mapped_column(Text)

    release_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class RamKitModel(TimestampMixin, PriceRangeMixin, Base):
    __tablename__ = "ram_kit_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    memory_type: Mapped[MemoryType] = mapped_column(index=True)
    speed_mhz: Mapped[int]
    capacity_gb_per_module: Mapped[int]
    modules_in_kit: Mapped[int]
    cas_latency: Mapped[int | None]

    release_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class StorageModel(TimestampMixin, PriceRangeMixin, Base):
    __tablename__ = "storage_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    storage_type: Mapped[StorageType] = mapped_column(index=True)
    interface: Mapped[str | None] = mapped_column(String(50))
    form_factor: Mapped[str | None] = mapped_column(String(30))
    capacity_gb: Mapped[int | None]
    read_speed_mbps: Mapped[int | None]
    write_speed_mbps: Mapped[int | None]

    release_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class PsuModel(TimestampMixin, PriceRangeMixin, Base):
    __tablename__ = "psu_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    wattage: Mapped[int] = mapped_column(index=True)
    efficiency_rating: Mapped[str | None] = mapped_column(String(30))
    modular: Mapped[PsuModular | None]
    form_factor: Mapped[FormFactor | None]

    release_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class CaseModel(TimestampMixin, PriceRangeMixin, Base):
    """Gabinete. Usado pelo motor de compatibilidade para checar clearance
    de GPU e suporte de form factor de placa-mãe."""

    __tablename__ = "case_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # form factors de placa-mãe que o gabinete aceita, ex: ["ATX", "MICRO_ATX", "MINI_ITX"]
    supported_form_factors: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_gpu_length_mm: Mapped[int | None]
    max_cooler_height_mm: Mapped[int | None]

    release_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)


class CoolerModel(TimestampMixin, PriceRangeMixin, Base):
    """Cooler de CPU (a ar ou AIO). Usado pelo motor de compatibilidade
    para checar suporte de socket e, no caso AIO, clearance de radiador."""

    __tablename__ = "cooler_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str | None] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    cooler_type: Mapped[CoolerType]

    # sockets suportados, ex: ["AM4", "AM5", "LGA1700"]
    supported_sockets: Mapped[list[str]] = mapped_column(JSON, default=list)
    height_mm: Mapped[int | None]  # relevante para coolers a ar (clearance do gabinete)
    radiator_size_mm: Mapped[int | None]  # relevante para AIO (120/240/280/360mm)
    tdp_rating_watts: Mapped[int | None]

    release_date: Mapped[dt.date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
