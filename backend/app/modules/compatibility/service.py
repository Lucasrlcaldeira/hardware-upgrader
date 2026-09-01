from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.catalog import models as catalog_models
from app.modules.catalog import service as catalog_service
from app.modules.catalog.enums import StorageType
from app.modules.compatibility.enums import CompatibilityRelation, CompatibilityStatus
from app.modules.compatibility.schemas import (
    BundleUpgrade,
    CompatibilityCheckRequest,
    CompatibilityCheckResponse,
    CompatibilityResult,
)

T = TypeVar("T")


def check_cpu_motherboard(
    cpu: catalog_models.CpuModel, motherboard: catalog_models.MotherboardModel
) -> CompatibilityResult:
    relation = CompatibilityRelation.CPU_MOTHERBOARD

    if cpu.socket != motherboard.socket:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INCOMPATIVEL,
            reason=(
                f"CPU usa socket {cpu.socket}, mas a placa-mãe é {motherboard.socket} — "
                "sockets incompatíveis fisicamente."
            ),
            additional_required_components=["motherboard"],
        )

    if not motherboard.supports_cpu_generations or not cpu.generation:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.COMPATIVEL_COM_RESSALVAS,
            reason=(
                "Sockets compatíveis, mas o catálogo não tem dados suficientes sobre suporte "
                "desta placa a esta geração específica de CPU — confirme na página de suporte "
                "de CPU/memória do fabricante antes de comprar."
            ),
        )

    if cpu.generation in motherboard.supports_cpu_generations:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.COMPATIVEL,
            reason="Socket e geração da CPU oficialmente suportados por esta placa-mãe.",
        )

    if motherboard.bios_notes:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.REQUER_ATUALIZACAO_BIOS,
            reason=motherboard.bios_notes,
        )

    return CompatibilityResult(
        relation=relation,
        status=CompatibilityStatus.INCOMPATIVEL,
        reason=(
            f"Placa-mãe não lista suporte à geração '{cpu.generation}' e o catálogo não tem "
            "nenhuma nota de atualização de BIOS para este caso."
        ),
        additional_required_components=["motherboard"],
    )


def check_motherboard_ram(
    motherboard: catalog_models.MotherboardModel, ram: catalog_models.RamKitModel
) -> CompatibilityResult:
    relation = CompatibilityRelation.MOTHERBOARD_RAM

    if motherboard.memory_type != ram.memory_type:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INCOMPATIVEL,
            reason=(
                f"Placa-mãe usa memória {motherboard.memory_type.value}, kit é "
                f"{ram.memory_type.value}."
            ),
        )

    if motherboard.memory_slots is not None and ram.modules_in_kit > motherboard.memory_slots:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INCOMPATIVEL,
            reason=(
                f"Kit tem {ram.modules_in_kit} módulos, mas a placa só tem "
                f"{motherboard.memory_slots} slots de memória."
            ),
        )

    total_capacity_gb = ram.capacity_gb_per_module * ram.modules_in_kit
    if motherboard.max_memory_gb is not None and total_capacity_gb > motherboard.max_memory_gb:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.COMPATIVEL_COM_RESSALVAS,
            reason=(
                f"Capacidade total do kit ({total_capacity_gb}GB) excede o máximo "
                f"oficialmente suportado pela placa ({motherboard.max_memory_gb}GB)."
            ),
        )

    if (
        motherboard.max_memory_speed_mhz is not None
        and ram.speed_mhz > motherboard.max_memory_speed_mhz
    ):
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.COMPATIVEL_COM_RESSALVAS,
            reason=(
                f"Kit roda a {ram.speed_mhz}MHz, mas a placa suporta oficialmente até "
                f"{motherboard.max_memory_speed_mhz}MHz — funcionará, mas nessa frequência "
                "reduzida (suporte a XMP/EXPO acima disso varia por placa)."
            ),
        )

    return CompatibilityResult(
        relation=relation,
        status=CompatibilityStatus.COMPATIVEL,
        reason="Tipo, capacidade e velocidade da memória dentro do suportado pela placa.",
    )


def check_gpu_psu(
    gpu: catalog_models.GpuModel, psu: catalog_models.PsuModel
) -> CompatibilityResult:
    relation = CompatibilityRelation.GPU_PSU

    if gpu.recommended_psu_watts is None:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INFORMACAO_INSUFICIENTE,
            reason="Catálogo não tem a potência de fonte recomendada para esta GPU.",
        )

    if psu.wattage < gpu.recommended_psu_watts:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INCOMPATIVEL,
            reason=(
                f"Fonte de {psu.wattage}W está abaixo dos {gpu.recommended_psu_watts}W "
                "recomendados para esta GPU."
            ),
            additional_required_components=["psu"],
        )

    if psu.wattage < gpu.recommended_psu_watts * 1.15:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.COMPATIVEL_COM_RESSALVAS,
            reason=(
                f"Fonte de {psu.wattage}W atende o mínimo recomendado "
                f"({gpu.recommended_psu_watts}W), mas com pouca margem para os demais "
                "componentes."
            ),
        )

    return CompatibilityResult(
        relation=relation,
        status=CompatibilityStatus.COMPATIVEL,
        reason="Potência da fonte confortavelmente acima do recomendado para esta GPU.",
    )


def check_pcie_interface(
    motherboard: catalog_models.MotherboardModel, gpu: catalog_models.GpuModel
) -> CompatibilityResult:
    relation = CompatibilityRelation.CPU_GPU_PCIE

    board_versions = [
        slot.get("version") for slot in (motherboard.pcie_slots or []) if slot.get("version")
    ]
    if not board_versions or not gpu.pcie_version:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INFORMACAO_INSUFICIENTE,
            reason="Dados insuficientes de versão PCIe da placa-mãe ou da GPU.",
        )

    try:
        board_max = max(float(v) for v in board_versions)
        gpu_version = float(gpu.pcie_version)
    except (TypeError, ValueError):
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INFORMACAO_INSUFICIENTE,
            reason="Não foi possível interpretar a versão PCIe informada no catálogo.",
        )

    if gpu_version > board_max:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.COMPATIVEL_COM_RESSALVAS,
            reason=(
                f"GPU é PCIe {gpu.pcie_version}, mas a placa oferece no máximo PCIe "
                f"{board_max:g}. PCIe é retrocompatível (a GPU funciona normalmente), mas "
                "roda na velocidade do slot mais antigo — o impacto real costuma ser pequeno "
                "na maioria dos jogos."
            ),
        )

    return CompatibilityResult(
        relation=relation,
        status=CompatibilityStatus.COMPATIVEL,
        reason="Interface PCIe da placa atende ou supera a exigida pela GPU.",
    )


def check_motherboard_storage(
    motherboard: catalog_models.MotherboardModel, storage: catalog_models.StorageModel
) -> CompatibilityResult:
    relation = CompatibilityRelation.MOTHERBOARD_STORAGE

    if storage.storage_type == StorageType.NVME_SSD:
        if not motherboard.m2_slots:
            return CompatibilityResult(
                relation=relation,
                status=CompatibilityStatus.INCOMPATIVEL,
                reason="Placa-mãe não tem slot M.2 disponível para um SSD NVMe.",
                additional_required_components=["motherboard"],
            )
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.COMPATIVEL,
            reason="Placa-mãe tem slot M.2 disponível para este SSD NVMe.",
        )

    return CompatibilityResult(
        relation=relation,
        status=CompatibilityStatus.COMPATIVEL,
        reason=(
            "Presume-se porta SATA disponível (praticamente universal em placas "
            "ATX/mATX/ITX modernas)."
        ),
    )


def check_case_gpu(
    case: catalog_models.CaseModel, gpu: catalog_models.GpuModel
) -> CompatibilityResult:
    relation = CompatibilityRelation.CASE_GPU

    if case.max_gpu_length_mm is None or gpu.length_mm is None:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INFORMACAO_INSUFICIENTE,
            reason="Comprimento máximo de GPU do gabinete ou comprimento da GPU não informado.",
        )

    if gpu.length_mm > case.max_gpu_length_mm:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INCOMPATIVEL,
            reason=(
                f"GPU tem {gpu.length_mm}mm, mas o gabinete suporta no máximo "
                f"{case.max_gpu_length_mm}mm de comprimento de placa de vídeo."
            ),
            additional_required_components=["case"],
        )

    if gpu.length_mm > case.max_gpu_length_mm - 10:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.COMPATIVEL_COM_RESSALVAS,
            reason=(
                "GPU cabe, mas com margem apertada — confira gerenciamento de cabos e fans "
                "frontais antes de finalizar a compra."
            ),
        )

    return CompatibilityResult(
        relation=relation,
        status=CompatibilityStatus.COMPATIVEL,
        reason="GPU cabe confortavelmente no gabinete.",
    )


def check_case_motherboard(
    case: catalog_models.CaseModel, motherboard: catalog_models.MotherboardModel
) -> CompatibilityResult:
    relation = CompatibilityRelation.CASE_MOTHERBOARD

    if not case.supported_form_factors or not motherboard.form_factor:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INFORMACAO_INSUFICIENTE,
            reason="Form factors suportados pelo gabinete ou da placa-mãe não informados.",
        )

    if motherboard.form_factor.value not in case.supported_form_factors:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INCOMPATIVEL,
            reason=f"Gabinete não lista suporte a placas {motherboard.form_factor.value}.",
            additional_required_components=["case"],
        )

    return CompatibilityResult(
        relation=relation,
        status=CompatibilityStatus.COMPATIVEL,
        reason="Gabinete suporta o form factor desta placa-mãe.",
    )


def check_cooler_cpu(
    cooler: catalog_models.CoolerModel, cpu: catalog_models.CpuModel
) -> CompatibilityResult:
    relation = CompatibilityRelation.COOLER_CPU

    if not cooler.supported_sockets:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INFORMACAO_INSUFICIENTE,
            reason="Sockets suportados pelo cooler não informados no catálogo.",
        )

    if cpu.socket not in cooler.supported_sockets:
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.INCOMPATIVEL,
            reason=f"Cooler não lista suporte ao socket {cpu.socket} desta CPU.",
            additional_required_components=["cooler"],
        )

    if (
        cooler.tdp_rating_watts is not None
        and cpu.tdp_watts is not None
        and cpu.tdp_watts > cooler.tdp_rating_watts
    ):
        return CompatibilityResult(
            relation=relation,
            status=CompatibilityStatus.COMPATIVEL_COM_RESSALVAS,
            reason=(
                f"TDP da CPU ({cpu.tdp_watts}W) excede a classificação do cooler "
                f"({cooler.tdp_rating_watts}W) — pode limitar o boost sob carga sustentada."
            ),
        )

    return CompatibilityResult(
        relation=relation,
        status=CompatibilityStatus.COMPATIVEL,
        reason="Socket suportado e dissipação adequada ao TDP da CPU.",
    )


def build_bundle(results: list[CompatibilityResult]) -> BundleUpgrade | None:
    """Agrega checks INCOMPATIVEL num único aviso de 'upgrade de conjunto'."""
    incompatible = [r for r in results if r.status == CompatibilityStatus.INCOMPATIVEL]
    components: set[str] = set()
    for result in incompatible:
        components.update(result.additional_required_components)
    if not components:
        return None

    reason = " ".join(result.reason for result in incompatible)
    return BundleUpgrade(components=sorted(components), reason=reason)


def _resolve(
    db: Session, model_name: str | None, getter: Callable[[Session, str], T | None], label: str
) -> T | None:
    if not model_name:
        return None
    obj = getter(db, model_name)
    if obj is None:
        raise NotFoundError(f"{label} '{model_name}' não encontrado no catálogo.")
    return obj


def run_compatibility_check(
    db: Session, request: CompatibilityCheckRequest
) -> CompatibilityCheckResponse:
    cpu = _resolve(db, request.cpu_model_name, catalog_service.get_cpu_by_model_name, "CPU")
    gpu = _resolve(db, request.gpu_model_name, catalog_service.get_gpu_by_model_name, "GPU")
    motherboard = _resolve(
        db,
        request.motherboard_model_name,
        catalog_service.get_motherboard_by_model_name,
        "Placa-mãe",
    )
    ram = _resolve(
        db, request.ram_model_name, catalog_service.get_ram_kit_by_model_name, "Kit de RAM"
    )
    storage = _resolve(
        db, request.storage_model_name, catalog_service.get_storage_by_model_name, "Armazenamento"
    )
    psu = _resolve(db, request.psu_model_name, catalog_service.get_psu_by_model_name, "Fonte")
    case = _resolve(db, request.case_model_name, catalog_service.get_case_by_model_name, "Gabinete")
    cooler = _resolve(
        db, request.cooler_model_name, catalog_service.get_cooler_by_model_name, "Cooler"
    )

    results: list[CompatibilityResult] = []
    if cpu and motherboard:
        results.append(check_cpu_motherboard(cpu, motherboard))
    if motherboard and ram:
        results.append(check_motherboard_ram(motherboard, ram))
    if gpu and psu:
        results.append(check_gpu_psu(gpu, psu))
    if motherboard and gpu:
        results.append(check_pcie_interface(motherboard, gpu))
    if motherboard and storage:
        results.append(check_motherboard_storage(motherboard, storage))
    if case and gpu:
        results.append(check_case_gpu(case, gpu))
    if case and motherboard:
        results.append(check_case_motherboard(case, motherboard))
    if cooler and cpu:
        results.append(check_cooler_cpu(cooler, cpu))

    return CompatibilityCheckResponse(results=results, bundle=build_bundle(results))
