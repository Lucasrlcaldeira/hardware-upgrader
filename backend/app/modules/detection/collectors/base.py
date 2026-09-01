from abc import ABC, abstractmethod

from app.modules.detection.schemas import MonitorInfo, OsInfo, PsuInfo, RamInfo, StorageDeviceInfo


class HardwareCollector(ABC):
    """Uma implementação por fonte de detecção (Windows real, manual/fallback, etc.).

    Nunca lança exceção: um componente que não pode ser detectado retorna
    `None` (ou uma instância "vazia"/lista vazia) em vez de falhar — é isso
    que o `service.run_detection` usa para marcar o campo como
    `MANUAL_REQUIRED` e pedir para o usuário preencher.
    """

    @abstractmethod
    def detect_cpu(self) -> str | None: ...

    @abstractmethod
    def detect_gpu(self) -> str | None: ...

    @abstractmethod
    def detect_motherboard(self) -> str | None: ...

    @abstractmethod
    def detect_ram(self) -> RamInfo: ...

    @abstractmethod
    def detect_storage(self) -> list[StorageDeviceInfo]: ...

    @abstractmethod
    def detect_psu(self) -> PsuInfo: ...

    @abstractmethod
    def detect_os(self) -> OsInfo: ...

    @abstractmethod
    def detect_monitor(self) -> MonitorInfo: ...
