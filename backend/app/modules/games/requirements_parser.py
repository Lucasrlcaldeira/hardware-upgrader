"""Transforma o HTML de requisitos da Steam (pc_requirements.minimum/recommended) em dados.

Exemplo do que a Steam devolve:

    <strong>Minimum:</strong><br><ul class="bb_ul">
      <li><strong>OS:</strong> 64-bit Windows 10<br></li>
      <li><strong>Processor:</strong> Core i7-6700 or Ryzen 5 1600<br></li>
      <li><strong>Memory:</strong> 12 GB RAM<br></li>
      ...

Nem todo jogo segue o formulário padrão da Steam: alguns escrevem texto livre. Por isso
todo campo extraído é opcional, e um campo que não deu para interpretar simplesmente fica
None ("não determinado"), em vez de virar um chute.
"""

import html
import re
import unicodedata
from dataclasses import dataclass, field

# Rótulos em inglês (pedimos a página em inglês, que é o formato mais padronizado) e em
# português, caso o desenvolvedor tenha escrito o texto à mão.
_LABEL_ALIASES = {
    "os": {"os", "so", "operating system", "sistema operacional"},
    "cpu": {"processor", "processador", "cpu"},
    "ram": {"memory", "memoria", "ram", "system memory", "memoria ram"},
    "gpu": {
        "graphics",
        "graphics card",
        "video card",
        "video",
        "gpu",
        "placa de video",
        "placa grafica",
    },
    "storage": {
        "storage",
        "hard drive",
        "hard disk space",
        "disk space",
        "hdd",
        "armazenamento",
        "espaco em disco",
        "disco rigido",
    },
    "notes": {"additional notes", "notes", "outras observacoes", "observacoes", "notas adicionais"},
}

_TIER_HEADER = re.compile(r"^(minimum|recommended|minimos?|recomendados?)\s*:?\s*$", re.IGNORECASE)
_LABELED_LINE = re.compile(r"^([^:]{2,40}):\s*(.+)$")
_SIZE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(tb|gb|mb|g)\b", re.IGNORECASE)
_WINDOWS_VERSION = re.compile(r"windows\s*(11|10|8\.1|8|7|vista|xp)\b", re.IGNORECASE)
_WINDOWS_ORDER = {"xp": 5.1, "vista": 6.0, "7": 7, "8": 8, "8.1": 8.1, "10": 10, "11": 11}

# VRAM acima disso numa linha de placa de vídeo quase certamente é outra coisa (ex: RAM).
_MAX_PLAUSIBLE_VRAM_GB = 48


@dataclass
class RequirementLine:
    label: str
    value: str


@dataclass
class ParsedRequirements:
    lines: list[RequirementLine] = field(default_factory=list)
    os: str | None = None
    cpu: str | None = None
    gpu: str | None = None
    ram: str | None = None
    storage: str | None = None
    notes: str | None = None

    ram_gb: float | None = None
    vram_gb: int | None = None
    storage_gb: float | None = None
    ssd_required: bool = False
    min_windows_version: str | None = None


def _normalize_label(label: str) -> str:
    value = unicodedata.normalize("NFD", label.lower())
    return "".join(c for c in value if not unicodedata.combining(c)).strip()


def _html_to_lines(raw_html: str) -> list[str]:
    text = re.sub(r"<br\s*/?>|</li>|</p>|</div>", "\n", raw_html, flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return [line.strip() for line in text.splitlines() if line.strip()]


def _size_in_gb(text: str | None) -> float | None:
    if not text:
        return None
    match = _SIZE.search(text)
    if not match:
        return None
    amount = float(match.group(1).replace(",", "."))
    unit = match.group(2).lower()
    if unit == "tb":
        return amount * 1024
    if unit == "mb":
        return round(amount / 1024, 2)
    return amount


def _vram_gb(gpu_text: str | None) -> int | None:
    """Menor quantidade de memória citada na linha da placa de vídeo.

    "GTX 1060 6GB or RX 580 8GB" -> 6: quem publicou aceita qualquer das alternativas, então
    a exigência real é a menor delas.
    """
    if not gpu_text:
        return None
    amounts = [
        int(float(m.group(1).replace(",", ".")))
        for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*gb\b", gpu_text, re.IGNORECASE)
    ]
    amounts = [a for a in amounts if 0 < a <= _MAX_PLAUSIBLE_VRAM_GB]
    return min(amounts) if amounts else None


def _requires_ssd(storage: str | None, notes: str | None) -> bool:
    # "SSD recommended" não é exigência; "SSD required" / "SSD obrigatório" é.
    if storage and re.search(r"\bssd\b", storage, re.IGNORECASE):
        if not re.search(r"recommend|recomend", storage, re.IGNORECASE):
            return True
    if notes and re.search(r"\bssd\b[^.]*\b(required|obrigat\w*|necess\w*)", notes, re.IGNORECASE):
        return True
    return False


def _min_windows_version(os_text: str | None) -> str | None:
    if not os_text:
        return None
    versions = [m.group(1).lower() for m in _WINDOWS_VERSION.finditer(os_text)]
    if not versions:
        return None
    return min(versions, key=lambda v: _WINDOWS_ORDER[v])


def parse_requirements(raw_html: str | None) -> ParsedRequirements | None:
    if not raw_html or not raw_html.strip():
        return None

    parsed = ParsedRequirements()
    for line in _html_to_lines(raw_html):
        if _TIER_HEADER.match(line):
            continue
        labeled = _LABELED_LINE.match(line)
        if not labeled:
            # Linhas sem rótulo, ex: "Requires a 64-bit processor and operating system".
            parsed.lines.append(RequirementLine(label="", value=line))
            continue

        label, value = labeled.group(1).strip(), labeled.group(2).strip()
        parsed.lines.append(RequirementLine(label=label, value=value))

        normalized = _normalize_label(label)
        for attr, aliases in _LABEL_ALIASES.items():
            # Só o primeiro valor de cada campo conta: alguns jogos repetem rótulos.
            if normalized in aliases and getattr(parsed, attr) is None:
                setattr(parsed, attr, value)
                break

    if not parsed.lines:
        return None

    parsed.ram_gb = _size_in_gb(parsed.ram)
    parsed.vram_gb = _vram_gb(parsed.gpu)
    parsed.storage_gb = _size_in_gb(parsed.storage)
    parsed.ssd_required = _requires_ssd(parsed.storage, parsed.notes)
    parsed.min_windows_version = _min_windows_version(parsed.os)
    return parsed


def windows_version_rank(version: str) -> float:
    return _WINDOWS_ORDER[version]
