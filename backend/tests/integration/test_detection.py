from app.main import app
from app.modules.detection.collectors.manual import ManualOnlyCollector
from app.modules.detection.service import get_collector


def test_detection_run_endpoint_uses_overridden_collector(client):
    app.dependency_overrides[get_collector] = lambda: ManualOnlyCollector()
    try:
        response = client.get("/detection/run")
        assert response.status_code == 200
        body = response.json()
        assert body["field_status"]["cpu_model_name"] == "MANUAL_REQUIRED"
        assert body["snapshot"]["cpu_model_name"] is None
    finally:
        app.dependency_overrides.pop(get_collector, None)
