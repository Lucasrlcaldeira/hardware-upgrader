import enum


class RequirementTier(str, enum.Enum):
    MINIMUM = "MINIMUM"
    RECOMMENDED = "RECOMMENDED"


class RequirementComponent(str, enum.Enum):
    CPU = "cpu"
    GPU = "gpu"
    VRAM = "vram"
    RAM = "ram"
    STORAGE = "storage"
    OS = "os"


class CheckStatus(str, enum.Enum):
    ATENDE = "ATENDE"
    NAO_ATENDE = "NAO_ATENDE"
    NAO_DETERMINADO = "NAO_DETERMINADO"


class GameVerdict(str, enum.Enum):
    RODA_NO_RECOMENDADO = "RODA_NO_RECOMENDADO"
    RODA_NO_MINIMO = "RODA_NO_MINIMO"
    ABAIXO_DO_MINIMO = "ABAIXO_DO_MINIMO"
    INDETERMINADO = "INDETERMINADO"
