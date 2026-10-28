import json
from pathlib import Path

import pytest

from app.modules.games.hardware_reference import (
    ReferenceEntry,
    find_requirement_alternatives,
    load_reference_entries,
    match_exact,
    tokenize,
)
from app.modules.games.requirements_parser import parse_requirements

CATALOG_SEED_DIR = Path(__file__).parents[2] / "app" / "modules" / "catalog" / "seed"

# HTML real (resumido) da página do Cyberpunk 2077 na Steam.
CYBERPUNK_MINIMUM = (
    '<strong>Minimum:</strong><br><ul class="bb_ul">'
    "<li>Requires a 64-bit processor and operating system<br></li>"
    "<li><strong>OS:</strong> 64-bit Windows 10<br></li>"
    "<li><strong>Processor:</strong> Core i7-6700 or Ryzen 5 1600<br></li>"
    "<li><strong>Memory:</strong> 12 GB RAM<br></li>"
    "<li><strong>Graphics:</strong> GeForce GTX 1060 6GB or Radeon RX 580 8GB or Arc A380<br></li>"
    "<li><strong>DirectX:</strong> Version 12<br></li>"
    "<li><strong>Storage:</strong> 70 GB available space<br></li>"
    "<li><strong>Additional Notes:</strong> SSD required. Attention: visual effects.</li></ul>"
)


def _entry(name, score, kind="gpu"):
    return ReferenceEntry(name=name, score=score, tokens=frozenset(tokenize(name, kind)))


# ---------------------------------------------------------------- parser


def test_parses_standard_steam_requirements():
    parsed = parse_requirements(CYBERPUNK_MINIMUM)

    assert parsed.cpu == "Core i7-6700 or Ryzen 5 1600"
    assert parsed.gpu == "GeForce GTX 1060 6GB or Radeon RX 580 8GB or Arc A380"
    assert parsed.ram_gb == 12
    assert parsed.vram_gb == 6
    assert parsed.storage_gb == 70
    assert parsed.ssd_required is True
    assert parsed.min_windows_version == "10"
    # Linha sem rótulo é preservada para mostrar ao usuário.
    assert parsed.lines[0].label == ""
    assert parsed.lines[0].value.startswith("Requires a 64-bit")


def test_parses_ram_in_megabytes_and_ignores_recommended_ssd():
    parsed = parse_requirements(
        "<ul><li><strong>Memory:</strong> 4096 MB RAM</li>"
        "<li><strong>Storage:</strong> 20 GB available space (SSD recommended)</li></ul>"
    )

    assert parsed.ram_gb == 4
    assert parsed.ssd_required is False


def test_portuguese_labels_are_understood():
    parsed = parse_requirements(
        "<ul><li><strong>Processador:</strong> Intel Core i5-4460</li>"
        "<li><strong>Memória:</strong> 8 GB de RAM</li>"
        "<li><strong>Placa de vídeo:</strong> GTX 960</li></ul>"
    )

    assert parsed.cpu == "Intel Core i5-4460"
    assert parsed.ram_gb == 8
    assert parsed.gpu == "GTX 960"


def test_oldest_windows_version_listed_is_the_minimum():
    parsed = parse_requirements("<ul><li><strong>OS:</strong> Windows 7 SP1 / Windows 10</li></ul>")
    assert parsed.min_windows_version == "7"


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_empty_requirements_return_none(raw):
    assert parse_requirements(raw) is None


# ---------------------------------------------------------------- reconhecimento de peças


@pytest.mark.parametrize(
    ("detected", "expected_tokens"),
    [
        ("Intel(R) Core(TM) i5-4460  CPU @ 3.20GHz", {"i5", "4460"}),
        ("AMD Ryzen 5 5600 6-Core Processor", {"ryzen", "5", "5600"}),
        ("AMD Ryzen 5 1600 Six-Core Processor", {"ryzen", "5", "1600"}),
        ("12th Gen Intel(R) Core(TM) i5-12400F", {"i5", "12400"}),
        ("AMD Ryzen 5 5600G with Radeon Graphics", {"ryzen", "5", "5600g"}),
        ("R5 3600", {"ryzen", "5", "3600"}),
    ],
)
def test_cpu_tokenization_strips_detection_noise(detected, expected_tokens):
    assert set(tokenize(detected, "cpu")) == expected_tokens


def test_gpu_spelling_variants_tokenize_the_same():
    assert tokenize("GTX 1050Ti", "gpu") == tokenize("NVIDIA GeForce GTX 1050 Ti", "gpu")
    assert tokenize("RTX2060", "gpu") == tokenize("GeForce RTX 2060", "gpu")


def test_requirement_alternatives_are_split_before_matching():
    pool = [
        _entry("GeForce RTX 2060", 30),
        _entry("GeForce RTX 2060 Super", 34),
        _entry("GeForce GTX 1660 Super", 25),
    ]

    found = find_requirement_alternatives("RTX 2060 or GTX 1660 Super", pool, "gpu")

    # "RTX 2060 Super" NÃO foi pedida — os tokens só "aparecem" se misturarmos alternativas.
    assert [e.name for e in found] == ["GeForce RTX 2060", "GeForce GTX 1660 Super"]


def test_more_specific_model_wins_over_its_base_model():
    pool = [_entry("GeForce RTX 2060", 30), _entry("GeForce RTX 2060 Super", 34)]

    found = find_requirement_alternatives("GeForce RTX 2060 SUPER 8GB", pool, "gpu")

    assert [e.name for e in found] == ["GeForce RTX 2060 Super"]


def test_vram_amount_never_matches_an_integrated_gpu_name():
    pool = [_entry("Radeon Vega 8", 4), _entry("Radeon RX Vega 56", 27)]

    found = find_requirement_alternatives("AMD Radeon RX Vega 56 8 GB", pool, "gpu")

    assert [e.name for e in found] == ["Radeon RX Vega 56"]


def test_exact_match_rejects_laptop_variant_of_a_desktop_gpu():
    pool = [_entry("GeForce RTX 3060", 47)]
    assert match_exact("NVIDIA GeForce RTX 3060 Laptop GPU", pool, "gpu") is None


def test_exact_match_ignores_vram_suffix_only_when_it_does_not_identify_the_model():
    pool = [_entry("GeForce GTX 1060", 19), _entry("GeForce GTX 1060 3GB", 17)]

    assert match_exact("NVIDIA GeForce GTX 1060 6GB", pool, "gpu").name == "GeForce GTX 1060"
    assert match_exact("NVIDIA GeForce GTX 1060 3GB", pool, "gpu").name == "GeForce GTX 1060 3GB"


# ---------------------------------------------------------------- integridade da base


@pytest.mark.parametrize("kind", ["cpu", "gpu"])
def test_reference_entries_are_unique_and_positive(kind):
    entries = load_reference_entries(kind)
    token_sets = [e.tokens for e in entries]

    assert all(e.score > 0 for e in entries)
    assert all(e.tokens for e in entries)
    assert len(token_sets) == len(set(token_sets)), "dois modelos viram os mesmos tokens"


@pytest.mark.parametrize("kind", ["cpu", "gpu"])
def test_reference_does_not_duplicate_catalog_models(kind):
    """O catálogo é a fonte de verdade: um modelo que já existe lá não deve ser repetido na
    base de referência (com risco de as duas notas divergirem)."""
    with open(CATALOG_SEED_DIR / f"{kind}s.json", encoding="utf-8") as f:
        catalog_token_sets = {
            frozenset(tokenize(item["model_name"], kind)) for item in json.load(f)
        }

    duplicated = [e.name for e in load_reference_entries(kind) if e.tokens in catalog_token_sets]
    assert duplicated == []
