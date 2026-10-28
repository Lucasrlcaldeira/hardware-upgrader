"""Reconhecimento de CPUs/GPUs por nome e posicionamento numa escala comum de desempenho.

Por que isto existe: os requisitos da Steam citam peças que muitas vezes não estão no
catálogo de upgrades (GTX 960, i5-4460, FX-6300...). Para responder "a peça do usuário é
pelo menos tão boa quanto a exigida?", as duas precisam estar na mesma escala — a escala
ordinal de performance_tier do catálogo. O "pool" de comparação junta:

- as peças do catálogo (o tier do catálogo é a fonte de verdade para elas), e
- a base de referência em reference/*.json, que só cobre o que falta no catálogo.

A escala é ordinal: serve para ordenar peças ("A >= B"), nunca para calcular FPS.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from sqlalchemy.orm import Session

from app.modules.catalog import service as catalog_service

HardwareKind = Literal["cpu", "gpu"]

_REFERENCE_DIR = Path(__file__).parent / "reference"

# Ruído que a detecção do Windows e os textos da Steam colocam ao redor do modelo real.
# Removido ANTES de quebrar em tokens, porque depois disso "(TM)" vira um token "tm" solto e
# "6-Core" vira um "6" indistinguível de parte do nome do modelo.
_PRE_STRIP_PATTERNS = [
    re.compile(r"\((?:r|tm|c)\)"),  # Intel(R) Core(TM)
    re.compile(r"[®™]"),
    re.compile(r"\b\d+(?:st|nd|rd|th)\s+gen(?:eration)?\b"),  # "12th Gen Intel..."
    re.compile(r"\b\d+-core\b"),  # "AMD Ryzen 5 5600 6-Core Processor"
    re.compile(r"@?\s*\d+(?:[.,]\d+)?\s*ghz\b"),  # "@ 3.20GHz"
    re.compile(r"\bwith radeon(?: vega)? graphics\b"),  # "Ryzen 5 5600G with Radeon Graphics"
]

# Tokens genéricos que não distinguem um produto de outro. Nunca entra aqui algo como "ti",
# "super", "xt" ou "laptop" — esses separam produtos com desempenho bem diferente.
_IGNORABLE_TOKENS = {
    "amd",
    "nvidia",
    "intel",
    "geforce",
    "radeon",
    "core",
    "processor",
    "processador",
    "cpu",
    "gpu",
    "graphics",
    "card",
    "video",
    "placa",
    "de",
    "with",
    "com",
    "six",
    "quad",
    "eight",
    "dual",
    "ten",
    "twelve",
    "sixteen",
    "cores",
}

# Separadores entre alternativas num requisito ("GTX 1060 6GB or RX 580 8GB / Arc A380").
# Sem separar antes, os tokens de alternativas diferentes se misturam: "RTX 2060 or GTX
# 1660 Super" contém todos os tokens de "RTX 2060 Super" — que não foi pedida.
_ALTERNATIVE_SPLIT = re.compile(r"\s*(?:/|\||;|,|\bor\b|\bou\b)\s*", re.IGNORECASE)


@dataclass(frozen=True)
class ReferenceEntry:
    name: str
    score: int
    tokens: frozenset[str]
    vram_gb: int | None = None
    from_catalog: bool = False


def tokenize(text: str, kind: HardwareKind) -> list[str]:
    value = unicodedata.normalize("NFD", text.lower())
    value = "".join(c for c in value if not unicodedata.combining(c))
    for pattern in _PRE_STRIP_PATTERNS:
        value = pattern.sub(" ", value)

    # "6 GB" e "6GB" precisam virar o mesmo token "6gb" — senão o "8" de "8 GB" casaria
    # com um modelo como "Radeon Vega 8".
    value = re.sub(r"(\d+)\s*(gb|mb)\b", r"\1\2", value)
    # "1050Ti" -> "1050 ti", "RTX2060" -> "rtx 2060": mesma peça, grafias diferentes.
    value = re.sub(r"(\d)(ti|super|xtx|xt)\b", r"\1 \2", value)
    value = re.sub(r"\b(gtx|rtx|gt|rx|hd|fx)(\d)", r"\1 \2", value)

    tokens = [t for t in re.sub(r"[^a-z0-9]+", " ", value).split() if t not in _IGNORABLE_TOKENS]

    if kind == "cpu":
        tokens = _normalize_cpu_tokens(tokens)
    return tokens


def _normalize_cpu_tokens(tokens: list[str]) -> list[str]:
    normalized: list[str] = []
    for i, token in enumerate(tokens):
        # "R5 3600" é abreviação comum de "Ryzen 5 3600" em requisitos. Só vale para CPU:
        # em GPU, "R9 290" é uma Radeon.
        next_token = tokens[i + 1] if i + 1 < len(tokens) else ""
        if re.fullmatch(r"r[3579]", token) and re.match(r"\d{4}", next_token):
            normalized.extend(["ryzen", token[1]])
            continue
        # Sufixo "F" da Intel (12400F, 13600KF) = mesma CPU sem vídeo integrado, mesmo
        # desempenho em jogos — tratamos como o modelo base.
        normalized.append(re.sub(r"^(\d{4,5}k?)f$", r"\1", token))
    return normalized


def _entry_from_name(
    name: str, score: int, kind: HardwareKind, *, vram_gb: int | None = None, from_catalog=False
) -> ReferenceEntry:
    return ReferenceEntry(
        name=name,
        score=score,
        tokens=frozenset(tokenize(name, kind)),
        vram_gb=vram_gb,
        from_catalog=from_catalog,
    )


@lru_cache
def load_reference_entries(kind: HardwareKind) -> tuple[ReferenceEntry, ...]:
    with open(_REFERENCE_DIR / f"{kind}s.json", encoding="utf-8") as f:
        raw = json.load(f)
    return tuple(_entry_from_name(item["name"], item["score"], kind) for item in raw["items"])


def build_pool(db: Session, kind: HardwareKind) -> list[ReferenceEntry]:
    """Catálogo + base de referência. Se o mesmo modelo aparecer nos dois, vale o catálogo."""
    if kind == "cpu":
        catalog_entries = [
            _entry_from_name(c.model_name, c.performance_tier, kind, from_catalog=True)
            for c in catalog_service.list_cpus(db)
            if c.performance_tier is not None
        ]
    else:
        catalog_entries = [
            _entry_from_name(
                g.model_name, g.performance_tier, kind, vram_gb=g.vram_gb, from_catalog=True
            )
            for g in catalog_service.list_gpus(db)
            if g.performance_tier is not None
        ]

    catalog_token_sets = {e.tokens for e in catalog_entries}
    reference_entries = [
        e for e in load_reference_entries(kind) if e.tokens not in catalog_token_sets
    ]
    return catalog_entries + reference_entries


def find_requirement_alternatives(
    requirement_text: str, pool: list[ReferenceEntry], kind: HardwareKind
) -> list[ReferenceEntry]:
    """Peças reconhecidas num texto de requisito, uma por alternativa citada.

    Aqui o casamento é por subconjunto (todos os tokens do modelo aparecem no trecho),
    porque requisitos vêm com ruído ("6GB", "or better", "equivalent"). Quando um modelo
    "engole" outro (o texto diz "RTX 2060 Super" e tanto "RTX 2060" quanto "RTX 2060 Super"
    casam), fica só o mais específico.
    """
    alternatives: list[ReferenceEntry] = []
    for segment in _ALTERNATIVE_SPLIT.split(requirement_text):
        segment_tokens = set(tokenize(segment, kind))
        if not segment_tokens:
            continue
        hits = [e for e in pool if e.tokens and e.tokens <= segment_tokens]
        for hit in hits:
            if any(hit.tokens < other.tokens for other in hits):
                continue
            if hit not in alternatives:
                alternatives.append(hit)
    return alternatives


def match_exact(name: str, pool: list[ReferenceEntry], kind: HardwareKind) -> ReferenceEntry | None:
    """Casa o nome de uma peça do usuário (ex: o que o Windows detectou) com o pool.

    Bem mais rígido que find_requirement_alternatives: depois de remover o ruído, os tokens
    têm que ser exatamente os do modelo. Assim "RTX 3060 Laptop GPU" nunca vira a RTX 3060
    de desktop, que é bem mais forte. Na dúvida, preferimos "não reconhecido" a superestimar
    o PC do usuário.
    """
    tokens = frozenset(tokenize(name, kind))
    if not tokens:
        return None
    match = _single_exact_match(tokens, pool)
    if match is not None:
        return match

    # O Windows costuma incluir a VRAM no nome ("GeForce GTX 1060 6GB"). Só a descartamos
    # depois de tentar com ela, porque às vezes ela É o que distingue o modelo (GTX 1060 3GB).
    without_memory = frozenset(t for t in tokens if not re.fullmatch(r"\d+(gb|mb)", t))
    if without_memory and without_memory != tokens:
        return _single_exact_match(without_memory, pool)
    return None


def _single_exact_match(
    tokens: frozenset[str], pool: list[ReferenceEntry]
) -> ReferenceEntry | None:
    matches = [e for e in pool if e.tokens == tokens]
    return matches[0] if len(matches) == 1 else None


def find_catalog_entry(pool: list[ReferenceEntry], model_name: str) -> ReferenceEntry | None:
    return next((e for e in pool if e.from_catalog and e.name == model_name), None)
