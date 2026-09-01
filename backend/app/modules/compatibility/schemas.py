from pydantic import BaseModel

from app.modules.compatibility.enums import CompatibilityRelation, CompatibilityStatus


class CompatibilityResult(BaseModel):
    relation: CompatibilityRelation
    status: CompatibilityStatus
    reason: str
    additional_required_components: list[str] = []


class BundleUpgrade(BaseModel):
    components: list[str]
    reason: str


class CompatibilityCheckRequest(BaseModel):
    """model_name (do catálogo) de cada componente a checar entre si.

    Qualquer campo omitido simplesmente pula os checks que dependeriam dele
    — não é obrigatório informar o sistema inteiro para checar um par.
    """

    cpu_model_name: str | None = None
    gpu_model_name: str | None = None
    motherboard_model_name: str | None = None
    ram_model_name: str | None = None
    storage_model_name: str | None = None
    psu_model_name: str | None = None
    case_model_name: str | None = None
    cooler_model_name: str | None = None


class CompatibilityCheckResponse(BaseModel):
    results: list[CompatibilityResult]
    bundle: BundleUpgrade | None = None
