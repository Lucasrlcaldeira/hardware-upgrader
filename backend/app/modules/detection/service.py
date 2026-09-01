import platform

from app.modules.detection.collectors.base import HardwareCollector
from app.modules.detection.collectors.manual import ManualOnlyCollector
from app.modules.detection.enums import DetectionSource
from app.modules.detection.schemas import DetectionResult, HardwareSnapshotBase


def get_collector() -> HardwareCollector:
    """Dependência FastAPI: escolhe o collector real por plataforma.

    Testável via `app.dependency_overrides[get_collector] = ...`, no mesmo
    padrão já usado para `get_db`.
    """
    if platform.system() == "Windows":
        from app.modules.detection.collectors.windows import WindowsWmiCollector

        return WindowsWmiCollector()
    return ManualOnlyCollector()


def run_detection(collector: HardwareCollector) -> DetectionResult:
    ram = collector.detect_ram()
    psu = collector.detect_psu()
    os_info = collector.detect_os()
    monitor = collector.detect_monitor()

    snapshot = HardwareSnapshotBase(
        cpu_model_name=collector.detect_cpu(),
        gpu_model_name=collector.detect_gpu(),
        motherboard_model_name=collector.detect_motherboard(),
        ram_capacity_gb=ram.capacity_gb,
        ram_speed_mhz=ram.speed_mhz,
        ram_modules=ram.modules,
        storage_devices=collector.detect_storage(),
        psu_model_name=psu.model_name,
        psu_wattage=psu.wattage,
        os_name=os_info.name,
        os_version=os_info.version,
        monitor_resolution=monitor.resolution,
        monitor_refresh_hz=monitor.refresh_hz,
    )

    field_status: dict[str, DetectionSource] = {}
    for field_name, value in snapshot.model_dump().items():
        is_present = len(value) > 0 if isinstance(value, list) else value is not None
        field_status[field_name] = (
            DetectionSource.DETECTED if is_present else DetectionSource.MANUAL_REQUIRED
        )

    return DetectionResult(snapshot=snapshot, field_status=field_status)
