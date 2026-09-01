import enum


class MemoryType(str, enum.Enum):
    DDR3 = "DDR3"
    DDR4 = "DDR4"
    DDR5 = "DDR5"


class StorageType(str, enum.Enum):
    HDD = "HDD"
    SATA_SSD = "SATA_SSD"
    NVME_SSD = "NVME_SSD"


class PsuModular(str, enum.Enum):
    NONE = "NONE"
    SEMI = "SEMI"
    FULL = "FULL"


class FormFactor(str, enum.Enum):
    ATX = "ATX"
    MICRO_ATX = "MICRO_ATX"
    MINI_ITX = "MINI_ITX"
    E_ATX = "E_ATX"


class CoolerType(str, enum.Enum):
    AIR = "AIR"
    AIO_LIQUID = "AIO_LIQUID"
