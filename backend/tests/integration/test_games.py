def _seed_gpus(client):
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "gpu",
            "items": [
                {"manufacturer": "AMD", "model_name": "GPU Forte", "performance_tier": 80},
                {"manufacturer": "AMD", "model_name": "GPU Fraca", "performance_tier": 20},
            ],
        },
    )


def _seed_game_with_benchmark(db_session):
    from app.modules.games import models

    game = models.Game(title="Jogo Teste", notes="dataset de teste")
    db_session.add(game)
    db_session.flush()
    db_session.add(
        models.GameBenchmark(
            game_id=game.id,
            gpu_id=_gpu_id(db_session, "GPU Forte"),
            resolution="1080P",
            avg_fps=90,
            test_cpu_model="CPU de Teste Forte",
            quality_preset_note="Preset não declarado pela fonte de teste.",
            source_name="Fonte de Teste",
            source_url="https://example.com/benchmark",
        )
    )
    db_session.commit()


def _gpu_id(db_session, model_name):
    from app.modules.catalog import service as catalog_service

    return catalog_service.get_gpu_by_model_name(db_session, model_name).id


def test_list_games_returns_seeded_titles(client, db_session):
    _seed_gpus(client)
    _seed_game_with_benchmark(db_session)

    response = client.get("/games/")
    assert response.status_code == 200
    assert response.json() == ["Jogo Teste"]


def test_fps_estimate_returns_real_sourced_data(client, db_session):
    _seed_gpus(client)
    _seed_game_with_benchmark(db_session)

    response = client.post(
        "/games/fps-estimate",
        json={
            "game_title": "Jogo Teste",
            "gpu_model_name": "GPU Forte",
            "resolution": "1080P",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["avg_fps"] == 90
    assert body["source_url"] == "https://example.com/benchmark"
    assert body["cpu_bottleneck_caveat"] is None


def test_fps_estimate_adds_cpu_bottleneck_caveat_when_cpu_much_weaker(client, db_session):
    _seed_gpus(client)
    _seed_game_with_benchmark(db_session)
    client.post(
        "/catalog/import",
        json={
            "catalog_type": "cpu",
            "items": [
                {
                    "manufacturer": "AMD",
                    "model_name": "CPU Muito Fraca",
                    "socket": "AM4",
                    "performance_tier": 5,
                }
            ],
        },
    )

    response = client.post(
        "/games/fps-estimate",
        json={
            "game_title": "Jogo Teste",
            "gpu_model_name": "GPU Forte",
            "cpu_model_name": "CPU Muito Fraca",
            "resolution": "1080P",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["avg_fps"] == 90
    assert body["cpu_bottleneck_caveat"] is not None


def test_fps_estimate_404_for_unknown_game(client, db_session):
    _seed_gpus(client)

    response = client.post(
        "/games/fps-estimate",
        json={"game_title": "Jogo Que Não Existe", "gpu_model_name": "GPU Forte"},
    )

    assert response.status_code == 404


def test_fps_estimate_422_when_no_benchmark_for_this_gpu(client, db_session):
    _seed_gpus(client)
    _seed_game_with_benchmark(db_session)

    response = client.post(
        "/games/fps-estimate",
        json={"game_title": "Jogo Teste", "gpu_model_name": "GPU Fraca"},
    )

    assert response.status_code == 422
    assert response.json()["error"] == "InsufficientDataError"
