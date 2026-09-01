from app.modules.catalog.enums import CoolerType, FormFactor, MemoryType, StorageType
from app.modules.catalog.models import (
    CaseModel,
    CoolerModel,
    CpuModel,
    GpuModel,
    MotherboardModel,
    PsuModel,
    RamKitModel,
    StorageModel,
)
from app.modules.compatibility.enums import CompatibilityStatus
from app.modules.compatibility.service import (
    build_bundle,
    check_case_gpu,
    check_case_motherboard,
    check_cooler_cpu,
    check_cpu_motherboard,
    check_gpu_psu,
    check_motherboard_ram,
    check_motherboard_storage,
    check_pcie_interface,
)


def test_check_cpu_motherboard_incompatible_socket():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD")
    board = MotherboardModel(
        model_name="B", socket="AM5", chipset="B650", manufacturer="ASRock",
        memory_type=MemoryType.DDR5,
    )
    result = check_cpu_motherboard(cpu, board)
    assert result.status == CompatibilityStatus.INCOMPATIVEL
    assert "motherboard" in result.additional_required_components


def test_check_cpu_motherboard_requires_bios_update():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD", generation="Zen 3")
    board = MotherboardModel(
        model_name="B", socket="AM4", chipset="B450", manufacturer="ASRock",
        memory_type=MemoryType.DDR4, supports_cpu_generations=["Zen 1", "Zen 2"],
        bios_notes="Requer atualização de BIOS para suportar Zen 3.",
    )
    result = check_cpu_motherboard(cpu, board)
    assert result.status == CompatibilityStatus.REQUER_ATUALIZACAO_BIOS


def test_check_cpu_motherboard_insufficient_data():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD")
    board = MotherboardModel(
        model_name="B", socket="AM4", chipset="B450", manufacturer="ASRock",
        memory_type=MemoryType.DDR4,
    )
    result = check_cpu_motherboard(cpu, board)
    assert result.status == CompatibilityStatus.COMPATIVEL_COM_RESSALVAS


def test_check_motherboard_ram_wrong_memory_type():
    board = MotherboardModel(
        model_name="B", socket="AM4", chipset="B450", manufacturer="ASRock",
        memory_type=MemoryType.DDR4,
    )
    ram = RamKitModel(
        model_name="R", memory_type=MemoryType.DDR5, speed_mhz=6000,
        capacity_gb_per_module=16, modules_in_kit=2,
    )
    result = check_motherboard_ram(board, ram)
    assert result.status == CompatibilityStatus.INCOMPATIVEL


def test_check_motherboard_ram_exceeds_speed():
    board = MotherboardModel(
        model_name="B", socket="AM4", chipset="B450", manufacturer="ASRock",
        memory_type=MemoryType.DDR4, max_memory_speed_mhz=3200, memory_slots=4,
    )
    ram = RamKitModel(
        model_name="R", memory_type=MemoryType.DDR4, speed_mhz=3600,
        capacity_gb_per_module=8, modules_in_kit=2,
    )
    result = check_motherboard_ram(board, ram)
    assert result.status == CompatibilityStatus.COMPATIVEL_COM_RESSALVAS


def test_check_gpu_psu_underpowered():
    gpu = GpuModel(model_name="G", manufacturer="AMD", recommended_psu_watts=550)
    psu = PsuModel(model_name="P", wattage=450)
    result = check_gpu_psu(gpu, psu)
    assert result.status == CompatibilityStatus.INCOMPATIVEL
    assert "psu" in result.additional_required_components


def test_check_gpu_psu_insufficient_data():
    gpu = GpuModel(model_name="G", manufacturer="AMD")
    psu = PsuModel(model_name="P", wattage=650)
    result = check_gpu_psu(gpu, psu)
    assert result.status == CompatibilityStatus.INFORMACAO_INSUFICIENTE


def test_check_pcie_interface_backward_compatible_with_caveat():
    board = MotherboardModel(
        model_name="B", socket="AM4", chipset="B450", manufacturer="ASRock",
        memory_type=MemoryType.DDR4, pcie_slots=[{"version": "3.0", "lanes": 16, "count": 1}],
    )
    gpu = GpuModel(model_name="G", manufacturer="AMD", pcie_version="4.0")
    result = check_pcie_interface(board, gpu)
    assert result.status == CompatibilityStatus.COMPATIVEL_COM_RESSALVAS


def test_check_motherboard_storage_nvme_without_m2_slot():
    board = MotherboardModel(
        model_name="B", socket="AM4", chipset="B450", manufacturer="ASRock",
        memory_type=MemoryType.DDR4, m2_slots=0,
    )
    storage = StorageModel(model_name="S", storage_type=StorageType.NVME_SSD)
    result = check_motherboard_storage(board, storage)
    assert result.status == CompatibilityStatus.INCOMPATIVEL


def test_check_case_gpu_too_long():
    case = CaseModel(model_name="C", max_gpu_length_mm=300)
    gpu = GpuModel(model_name="G", manufacturer="AMD", length_mm=320)
    result = check_case_gpu(case, gpu)
    assert result.status == CompatibilityStatus.INCOMPATIVEL
    assert "case" in result.additional_required_components


def test_check_case_motherboard_unsupported_form_factor():
    case = CaseModel(model_name="C", supported_form_factors=["MINI_ITX"])
    board = MotherboardModel(
        model_name="B", socket="AM4", chipset="B450", manufacturer="ASRock",
        memory_type=MemoryType.DDR4, form_factor=FormFactor.ATX,
    )
    result = check_case_motherboard(case, board)
    assert result.status == CompatibilityStatus.INCOMPATIVEL


def test_check_cooler_cpu_unsupported_socket():
    cooler = CoolerModel(
        model_name="K", cooler_type=CoolerType.AIR, supported_sockets=["LGA1700"]
    )
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD")
    result = check_cooler_cpu(cooler, cpu)
    assert result.status == CompatibilityStatus.INCOMPATIVEL
    assert "cooler" in result.additional_required_components


def test_check_cooler_cpu_tdp_exceeds_rating():
    cooler = CoolerModel(
        model_name="K", cooler_type=CoolerType.AIR, supported_sockets=["AM4"],
        tdp_rating_watts=65,
    )
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD", tdp_watts=105)
    result = check_cooler_cpu(cooler, cpu)
    assert result.status == CompatibilityStatus.COMPATIVEL_COM_RESSALVAS


def test_build_bundle_aggregates_incompatible_components():
    cpu = CpuModel(model_name="A", socket="AM5", manufacturer="AMD")
    board = MotherboardModel(
        model_name="B", socket="AM4", chipset="B450", manufacturer="ASRock",
        memory_type=MemoryType.DDR4,
    )
    gpu = GpuModel(model_name="G", manufacturer="AMD", recommended_psu_watts=550)
    psu = PsuModel(model_name="P", wattage=450)

    results = [check_cpu_motherboard(cpu, board), check_gpu_psu(gpu, psu)]
    bundle = build_bundle(results)

    assert bundle is not None
    assert bundle.components == ["motherboard", "psu"]


def test_build_bundle_returns_none_when_all_compatible():
    cpu = CpuModel(model_name="A", socket="AM4", manufacturer="AMD")
    board = MotherboardModel(
        model_name="B", socket="AM4", chipset="B450", manufacturer="ASRock",
        memory_type=MemoryType.DDR4, supports_cpu_generations=["Zen 1"],
    )
    cpu.generation = "Zen 1"
    results = [check_cpu_motherboard(cpu, board)]
    assert build_bundle(results) is None
