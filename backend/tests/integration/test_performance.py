def _import_cpu(client, model_name, tier):
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "cpu",
            "items": [
                {
                    "manufacturer": "AMD",
                    "model_name": model_name,
                    "socket": "AM4",
                    "performance_tier": tier,
                }
            ],
        },
    )


def _import_gpu(client, model_name, tier):
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "gpu",
            "items": [
                {"manufacturer": "AMD", "model_name": model_name, "performance_tier": tier}
            ],
        },
    )


def test_bottleneck_endpoint_returns_verdict(client):
    _import_cpu(client, "CPU Fraca", 15)
    _import_gpu(client, "GPU Forte", 80)

    response = client.post(
        "/performance/bottleneck",
        json={
            "cpu_model_name": "CPU Fraca",
            "gpu_model_name": "GPU Forte",
            "resolution": "1080P",
            "graphics_quality": "LOW",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "CPU_BOUND"
    assert body["limiting_component"] == "cpu"


def test_bottleneck_endpoint_422_when_tier_missing(client):
    _import_cpu(client, "CPU Sem Tier", None)
    _import_gpu(client, "GPU Com Tier", 50)

    response = client.post(
        "/performance/bottleneck",
        json={
            "cpu_model_name": "CPU Sem Tier",
            "gpu_model_name": "GPU Com Tier",
            "resolution": "1080P",
            "graphics_quality": "MEDIUM",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == "InsufficientDataError"


def test_bottleneck_endpoint_404_for_unknown_gpu(client):
    _import_cpu(client, "CPU Existe", 50)

    response = client.post(
        "/performance/bottleneck",
        json={
            "cpu_model_name": "CPU Existe",
            "gpu_model_name": "Não Existe",
            "resolution": "1080P",
            "graphics_quality": "MEDIUM",
        },
    )

    assert response.status_code == 404
