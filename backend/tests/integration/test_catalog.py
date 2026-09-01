from app.modules.catalog import service


def test_list_cpus_empty(client):
    response = client.get("/catalog/cpus")
    assert response.status_code == 200
    assert response.json() == []


def test_import_and_list_cpus(client):
    payload = {
        "catalog_type": "cpu",
        "items": [
            {
                "manufacturer": "AMD",
                "model_name": "Ryzen 5 1600",
                "socket": "AM4",
                "cores": 6,
                "threads": 12,
                "performance_tier": 15,
                "substitute_names": ["Ryzen 5 3600"],
            },
            {
                "manufacturer": "AMD",
                "model_name": "Ryzen 5 3600",
                "socket": "AM4",
                "cores": 6,
                "threads": 12,
                "performance_tier": 35,
            },
        ],
    }
    import_response = client.post("/catalog/import", json=payload)
    assert import_response.status_code == 200
    assert import_response.json() == {"catalog_type": "cpu", "imported": 2}

    list_response = client.get("/catalog/cpus", params={"socket": "AM4"})
    assert list_response.status_code == 200
    names = {item["model_name"] for item in list_response.json()}
    assert names == {"Ryzen 5 1600", "Ryzen 5 3600"}


def test_import_is_idempotent_upsert(client):
    payload = {
        "catalog_type": "psu",
        "items": [{"model_name": "500W Bronze", "wattage": 500}],
    }
    client.post("/catalog/import", json=payload)
    payload["items"][0]["wattage"] = 550
    response = client.post("/catalog/import", json=payload)
    assert response.status_code == 200

    psus = client.get("/catalog/psus").json()
    assert len(psus) == 1
    assert psus[0]["wattage"] == 550


def test_seed_loader_populates_catalog(db_session):
    from app.modules.catalog.seed.load_seed import run as run_seed

    run_seed(db=db_session)

    cpus = service.list_cpus(db_session)
    gpus = service.list_gpus(db_session)
    assert len(cpus) > 0
    assert len(gpus) > 0
    assert service.list_motherboards(db_session)
    assert service.list_ram_kits(db_session)
    assert service.list_storage(db_session)
    assert service.list_psus(db_session)
    assert service.list_cases(db_session)
    assert service.list_coolers(db_session)

    # substitute_names do seed devem ter virado vínculos reais de substitutos
    assert any(cpu.substitutes for cpu in cpus)
    assert any(gpu.substitutes for gpu in gpus)


def test_model_name_filter_on_cpu_list(client):
    payload = {
        "catalog_type": "cpu",
        "items": [
            {"manufacturer": "AMD", "model_name": "Ryzen 5 1600", "socket": "AM4"},
            {"manufacturer": "AMD", "model_name": "Ryzen 5 3600", "socket": "AM4"},
        ],
    }
    client.post("/catalog/import", json=payload)

    response = client.get("/catalog/cpus", params={"model_name": "Ryzen 5 3600"})
    assert response.status_code == 200
    names = {item["model_name"] for item in response.json()}
    assert names == {"Ryzen 5 3600"}


def test_import_and_list_cases_and_coolers(client):
    case_payload = {
        "catalog_type": "case",
        "items": [
            {
                "model_name": "Lancool 215",
                "supported_form_factors": ["ATX", "MICRO_ATX"],
                "max_gpu_length_mm": 405,
            }
        ],
    }
    cooler_payload = {
        "catalog_type": "cooler",
        "items": [
            {
                "model_name": "Hyper 212 Black Edition",
                "cooler_type": "AIR",
                "supported_sockets": ["AM4", "AM5"],
                "height_mm": 159,
            }
        ],
    }

    assert client.post("/catalog/import", json=case_payload).status_code == 200
    assert client.post("/catalog/import", json=cooler_payload).status_code == 200

    cases = client.get("/catalog/cases").json()
    coolers = client.get("/catalog/coolers").json()
    assert cases[0]["model_name"] == "Lancool 215"
    assert coolers[0]["cooler_type"] == "AIR"
    assert coolers[0]["supported_sockets"] == ["AM4", "AM5"]


def test_upsert_cpu_and_set_substitutes(db_session):
    service.upsert_cpu(db_session, {"manufacturer": "AMD", "model_name": "A", "socket": "AM4"})
    service.upsert_cpu(db_session, {"manufacturer": "AMD", "model_name": "B", "socket": "AM4"})
    db_session.flush()
    service.set_cpu_substitutes(db_session, "A", ["B"])
    db_session.commit()

    cpu_a = service.get_cpu_by_model_name(db_session, "A")
    assert [c.model_name for c in cpu_a.substitutes] == ["B"]
