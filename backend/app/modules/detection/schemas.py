from pydantic import BaseModel

from app.modules.detection.enums import DetectionSource


class RamInfo(BaseModel):
    capacity_gb: int | None = None
    speed_mhz: int | None = None
    modules: int | None = None


class PsuInfo(BaseModel):
    model_name: str | None = None
    wattage: int | None = None


class OsInfo(BaseModel):
    name: str | None = None
    version: str | None = None


class MonitorInfo(BaseModel):
    resolution: str | None = None
    refresh_hz: int | None = None


class StorageDeviceInfo(BaseModel):
    storage_type: str | None = None
    capacity_gb: int | None = None
    model_name: str | None = None


class HardwareSnapshotBase(BaseModel):
    """Estrutura única usada tanto pela detecção automática quanto pela
    entrada manual do usuário — os dois caminhos preenchem exatamente os
    mesmos campos, conforme exigido pelo produto."""

    cpu_model_name: str | None = None
    gpu_model_name: str | None = None
    motherboard_model_name: str | None = None
    ram_capacity_gb: int | None = None
    ram_speed_mhz: int | None = None
    ram_modules: int | None = None
    storage_devices: list[StorageDeviceInfo] = []
    psu_model_name: str | None = None
    psu_wattage: int | None = None
    os_name: str | None = None
    os_version: str | None = None
    monitor_resolution: str | None = None
    monitor_refresh_hz: int | None = None


class DetectionResult(BaseModel):
    snapshot: HardwareSnapshotBase
    field_status: dict[str, DetectionSource]
