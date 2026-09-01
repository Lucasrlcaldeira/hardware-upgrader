def test_compatibility_check_endpoint_detects_bundle(client):
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "cpu",
            "items": [{"manufacturer": "AMD", "model_name": "Ryzen 5 5600", "socket": "AM5"}],
        },
    )
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "motherboard",
            "items": [
                {
                    "manufacturer": "ASRock",
                    "model_name": "A320M-DGS",
                    "socket": "AM4",
                    "chipset": "A320",
                    "memory_type": "DDR4",
                }
            ],
        },
    )

    response = client.post(
        "/compatibility/check",
        json={"cpu_model_name": "Ryzen 5 5600", "motherboard_model_name": "A320M-DGS"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["status"] == "INCOMPATIVEL"
    assert body["bundle"]["components"] == ["motherboard"]


def test_compatibility_check_endpoint_404_for_unknown_component(client):
    response = client.post("/compatibility/check", json={"cpu_model_name": "Não Existe"})
    assert response.status_code == 404
    assert response.json()["error"] == "NotFoundError"


def test_compatibility_check_endpoint_empty_when_nothing_provided(client):
    response = client.post("/compatibility/check", json={})
    assert response.status_code == 200
    assert response.json() == {"results": [], "bundle": None}
