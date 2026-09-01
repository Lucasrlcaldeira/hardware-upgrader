import enum


class CompatibilityStatus(str, enum.Enum):
    COMPATIVEL = "COMPATIVEL"
    INCOMPATIVEL = "INCOMPATIVEL"
    COMPATIVEL_COM_RESSALVAS = "COMPATIVEL_COM_RESSALVAS"
    REQUER_ATUALIZACAO_BIOS = "REQUER_ATUALIZACAO_BIOS"
    REQUER_TROCA_DE_OUTROS_COMPONENTES = "REQUER_TROCA_DE_OUTROS_COMPONENTES"
    INFORMACAO_INSUFICIENTE = "INFORMACAO_INSUFICIENTE"


class CompatibilityRelation(str, enum.Enum):
    CPU_MOTHERBOARD = "cpu_motherboard"
    MOTHERBOARD_RAM = "motherboard_ram"
    GPU_PSU = "gpu_psu"
    CPU_GPU_PCIE = "cpu_gpu_pcie"
    MOTHERBOARD_STORAGE = "motherboard_storage"
    CASE_GPU = "case_gpu"
    CASE_MOTHERBOARD = "case_motherboard"
    COOLER_CPU = "cooler_cpu"
