import logging
import platform

import psutil
import pythoncom
import wmi

from app.modules.detection.collectors.base import HardwareCollector
from app.modules.detection.collectors.heuristics import pick_primary_gpu, storage_type_from_msft
from app.modules.detection.schemas import MonitorInfo, OsInfo, PsuInfo, RamInfo, StorageDeviceInfo

logger = logging.getLogger(__name__)

_ENUM_CURRENT_SETTINGS = -1


class WindowsWmiCollector(HardwareCollector):
    """Detecção real via WMI (pacote `WMI`) + `pywin32`.

    PSU não é exposto de forma confiável pela WMI na grande maioria das
    placas-mãe — na prática esse campo quase sempre acaba MANUAL_REQUIRED,
    o que é o comportamento correto (não inventamos o dado).
    """

    def _connect(self, namespace: str | None = None) -> "wmi.WMI":
        # COM tem estado por thread, e o FastAPI despacha dependências/handlers síncronos
        # para um pool de threads sem garantir a mesma thread entre chamadas dentro de uma
        # mesma requisição — conectar uma única vez em __init__ falhava intermitentemente
        # (x_wmi_uninitialised_thread) nas threads do pool que nunca tinham COM inicializado.
        # CoInitialize é idempotente por thread (seguro chamar de novo), então conectamos
        # aqui, a cada chamada, em vez de guardar uma conexão criada em outra thread.
        pythoncom.CoInitialize()
        return wmi.WMI(namespace=namespace) if namespace else wmi.WMI()

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
            return pick_primary_gpu([gpu.Name for gpu in gpus])
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
        # MSFT_PhysicalDisk (Windows 8+) informa se o disco é SSD/HDD/NVMe, o que
        # Win32_DiskDrive não faz. Se o namespace não estiver disponível, caímos no
        # Win32_DiskDrive e deixamos o tipo em branco.
        try:
            disks = self._connect("root/Microsoft/Windows/Storage").MSFT_PhysicalDisk()
            return [
                StorageDeviceInfo(
                    storage_type=storage_type_from_msft(disk.MediaType, disk.BusType),
                    capacity_gb=round(int(disk.Size) / (1024**3)) if disk.Size else None,
                    model_name=disk.FriendlyName.strip() if disk.FriendlyName else None,
                )
                for disk in disks
            ]
        except Exception:
            logger.warning(
                "MSFT_PhysicalDisk indisponível; usando Win32_DiskDrive (sem tipo de disco)",
                exc_info=True,
            )

        try:
            drives = self._connect().Win32_DiskDrive()
            return [
                StorageDeviceInfo(
                    storage_type=None,
                    capacity_gb=round(int(drive.Size) / (1024**3)) if drive.Size else None,
                    model_name=drive.Model.strip() if drive.Model else None,
                )
                for drive in drives
            ]
        except Exception:
            logger.exception("Falha ao detectar armazenamento via WMI")
            return []

    def detect_free_disk_space_gb(self) -> int | None:
        free_values: list[int] = []
        for partition in psutil.disk_partitions(all=False):
            # Só unidades internas: pendrives e leitores de DVD não são onde se instala jogo.
            if "fixed" not in partition.opts:
                continue
            try:
                free_values.append(psutil.disk_usage(partition.mountpoint).free)
            except OSError:
                logger.warning("Sem acesso à unidade %s", partition.mountpoint, exc_info=True)
        return int(max(free_values) / (1024**3)) if free_values else None

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

            # EnumDisplaySettings devolve o modo de vídeo real. GetSystemMetrics (o que
            # usávamos antes) é afetado pela escala do Windows: com 125%, um monitor 1920x1080
            # aparecia como 1536x864, porque o processo do backend não é "DPI aware".
            resolution = None
            refresh_hz = None
            try:
                settings = win32api.EnumDisplaySettings(None, _ENUM_CURRENT_SETTINGS)
                if settings.PelsWidth and settings.PelsHeight:
                    resolution = f"{settings.PelsWidth}x{settings.PelsHeight}"
                refresh_hz = getattr(settings, "DisplayFrequency", None) or None
            except Exception:
                logger.exception("Falha ao ler o modo de vídeo atual do monitor")

            if resolution is None:
                width = win32api.GetSystemMetrics(0)
                height = win32api.GetSystemMetrics(1)
                resolution = f"{width}x{height}" if width and height else None

            return MonitorInfo(resolution=resolution, refresh_hz=refresh_hz)
        except Exception:
            logger.exception("Falha ao detectar monitor")
            return MonitorInfo()
