"""Cliente da loja Steam: busca de jogos e requisitos de PC de um jogo.

Usa os mesmos endpoints JSON que alimentam a página da loja (store.steampowered.com), sem
precisar de chave de API:

- /api/storesearch/?term=...       -> busca por nome
- /api/appdetails?appids=...       -> detalhes do jogo, incluindo pc_requirements

Pedimos tudo em inglês (l=english) porque é o formato de requisitos mais padronizado entre
jogos — os rótulos são traduzidos só na hora de mostrar para o usuário.
"""

import re
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.exceptions import DomainError, NotFoundError

_STORE_BASE_URL = "https://store.steampowered.com"
_TIMEOUT_SECONDS = 10.0
_SEARCH_LIMIT = 10

# Requisitos de um jogo quase nunca mudam; a busca muda um pouco mais (lançamentos). O
# cache também nos protege do limite de requisições da Steam (~200 a cada 5 min no
# appdetails), já que a mesma tela consulta o mesmo jogo várias vezes.
_APP_TTL_SECONDS = 6 * 60 * 60
_SEARCH_TTL_SECONDS = 60 * 60

_STORE_URL_PATTERN = re.compile(r"store\.steampowered\.com/app/(\d+)", re.IGNORECASE)


class SteamUnavailableError(DomainError):
    status_code = 502


@dataclass(frozen=True)
class SteamSearchItem:
    app_id: int
    name: str
    image_url: str | None


@dataclass(frozen=True)
class SteamApp:
    app_id: int
    name: str
    header_image: str | None
    minimum_html: str | None
    recommended_html: str | None

    @property
    def store_url(self) -> str:
        return f"{_STORE_BASE_URL}/app/{self.app_id}"


class _TtlCache:
    """Cache em memória mínimo, seguro entre threads (o FastAPI roda handlers síncronos
    num pool de threads)."""

    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._data: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: Any) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            stored_at, value = item
            if time.monotonic() - stored_at > self._ttl:
                del self._data[key]
                return None
            return value

    def set(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic(), value)


def parse_app_id(term: str) -> int | None:
    """Aceita um link da loja ("store.steampowered.com/app/1091500/...") ou o número do app."""
    term = term.strip()
    match = _STORE_URL_PATTERN.search(term)
    if match:
        return int(match.group(1))
    return int(term) if term.isdigit() else None


class SteamStoreClient:
    def __init__(self, http_client: httpx.Client | None = None):
        self._http = http_client or httpx.Client(
            base_url=_STORE_BASE_URL,
            timeout=_TIMEOUT_SECONDS,
            headers={"User-Agent": "HardwareUpgrader/0.1"},
        )
        self._app_cache = _TtlCache(_APP_TTL_SECONDS)
        self._search_cache = _TtlCache(_SEARCH_TTL_SECONDS)

    def _get_json(self, path: str, params: dict[str, Any]) -> Any:
        try:
            response = self._http.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SteamUnavailableError(
                "Não conseguimos falar com a loja da Steam agora. Confira sua conexão com a "
                "internet e tente de novo em alguns instantes."
            ) from exc

    def search(self, term: str) -> list[SteamSearchItem]:
        app_id = parse_app_id(term)
        if app_id is not None:
            app = self.get_app(app_id)
            return [SteamSearchItem(app_id=app.app_id, name=app.name, image_url=app.header_image)]

        key = term.strip().lower()
        cached = self._search_cache.get(key)
        if cached is not None:
            return cached

        payload = self._get_json(
            "/api/storesearch/", {"term": term.strip(), "l": "english", "cc": "BR"}
        )
        items = [
            SteamSearchItem(
                app_id=int(item["id"]),
                name=item.get("name", ""),
                image_url=item.get("tiny_image"),
            )
            for item in (payload or {}).get("items", [])
            if item.get("type") == "app" and item.get("id")
        ][:_SEARCH_LIMIT]
        self._search_cache.set(key, items)
        return items

    def get_app(self, app_id: int) -> SteamApp:
        cached = self._app_cache.get(app_id)
        if cached is not None:
            return cached

        payload = self._get_json(
            "/api/appdetails", {"appids": app_id, "l": "english", "cc": "BR", "filters": "basic"}
        )
        entry = (payload or {}).get(str(app_id)) or {}
        if not entry.get("success") or not entry.get("data"):
            raise NotFoundError(f"Não achamos nenhum jogo com o ID {app_id} na loja da Steam.")

        data = entry["data"]
        # Quando o jogo não publica requisitos de PC, a Steam devolve uma lista vazia em vez
        # de um objeto — por isso o isinstance.
        requirements = data.get("pc_requirements")
        requirements = requirements if isinstance(requirements, dict) else {}

        app = SteamApp(
            app_id=app_id,
            name=data.get("name", f"App {app_id}"),
            header_image=data.get("header_image"),
            minimum_html=requirements.get("minimum"),
            recommended_html=requirements.get("recommended"),
        )
        self._app_cache.set(app_id, app)
        return app


_default_client: SteamStoreClient | None = None
_default_client_lock = threading.Lock()


def get_steam_client() -> SteamStoreClient:
    """Dependência FastAPI. Uma instância por processo, para o cache valer entre requisições.

    Testável via `app.dependency_overrides[get_steam_client] = ...`, no mesmo padrão de
    `get_db` e `get_collector`.
    """
    global _default_client
    with _default_client_lock:
        if _default_client is None:
            _default_client = SteamStoreClient()
        return _default_client
