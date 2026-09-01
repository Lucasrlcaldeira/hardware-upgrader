import enum


class UpgradeProfile(str, enum.Enum):
    ECONOMICO = "ECONOMICO"
    CUSTO_BENEFICIO = "CUSTO_BENEFICIO"
    ALTO_DESEMPENHO = "ALTO_DESEMPENHO"
    UPGRADE_COMPLETO = "UPGRADE_COMPLETO"


class RecommendationPriority(str, enum.Enum):
    CRITICA = "CRITICA"
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAIXA = "BAIXA"


class ComponentSlot(str, enum.Enum):
    CPU = "cpu"
    GPU = "gpu"
    MOTHERBOARD = "motherboard"
    RAM = "ram"
    STORAGE = "storage"
    PSU = "psu"
    CASE = "case"
    COOLER = "cooler"
