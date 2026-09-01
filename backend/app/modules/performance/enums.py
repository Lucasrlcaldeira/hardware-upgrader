import enum


class WorkloadType(str, enum.Enum):
    GAMING = "GAMING"
    CONTENT_CREATION = "CONTENT_CREATION"
    PRODUCTIVITY = "PRODUCTIVITY"
    GENERAL = "GENERAL"


class GraphicsQuality(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    ULTRA = "ULTRA"


class Resolution(str, enum.Enum):
    R_1080P = "1080P"
    R_1440P = "1440P"
    R_4K = "4K"


class BottleneckVerdict(str, enum.Enum):
    CPU_BOUND = "CPU_BOUND"
    GPU_BOUND = "GPU_BOUND"
    BALANCED = "BALANCED"
    # Não é produzido diretamente pelo service (que levanta InsufficientDataError) — existe
    # para a etapa de análise (orquestrador) representar um resultado degradado ao persistir.
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ConfidenceLevel(str, enum.Enum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
