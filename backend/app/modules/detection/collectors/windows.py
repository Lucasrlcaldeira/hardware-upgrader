import logging
import platform

import pythoncom
import wmi

from app.modules.detection.collectors.base import HardwareCollector
from app.modules.detection.schemas import MonitorInfo, OsInfo, PsuInfo, RamInfo, StorageDeviceInfo

logger = logging.getLogger(__name__)


class WindowsWmiCollector(HardwareCollector):
    """Detecção real via WMI (pacote `WMI`) + `pywin32`.

    PSU não é exposto de forma confiável pela WMI na grande maioria das
    placas-mãe — na prática esse campo quase sempre acaba MANUAL_REQUIRED,
    o que é o comportamento correto (não inventamos o dado).
    """

    def _connect(self) -> "wmi.WMI":
        # COM tem estado por thread, e o FastAPI despacha dependências/handlers síncronos
        # para um pool de threads sem garantir a mesma thread entre chamadas dentro de uma
        # mesma requisição — conectar uma única vez em __init__ falhava intermitentemente
        # (x_wmi_uninitialised_thread) nas threads do pool que nunca tinham COM inicializado.
        # CoInitialize é idempotente por thread (seguro chamar de novo), então conectamos
        # aqui, a cada chamada, em vez de guardar uma conexão criada em outra thread.
        pythoncom.CoInitialize()
        return wmi.WMI()

    def detect_cpu(self) -> str | None:
        try:
            cpus = self._connect().Win32_Processor()
            return cpus[0].Name.strip() if cpus and cpus[0].Name else None
        except Exception:
            logger.exception("Falha ao detectar CPU via WMI")
            return None

    def detect_gpu(self) -> str | None:
        try:
            gpus = self._connect().Win32_VideoController()
            return gpus[0].Name.strip() if gpus and gpus[0].Name else None
        except Exception:
            logger.exception("Falha ao detectar GPU via WMI")
            return None

    def detect_motherboard(self) -> str | None:
        try:
            boards = self._connect().Win32_BaseBoard()
            if not boards:
                return None
            board = boards[0]
            parts = [p for p in (board.Manufacturer, board.Product) if p]
            return " ".join(parts).strip() or None
        except Exception:
            logger.exception("Falha ao detectar placa-mãe via WMI")
            return None

    def detect_ram(self) -> RamInfo:
        try:
            modules = self._connect().Win32_PhysicalMemory()
            if not modules:
                return RamInfo()
            total_bytes = sum(int(m.Capacity) for m in modules if m.Capacity)
            capacity_gb = round(total_bytes / (1024**3)) if total_bytes else None
            speed_mhz = int(modules[0].Speed) if modules[0].Speed else None
            return RamInfo(capacity_gb=capacity_gb, speed_mhz=speed_mhz, modules=len(modules))
        except Exception:
            logger.exception("Falha ao detectar RAM via WMI")
            return RamInfo()

    def detect_storage(self) -> list[StorageDeviceInfo]:
        try:
            drives = self._connect().Win32_DiskDrive()
            devices = []
            for drive in drives:
                capacity_gb = round(int(drive.Size) / (1024**3)) if drive.Size else None
                devices.append(
                    StorageDeviceInfo(
                        # WMI não distingue HDD/SATA SSD/NVMe de forma confiável;
                        # deixar em branco em vez de chutar.
                        storage_type=None,
                        capacity_gb=capacity_gb,
                        model_name=drive.Model.strip() if drive.Model else None,
                    )
                )
            return devices
        except Exception:
            logger.exception("Falha ao detectar armazenamento via WMI")
            return []

    def detect_psu(self) -> PsuInfo:
        return PsuInfo()

    def detect_os(self) -> OsInfo:
        try:
            return OsInfo(
                name="Windows",
                version=f"{platform.release()} (build {platform.version()})",
            )
        except Exception:
            logger.exception("Falha ao detectar sistema operacional")
            return OsInfo()

    def detect_monitor(self) -> MonitorInfo:
        try:
            import win32api

            width = win32api.GetSystemMetrics(0)
            height = win32api.GetSystemMetrics(1)
            resolution = f"{width}x{height}" if width and height else None

            refresh_hz = None
            try:
                settings = win32api.EnumDisplaySettings(None, -1)
                refresh_hz = getattr(settings, "DisplayFrequency", None) or None
            except Exception:
                logger.exception("Falha ao detectar taxa de atualização do monitor")

            return MonitorInfo(resolution=resolution, refresh_hz=refresh_hz)
        except Exception:
            logger.exception("Falha ao detectar monitor")
            return MonitorInfo()
