def _auth_headers(client, email="analyst@example.com"):
    client.post("/users/register", json={"email": email, "password": "supersecret1"})
    login = client.post("/users/login", json={"email": email, "password": "supersecret1"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_system(client):
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "cpu",
            "items": [
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
            ],
        },
    )
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "gpu",
            "items": [{"manufacturer": "AMD", "model_name": "GPU Forte", "performance_tier": 80}],
        },
    )
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "motherboard",
            "items": [
                {
                    "manufacturer": "ASRock",
                    "model_name": "B450 Board",
                    "socket": "AM4",
                    "chipset": "B450",
                    "memory_type": "DDR4",
                }
            ],
        },
    )
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "psu",
            "items": [{"model_name": "450W Bronze", "wattage": 450}],
        },
    )


def test_run_analysis_requires_auth(client):
    response = client.post(
        "/analysis/run",
        json={"system": {"cpu_model_name": "CPU Fraca"}, "profile": "ECONOMICO"},
    )
    assert response.status_code in (401, 403)


def test_run_analysis_persists_and_returns_full_report(client):
    _seed_system(client)
    headers = _auth_headers(client)

    response = client.post(
        "/analysis/run",
        headers=headers,
        json={
            "system": {
                "cpu_model_name": "CPU Fraca",
                "gpu_model_name": "GPU Forte",
                "motherboard_model_name": "B450 Board",
                "psu_model_name": "450W Bronze",
            },
            "profile": "ECONOMICO",
            "resolution": "1080P",
            "graphics_quality": "LOW",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"] == "ECONOMICO"
    assert body["report"]["bottleneck"]["verdict"] == "CPU_BOUND"
    assert len(body["report"]["current_compatibility"]) > 0
    slots = {r["slot"] for r in body["report"]["recommendations"]}
    assert "cpu" in slots


def test_history_lists_only_own_analyses(client):
    _seed_system(client)
    headers_a = _auth_headers(client, "alice@example.com")
    headers_b = _auth_headers(client, "bob@example.com")

    run_payload = {"system": {"cpu_model_name": "CPU Fraca"}, "profile": "ECONOMICO"}
    run_response = client.post("/analysis/run", headers=headers_a, json=run_payload)
    assert run_response.status_code == 200

    history_a = client.get("/analysis/history", headers=headers_a).json()
    history_b = client.get("/analysis/history", headers=headers_b).json()
    assert len(history_a) == 1
    assert len(history_b) == 0


def test_history_entry_not_owned_returns_404(client):
    _seed_system(client)
    headers_a = _auth_headers(client, "owner@example.com")
    headers_b = _auth_headers(client, "intruder@example.com")

    run_payload = {"system": {"cpu_model_name": "CPU Fraca"}, "profile": "ECONOMICO"}
    run_response = client.post("/analysis/run", headers=headers_a, json=run_payload)
    history_id = run_response.json()["id"]

    response = client.get(f"/analysis/history/{history_id}", headers=headers_b)
    assert response.status_code == 404

    own_response = client.get(f"/analysis/history/{history_id}", headers=headers_a)
    assert own_response.status_code == 200
