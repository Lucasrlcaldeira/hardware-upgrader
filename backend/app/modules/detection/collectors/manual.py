from app.modules.detection.collectors.base import HardwareCollector
from app.modules.detection.schemas import MonitorInfo, OsInfo, PsuInfo, RamInfo, StorageDeviceInfo


class ManualOnlyCollector(HardwareCollector):
    """Fallback usado fora do Windows e em testes: nada é detectado
    automaticamente, então todo campo vira MANUAL_REQUIRED."""

    def detect_cpu(self) -> str | None:
        return None

    def detect_gpu(self) -> str | None:
        return None

    def detect_motherboard(self) -> str | None:
        return None

    def detect_ram(self) -> RamInfo:
        return RamInfo()

    def detect_storage(self) -> list[StorageDeviceInfo]:
        return []

    def detect_psu(self) -> PsuInfo:
        return PsuInfo()

    def detect_os(self) -> OsInfo:
        return OsInfo()

    def detect_monitor(self) -> MonitorInfo:
        return MonitorInfo()
