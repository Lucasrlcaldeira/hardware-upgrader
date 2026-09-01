from app.modules.detection.collectors.manual import ManualOnlyCollector
from app.modules.detection.enums import DetectionSource
from app.modules.detection.schemas import RamInfo, StorageDeviceInfo
from app.modules.detection.service import run_detection


class FakeCollector(ManualOnlyCollector):
    """Detecta alguns campos e deixa outros faltando, para testar o mix."""

    def detect_cpu(self):
        return "Ryzen 5 5600"

    def detect_ram(self):
        return RamInfo(capacity_gb=16, speed_mhz=3200, modules=2)

    def detect_storage(self):
        return [StorageDeviceInfo(capacity_gb=512, model_name="Samsung 970 EVO")]


def test_manual_collector_everything_requires_manual_input():
    result = run_detection(ManualOnlyCollector())

    assert all(
        status == DetectionSource.MANUAL_REQUIRED for status in result.field_status.values()
    )
    assert result.snapshot.cpu_model_name is None
    assert result.snapshot.storage_devices == []


def test_partial_detection_marks_only_missing_fields_as_manual():
    result = run_detection(FakeCollector())

    assert result.field_status["cpu_model_name"] == DetectionSource.DETECTED
    assert result.field_status["ram_capacity_gb"] == DetectionSource.DETECTED
    assert result.field_status["ram_speed_mhz"] == DetectionSource.DETECTED
    assert result.field_status["storage_devices"] == DetectionSource.DETECTED
    assert result.field_status["gpu_model_name"] == DetectionSource.MANUAL_REQUIRED
    assert result.field_status["psu_model_name"] == DetectionSource.MANUAL_REQUIRED

    assert result.snapshot.cpu_model_name == "Ryzen 5 5600"
    assert result.snapshot.ram_capacity_gb == 16
    assert result.snapshot.storage_devices[0].model_name == "Samsung 970 EVO"
