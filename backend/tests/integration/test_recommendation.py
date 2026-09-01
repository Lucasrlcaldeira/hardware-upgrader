def _import(client, catalog_type, items):
    response = client.post("/catalog/import", json={"catalog_type": catalog_type, "items": items})
    assert response.status_code == 200


def _seed_cpu_bound_system(client):
    _import(
        client,
        "cpu",
        [
            {
                "manufacturer": "AMD",
                "model_name": "CPU Fraca",
                "socket": "AM4",
                "performance_tier": 15,
            },
            {
                "manufacturer": "AMD",
                "model_name": "CPU Media AM4",
                "socket": "AM4",
                "performance_tier": 40,
            },
            {
                "manufacturer": "AMD",
                "model_name": "CPU Forte AM5",
                "socket": "AM5",
                "performance_tier": 90,
                "price_range_brl_min": 2000,
                "price_range_brl_max": 2200,
            },
        ],
    )
    _import(
        client,
        "gpu",
        [{"manufacturer": "AMD", "model_name": "GPU Forte", "performance_tier": 80}],
    )
    _import(
        client,
        "motherboard",
        [
            {
                "manufacturer": "ASRock",
                "model_name": "B450 Board",
                "socket": "AM4",
                "chipset": "B450",
                "memory_type": "DDR4",
            }
        ],
    )


def test_recommend_cpu_when_cpu_bound(client):
    _seed_cpu_bound_system(client)

    response = client.post(
        "/recommendation/generate",
        json={
            "system": {
                "cpu_model_name": "CPU Fraca",
                "gpu_model_name": "GPU Forte",
                "motherboard_model_name": "B450 Board",
            },
            "profile": "ECONOMICO",
            "resolution": "1080P",
            "graphics_quality": "LOW",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["bottleneck"]["verdict"] == "CPU_BOUND"
    slots = {r["slot"] for r in body["recommendations"]}
    assert "cpu" in slots
    assert "gpu" not in slots

    cpu_rec = next(r for r in body["recommendations"] if r["slot"] == "cpu")
    # Perfil ECONOMICO deve preferir manter o socket atual (evita upgrade de conjunto)
    assert cpu_rec["recommended_model_name"] == "CPU Media AM4"
    assert cpu_rec["priority"] == "ALTA"


def test_alto_desempenho_profile_may_cross_socket_and_bundle(client):
    _seed_cpu_bound_system(client)

    response = client.post(
        "/recommendation/generate",
        json={
            "system": {
                "cpu_model_name": "CPU Fraca",
                "gpu_model_name": "GPU Forte",
                "motherboard_model_name": "B450 Board",
            },
            "profile": "ALTO_DESEMPENHO",
            "resolution": "1080P",
            "graphics_quality": "LOW",
        },
    )

    assert response.status_code == 200
    body = response.json()
    cpu_rec = next(r for r in body["recommendations"] if r["slot"] == "cpu")
    assert cpu_rec["recommended_model_name"] == "CPU Forte AM5"
    assert "motherboard" in cpu_rec["additional_required_components"]
    assert body["bundle"] is not None
    assert "motherboard" in body["bundle"]["components"]


def test_recommends_ssd_upgrade_for_hdd_storage(client):
    _import(
        client,
        "storage",
        [
            {"model_name": "HD Antigo", "storage_type": "HDD", "capacity_gb": 1000},
            {"model_name": "SSD Sata Novo", "storage_type": "SATA_SSD", "capacity_gb": 1000},
        ],
    )

    response = client.post(
        "/recommendation/generate",
        json={
            "system": {"storage_model_name": "HD Antigo"},
            "profile": "CUSTO_BENEFICIO",
        },
    )

    assert response.status_code == 200
    body = response.json()
    storage_rec = next(r for r in body["recommendations"] if r["slot"] == "storage")
    assert storage_rec["recommended_model_name"] == "SSD Sata Novo"


def test_recommends_ram_capacity_upgrade(client):
    _import(
        client,
        "ram",
        [
            {
                "model_name": "8GB Kit",
                "memory_type": "DDR4",
                "speed_mhz": 2666,
                "capacity_gb_per_module": 4,
                "modules_in_kit": 2,
            },
            {
                "model_name": "16GB Kit",
                "memory_type": "DDR4",
                "speed_mhz": 3200,
                "capacity_gb_per_module": 8,
                "modules_in_kit": 2,
            },
        ],
    )

    response = client.post(
        "/recommendation/generate",
        json={"system": {"ram_model_name": "8GB Kit"}, "profile": "ECONOMICO"},
    )

    assert response.status_code == 200
    body = response.json()
    ram_rec = next(r for r in body["recommendations"] if r["slot"] == "ram")
    assert ram_rec["recommended_model_name"] == "16GB Kit"
    assert ram_rec["priority"] == "ALTA"


def test_no_recommendations_when_nothing_flagged(client):
    _import(
        client,
        "cpu",
        [
            {
                "manufacturer": "AMD",
                "model_name": "CPU Única",
                "socket": "AM4",
                "performance_tier": 50,
            }
        ],
    )

    response = client.post(
        "/recommendation/generate",
        json={"system": {"cpu_model_name": "CPU Única"}, "profile": "ECONOMICO"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"] == []
    assert body["bundle"] is None


def test_404_for_unknown_component_in_system(client):
    response = client.post(
        "/recommendation/generate",
        json={"system": {"cpu_model_name": "Não Existe"}, "profile": "ECONOMICO"},
    )
    assert response.status_code == 404
