"""Regras puras usadas pelo coletor do Windows, separadas para serem testáveis sem WMI."""

import re

from app.modules.catalog.enums import StorageType

# Adaptadores de vídeo que não são uma placa de verdade (driver genérico, acesso remoto,
# monitores virtuais) — aparecem em Win32_VideoController e às vezes vêm em primeiro.
_VIRTUAL_ADAPTER_HINTS = (
    "microsoft basic",
    "microsoft remote",
    "remote display",
    "virtual",
    "parsec",
    "displaylink",
    "citrix",
    "vnc",
    "hyper-v",
    "spacedesk",
)

# Nomes típicos de GPU dedicada. "AMD Radeon(TM) Graphics" e "Intel(R) UHD Graphics" (vídeo
# integrado do processador) de propósito NÃO casam aqui.
_DEDICATED_GPU_PATTERN = re.compile(
    r"geforce|quadro|nvidia rtx|radeon\s*(?:\(tm\)\s*)?(?:rx|r[579]\b|hd\b|pro\b|vii\b)|\barc\b",
    re.IGNORECASE,
)

# Valores do enum MSFT_PhysicalDisk (namespace root/Microsoft/Windows/Storage).
_MEDIA_TYPE_HDD = 3
_MEDIA_TYPE_SSD = 4
_BUS_TYPE_NVME = 17


def pick_primary_gpu(names: list[str | None]) -> str | None:
    """Em PCs com vídeo integrado ativo (e em todo notebook), o Windows lista mais de um
    adaptador, e o primeiro costuma ser o integrado. Para avaliar jogos o que importa é a
    placa dedicada, então ela tem preferência."""
    candidates = [
        name.strip()
        for name in names
        if name
        and name.strip()
        and not any(hint in name.lower() for hint in _VIRTUAL_ADAPTER_HINTS)
    ]
    if not candidates:
        return None
    dedicated = [name for name in candidates if _DEDICATED_GPU_PATTERN.search(name)]
    return (dedicated or candidates)[0]


def storage_type_from_msft(media_type: int | None, bus_type: int | None) -> str | None:
    """Tipo do disco a partir de MSFT_PhysicalDisk. Muitos HDDs antigos informam MediaType
    0 ("não especificado") — nesse caso devolvemos None em vez de chutar."""
    if bus_type == _BUS_TYPE_NVME:
        return StorageType.NVME_SSD.value
    if media_type == _MEDIA_TYPE_SSD:
        return StorageType.SATA_SSD.value
    if media_type == _MEDIA_TYPE_HDD:
        return StorageType.HDD.value
    return None
