import pytest

from app.main import app
from app.modules.games.steam_client import (
    SteamApp,
    SteamSearchItem,
    SteamUnavailableError,
    get_steam_client,
)

MINIMUM_HTML = (
    '<strong>Minimum:</strong><br><ul class="bb_ul">'
    "<li>Requires a 64-bit processor and operating system<br></li>"
    "<li><strong>OS:</strong> 64-bit Windows 10<br></li>"
    "<li><strong>Processor:</strong> Intel Core i5-4460 / AMD FX-6300<br></li>"
    "<li><strong>Memory:</strong> 8 GB RAM<br></li>"
    "<li><strong>Graphics:</strong> NVIDIA GeForce GTX 960 2GB / AMD Radeon R9 280 3GB<br></li>"
    "<li><strong>Storage:</strong> 50 GB available space</li></ul>"
)
RECOMMENDED_HTML = (
    '<strong>Recommended:</strong><br><ul class="bb_ul">'
    "<li><strong>Processor:</strong> Intel Core i7-8700K / AMD Ryzen 5 3600X<br></li>"
    "<li><strong>Memory:</strong> 16 GB RAM<br></li>"
    "<li><strong>Graphics:</strong> NVIDIA GeForce RTX 2070 SUPER 8GB<br></li>"
    "<li><strong>Storage:</strong> 50 GB available space<br></li>"
    "<li><strong>Additional Notes:</strong> SSD required.</li></ul>"
)

GAME = SteamApp(
    app_id=100,
    name="Jogo Teste",
    header_image="https://example.com/header.jpg",
    minimum_html=MINIMUM_HTML,
    recommended_html=RECOMMENDED_HTML,
)
GAME_WITHOUT_REQUIREMENTS = SteamApp(
    app_id=200, name="Sem Requisitos", header_image=None, minimum_html=None, recommended_html=None
)


class FakeSteamClient:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.apps = {GAME.app_id: GAME, GAME_WITHOUT_REQUIREMENTS.app_id: GAME_WITHOUT_REQUIREMENTS}

    def search(self, term):
        if self.fail:
            raise SteamUnavailableError("Steam fora do ar")
        return [
            SteamSearchItem(app_id=app.app_id, name=app.name, image_url=app.header_image)
            for app in self.apps.values()
            if term.lower() in app.name.lower()
        ]

    def get_app(self, app_id):
        if self.fail:
            raise SteamUnavailableError("Steam fora do ar")
        return self.apps[app_id]


@pytest.fixture()
def steam(client):
    fake = FakeSteamClient()
    app.dependency_overrides[get_steam_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_steam_client, None)


def _seed_catalog(client):
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "cpu",
            "items": [
                {
                    "manufacturer": "AMD",
                    "model_name": "Ryzen 5 3600",
                    "socket": "AM4",
                    "performance_tier": 35,
                },
                {
                    "manufacturer": "AMD",
                    "model_name": "Ryzen 7 7700X",
                    "socket": "AM5",
                    "performance_tier": 80,
                },
            ],
        },
    )
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "gpu",
            "items": [
                {
                    "manufacturer": "NVIDIA",
                    "model_name": "GeForce RTX 3060",
                    "vram_gb": 12,
                    "performance_tier": 47,
                }
            ],
        },
    )
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "ram",
            "items": [
                {
                    "model_name": "Kit 2x16GB DDR4",
                    "memory_type": "DDR4",
                    "speed_mhz": 3200,
                    "capacity_gb_per_module": 16,
                    "modules_in_kit": 2,
                }
            ],
        },
    )


def _detected(**overrides):
    snapshot = {
        "cpu_model_name": None,
        "gpu_model_name": None,
        "ram_capacity_gb": 16,
        "storage_devices": [{"storage_type": "NVME_SSD", "capacity_gb": 1000, "model_name": "SSD"}],
        "free_disk_space_gb": 300,
        "os_name": "Windows",
        "os_version": "10 (build 10.0.22631)",
    }
    snapshot.update(overrides)
    return snapshot


def _check(client, **payload):
    response = client.post("/games/requirements-check", json={"app_id": GAME.app_id, **payload})
    assert response.status_code == 200, response.text
    return response.json()


def _checks_by_component(tier):
    return {c["component"]: c for c in tier["checks"]}


def test_search_returns_steam_results(client, steam):
    response = client.get("/games/search", params={"q": "jogo"})

    assert response.status_code == 200
    assert response.json() == [
        {"app_id": 100, "name": "Jogo Teste", "image_url": "https://example.com/header.jpg"}
    ]


def test_search_rejects_too_short_terms(client, steam):
    assert client.get("/games/search", params={"q": "a"}).status_code == 422


def test_meets_minimum_but_not_recommended_names_the_component_holding_it_back(client, steam):
    _seed_catalog(client)

    body = _check(
        client,
        system={"cpu_model_name": "Ryzen 5 3600", "gpu_model_name": "GeForce RTX 3060"},
        detected=_detected(),
    )

    assert body["name"] == "Jogo Teste"
    assert body["store_url"] == "https://store.steampowered.com/app/100"
    current = body["current"]
    assert current["verdict"] == "RODA_NO_MINIMO"
    assert current["minimum"]["status"] == "ATENDE"
    assert current["recommended"]["status"] == "NAO_ATENDE"

    recommended = _checks_by_component(current["recommended"])
    # Ryzen 5 3600 fica abaixo de "i7-8700K / Ryzen 5 3600X" — a 3600X é a opção mais
    # modesta e é um pouco mais forte que a 3600 sem X.
    assert recommended["cpu"]["status"] == "NAO_ATENDE"
    assert recommended["gpu"]["status"] == "ATENDE"
    assert recommended["ram"]["status"] == "ATENDE"
    assert "processador" in current["verdict_text"]


def test_upgraded_system_is_evaluated_separately(client, steam):
    _seed_catalog(client)

    body = _check(
        client,
        system={"cpu_model_name": "Ryzen 5 3600", "gpu_model_name": "GeForce RTX 3060"},
        detected=_detected(),
        upgraded_system={"cpu_model_name": "Ryzen 7 7700X", "gpu_model_name": "GeForce RTX 3060"},
    )

    assert body["current"]["verdict"] == "RODA_NO_MINIMO"
    assert body["upgraded"]["verdict"] == "RODA_NO_RECOMENDADO"


def test_uses_detected_hardware_when_nothing_was_picked_from_the_catalog(client, steam):
    _seed_catalog(client)

    body = _check(
        client,
        detected=_detected(
            cpu_model_name="Intel(R) Core(TM) i5-4460  CPU @ 3.20GHz",
            gpu_model_name="NVIDIA GeForce GTX 970",
        ),
    )

    minimum = _checks_by_component(body["current"]["minimum"])
    assert minimum["cpu"]["status"] == "ATENDE"
    assert minimum["cpu"]["yours"] == "Core i5-4460"
    assert minimum["gpu"]["status"] == "ATENDE"
    # GTX 970 não está no catálogo, então não sabemos a VRAM dela: vira só aviso, porque a
    # comparação de modelo já mostrou que ela supera a placa pedida.
    assert minimum["vram"]["status"] == "NAO_DETERMINADO"
    assert minimum["vram"]["counts_for_verdict"] is False
    assert body["current"]["verdict"] == "RODA_NO_MINIMO"


def test_below_minimum_when_ram_is_short(client, steam):
    _seed_catalog(client)

    body = _check(
        client,
        system={"cpu_model_name": "Ryzen 5 3600", "gpu_model_name": "GeForce RTX 3060"},
        detected=_detected(ram_capacity_gb=4),
    )

    current = body["current"]
    assert current["verdict"] == "ABAIXO_DO_MINIMO"
    assert _checks_by_component(current["minimum"])["ram"]["status"] == "NAO_ATENDE"
    assert "memória RAM" in current["verdict_text"]


def test_catalog_ram_kit_takes_priority_over_detected_capacity(client, steam):
    _seed_catalog(client)

    body = _check(
        client,
        system={"ram_model_name": "Kit 2x16GB DDR4"},
        detected=_detected(ram_capacity_gb=4),
    )

    ram = _checks_by_component(body["current"]["recommended"])["ram"]
    assert ram["yours"] == "32 GB"
    assert ram["status"] == "ATENDE"


def test_unrecognized_laptop_gpu_is_never_treated_as_its_desktop_version(client, steam):
    _seed_catalog(client)

    body = _check(
        client,
        system={"cpu_model_name": "Ryzen 7 7700X"},
        detected=_detected(gpu_model_name="NVIDIA GeForce RTX 3060 Laptop GPU"),
    )

    gpu = _checks_by_component(body["current"]["minimum"])["gpu"]
    assert gpu["status"] == "NAO_DETERMINADO"
    assert gpu["yours"] == "NVIDIA GeForce RTX 3060 Laptop GPU"
    assert body["current"]["verdict"] == "INDETERMINADO"


def test_storage_and_ssd_issues_warn_without_changing_the_verdict(client, steam):
    _seed_catalog(client)

    body = _check(
        client,
        system={"cpu_model_name": "Ryzen 7 7700X", "gpu_model_name": "GeForce RTX 3060"},
        detected=_detected(
            free_disk_space_gb=20,
            storage_devices=[{"storage_type": "HDD", "capacity_gb": 1000, "model_name": "HD"}],
        ),
    )

    current = body["current"]
    assert current["verdict"] == "RODA_NO_RECOMENDADO"
    storage = _checks_by_component(current["recommended"])["storage"]
    assert storage["status"] == "NAO_ATENDE"
    assert storage["counts_for_verdict"] is False
    assert "SSD" in storage["explanation"]
    assert "armazenamento" in current["verdict_text"]


def test_game_without_pc_requirements_returns_422(client, steam):
    response = client.post(
        "/games/requirements-check", json={"app_id": GAME_WITHOUT_REQUIREMENTS.app_id}
    )

    assert response.status_code == 422
    assert "não lista requisitos" in response.json()["message"]


def test_steam_unavailable_returns_502(client, steam):
    steam.fail = True

    response = client.post("/games/requirements-check", json={"app_id": GAME.app_id})

    assert response.status_code == 502
    assert response.json()["error"] == "SteamUnavailableError"
