"""Compara o PC do usuário com os requisitos de PC publicados na loja da Steam.

Substitui a antiga estimativa de FPS. FPS depende de cena, preset gráfico, driver, versão
do jogo e de dezenas de outros fatores — só com a lista de peças não dá para chegar num
número honesto. Já os requisitos mínimo e recomendado são publicados pelo próprio
desenvolvedor, e "sua peça é pelo menos tão boa quanto a pedida?" é uma pergunta que a
escala de desempenho do catálogo consegue responder.
"""

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientDataError
from app.modules.catalog import service as catalog_service
from app.modules.catalog.enums import StorageType
from app.modules.detection.schemas import HardwareSnapshotBase
from app.modules.games.enums import CheckStatus, GameVerdict, RequirementComponent, RequirementTier
from app.modules.games.hardware_reference import (
    HardwareKind,
    ReferenceEntry,
    build_pool,
    find_catalog_entry,
    find_requirement_alternatives,
    match_exact,
)
from app.modules.games.requirements_parser import (
    ParsedRequirements,
    parse_requirements,
    windows_version_rank,
)
from app.modules.games.schemas import (
    GameRequirementsCheckRequest,
    GameRequirementsCheckResult,
    RequirementCheck,
    RequirementLineRead,
    SteamGameSummary,
    SystemEvaluation,
    TierEvaluation,
)
from app.modules.games.steam_client import SteamStoreClient
from app.modules.recommendation.schemas import SystemSnapshot

DISCLAIMER = (
    "A comparação usa os requisitos publicados pelo desenvolvedor na Steam e uma escala "
    "aproximada de desempenho entre peças — é uma boa referência, não uma garantia. "
    "Drivers, temperatura e as configurações que você escolher no jogo também pesam."
)

# Texto do veredito é lido por quem não manja de hardware — nunca mostramos os slugs dos
# enums direto, só estes nomes.
_COMPONENT_LABELS = {
    RequirementComponent.CPU: "processador",
    RequirementComponent.GPU: "placa de vídeo",
    RequirementComponent.VRAM: "memória da placa de vídeo",
    RequirementComponent.RAM: "memória RAM",
    RequirementComponent.STORAGE: "espaço em disco",
    RequirementComponent.OS: "sistema operacional",
}

_COMPONENT_POSSESSIVES = {
    RequirementComponent.CPU: "o seu processador",
    RequirementComponent.GPU: "a sua placa de vídeo",
}

_STATUS_SEVERITY = [CheckStatus.NAO_ATENDE, CheckStatus.NAO_DETERMINADO, CheckStatus.ATENDE]

# Indício de que a linha de placa de vídeo cita algum modelo (mesmo que a gente não o
# reconheça). Sem isso, "1 GB, DirectX 11" passaria a valer só pela VRAM — o que é certo —
# mas "NVIDIA 1060 6GB" também, o que aprovaria qualquer placa com 6 GB.
_GPU_MODEL_HINT = re.compile(
    r"geforce|radeon|nvidia|quadro|\bgtx|\brtx|\bgt\s*\d|\brx\b|\barc\b|\biris\b|\buhd\b|\bvega\b"
    r"|\bintel\s+hd\b|\b\d{3,4}\s*(?:ti|xt|super)?\b(?!\s*(?:gb|mb))",
    re.IGNORECASE,
)

_SSD_TYPES = {StorageType.SATA_SSD.value, StorageType.NVME_SSD.value}
_KNOWN_STORAGE_TYPES = _SSD_TYPES | {StorageType.HDD.value}


@dataclass
class _UserComponent:
    entry: ReferenceEntry | None
    label: str | None


@dataclass
class _UserHardware:
    cpu: _UserComponent
    gpu: _UserComponent
    ram_gb: float | None
    free_disk_gb: int | None
    has_ssd: bool | None
    windows_version: str | None


def search_games(steam: SteamStoreClient, term: str) -> list[SteamGameSummary]:
    return [
        SteamGameSummary(app_id=item.app_id, name=item.name, image_url=item.image_url)
        for item in steam.search(term)
    ]


# ---------------------------------------------------------------- PC do usuário


def _resolve_component(
    pool: list[ReferenceEntry],
    kind: HardwareKind,
    catalog_name: str | None,
    detected_name: str | None,
) -> _UserComponent:
    # O que o usuário confirmou no catálogo vale mais que a detecção: foi ele quem disse.
    if catalog_name:
        return _UserComponent(entry=find_catalog_entry(pool, catalog_name), label=catalog_name)
    if detected_name and detected_name.strip():
        entry = match_exact(detected_name, pool, kind)
        return _UserComponent(entry=entry, label=entry.name if entry else detected_name.strip())
    return _UserComponent(entry=None, label=None)


def _user_ram_gb(db: Session, system: SystemSnapshot, detected: HardwareSnapshotBase | None):
    if system.ram_model_name:
        kit = catalog_service.get_ram_kit_by_model_name(db, system.ram_model_name)
        if kit is not None:
            return kit.capacity_gb_per_module * kit.modules_in_kit
    return detected.ram_capacity_gb if detected else None


def _user_has_ssd(
    db: Session, system: SystemSnapshot, detected: HardwareSnapshotBase | None
) -> bool | None:
    types: list[str | None] = []
    if system.storage_model_name:
        storage = catalog_service.get_storage_by_model_name(db, system.storage_model_name)
        if storage is not None:
            types.append(storage.storage_type.value)
    if detected:
        types.extend(device.storage_type for device in detected.storage_devices)

    if any(t in _SSD_TYPES for t in types):
        return True
    # Só afirmamos "não tem SSD" quando conhecemos o tipo de TODOS os discos — o Windows
    # muitas vezes não informa o tipo de HDDs mais antigos.
    if types and all(t in _KNOWN_STORAGE_TYPES for t in types):
        return False
    return None


def _user_windows_version(detected: HardwareSnapshotBase | None) -> str | None:
    if not detected or not detected.os_name or "windows" not in detected.os_name.lower():
        return None
    version = detected.os_version or ""
    # platform.release() diz "10" também no Windows 11 em várias versões do Python — o
    # número do build é o jeito confiável de diferenciar (Windows 11 começa no 22000).
    build = re.search(r"\d+\.\d+\.(\d+)", version)
    if build and int(build.group(1)) >= 22000:
        return "11"
    release = re.match(r"\s*(11|10|8\.1|8|7)\b", version)
    return release.group(1) if release else None


def _build_user_hardware(
    db: Session,
    system: SystemSnapshot,
    detected: HardwareSnapshotBase | None,
    cpu_pool: list[ReferenceEntry],
    gpu_pool: list[ReferenceEntry],
) -> _UserHardware:
    return _UserHardware(
        cpu=_resolve_component(
            cpu_pool, "cpu", system.cpu_model_name, detected.cpu_model_name if detected else None
        ),
        gpu=_resolve_component(
            gpu_pool, "gpu", system.gpu_model_name, detected.gpu_model_name if detected else None
        ),
        ram_gb=_user_ram_gb(db, system, detected),
        free_disk_gb=detected.free_disk_space_gb if detected else None,
        has_ssd=_user_has_ssd(db, system, detected),
        windows_version=_user_windows_version(detected),
    )


# ---------------------------------------------------------------- checagens


def _format_gb(value: float) -> str:
    return f"{value:g} GB"


def _hardware_check(
    component: RequirementComponent,
    kind: HardwareKind,
    requirement_text: str,
    pool: list[ReferenceEntry],
    user: _UserComponent,
    *,
    requirement_only_states_vram: bool = False,
) -> RequirementCheck:
    label = _COMPONENT_LABELS[component]
    alternatives = find_requirement_alternatives(requirement_text, pool, kind)

    def result(
        status: CheckStatus, explanation: str, *, counts_for_verdict: bool = True
    ) -> RequirementCheck:
        return RequirementCheck(
            component=component,
            required=requirement_text,
            yours=user.label,
            status=status,
            explanation=explanation,
            counts_for_verdict=counts_for_verdict,
        )

    if not alternatives:
        if requirement_only_states_vram:
            # Ex. (Counter-Strike 2): "Video card must be 1 GB or more and should be a
            # DirectX 11-compatible". Sem modelo citado, a memória de vídeo É o requisito de
            # placa — e ela já tem a própria checagem, então esta não decide o veredito.
            return result(
                CheckStatus.NAO_DETERMINADO,
                "O jogo não cita um modelo de placa, só a memória de vídeo mínima — veja a "
                "linha de memória da placa de vídeo.",
                counts_for_verdict=False,
            )
        return result(
            CheckStatus.NAO_DETERMINADO,
            f"Não reconhecemos o modelo de {label} que o jogo pede na nossa base de "
            "comparação, então não dá para cravar.",
        )
    if user.entry is None:
        possessive = _COMPONENT_POSSESSIVES[component]
        if user.label:
            return result(
                CheckStatus.NAO_DETERMINADO,
                f"Não temos {possessive} ({user.label}) na nossa base de comparação, então "
                "não dá para cravar.",
            )
        return result(CheckStatus.NAO_DETERMINADO, f"Você não informou {possessive}.")

    # Quando o jogo aceita alternativas ("Core i5-4460 or FX-6300"), qualquer uma delas
    # serve — então a régua é a mais modesta.
    weakest = min(alternatives, key=lambda a: a.score)
    qualifier = "" if len(alternatives) == 1 else ", a opção mais modesta que o jogo aceita"
    if user.entry.score >= weakest.score:
        return result(
            CheckStatus.ATENDE, f"Tem desempenho igual ou melhor que o {weakest.name}{qualifier}."
        )
    return result(CheckStatus.NAO_ATENDE, f"Fica abaixo do {weakest.name}{qualifier}.")


def _vram_check(parsed: ParsedRequirements, user: _UserComponent) -> RequirementCheck | None:
    if parsed.vram_gb is None or parsed.gpu is None:
        return None
    required = f"{parsed.vram_gb} GB"
    vram = user.entry.vram_gb if user.entry else None
    if vram is None:
        # Só sabemos a VRAM de placas do catálogo. Para as demais, a comparação de modelo
        # (checagem de GPU) já é o sinal principal — VRAM desconhecida vira só um aviso, em
        # vez de impedir o veredito de uma placa que já supera a pedida.
        return RequirementCheck(
            component=RequirementComponent.VRAM,
            required=required,
            status=CheckStatus.NAO_DETERMINADO,
            explanation=(
                "Não sabemos quanta memória tem a sua placa de vídeo — confira se ela tem "
                f"pelo menos {required}."
            ),
            counts_for_verdict=False,
        )
    meets = vram >= parsed.vram_gb
    return RequirementCheck(
        component=RequirementComponent.VRAM,
        required=required,
        yours=f"{vram} GB",
        status=CheckStatus.ATENDE if meets else CheckStatus.NAO_ATENDE,
        explanation=(
            "Memória de vídeo suficiente."
            if meets
            else "Pouca memória de vídeo: texturas no alto tendem a engasgar ou nem carregar."
        ),
    )


def _ram_check(parsed: ParsedRequirements, ram_gb: float | None) -> RequirementCheck | None:
    if parsed.ram is None:
        return None
    if parsed.ram_gb is None or ram_gb is None:
        return RequirementCheck(
            component=RequirementComponent.RAM,
            required=parsed.ram,
            yours=_format_gb(ram_gb) if ram_gb is not None else None,
            status=CheckStatus.NAO_DETERMINADO,
            explanation=(
                "Não sabemos quanta memória RAM o seu PC tem."
                if ram_gb is None
                else "Não conseguimos ler quanta memória o jogo pede."
            ),
        )
    meets = ram_gb >= parsed.ram_gb
    return RequirementCheck(
        component=RequirementComponent.RAM,
        required=parsed.ram,
        yours=_format_gb(ram_gb),
        status=CheckStatus.ATENDE if meets else CheckStatus.NAO_ATENDE,
        explanation=(
            "Memória suficiente."
            if meets
            else f"Faltam {_format_gb(parsed.ram_gb - ram_gb)} de RAM para o que o jogo pede."
        ),
    )


def _storage_check(parsed: ParsedRequirements, user: _UserHardware) -> RequirementCheck | None:
    if parsed.storage_gb is None and not parsed.ssd_required:
        return None

    statuses: list[CheckStatus] = []
    notes: list[str] = []
    if parsed.storage_gb is not None:
        if user.free_disk_gb is None:
            statuses.append(CheckStatus.NAO_DETERMINADO)
            notes.append("Não sabemos quanto espaço livre você tem.")
        elif user.free_disk_gb >= parsed.storage_gb:
            statuses.append(CheckStatus.ATENDE)
            notes.append("Tem espaço livre suficiente.")
        else:
            statuses.append(CheckStatus.NAO_ATENDE)
            notes.append(
                f"Libere pelo menos {_format_gb(parsed.storage_gb - user.free_disk_gb)} antes "
                "de instalar."
            )
    if parsed.ssd_required:
        if user.has_ssd is None:
            statuses.append(CheckStatus.NAO_DETERMINADO)
            notes.append("O jogo exige SSD, e não conseguimos confirmar se você tem um.")
        elif user.has_ssd:
            statuses.append(CheckStatus.ATENDE)
            notes.append("O jogo exige SSD, e você tem um — instale o jogo nele.")
        else:
            statuses.append(CheckStatus.NAO_ATENDE)
            notes.append(
                "O jogo exige SSD, e não encontramos nenhum no seu PC: num HD comum ele tende "
                "a engasgar e demorar muito para carregar."
            )

    required = parsed.storage or ""
    if parsed.ssd_required and "ssd" not in required.lower():
        required = f"{required} · SSD exigido".strip(" ·")
    return RequirementCheck(
        component=RequirementComponent.STORAGE,
        required=required,
        yours=(
            f"{user.free_disk_gb} GB livres (maior unidade)"
            if user.free_disk_gb is not None
            else None
        ),
        status=min(statuses, key=_STATUS_SEVERITY.index),
        explanation=" ".join(notes),
        counts_for_verdict=False,
    )


def _os_check(parsed: ParsedRequirements, windows_version: str | None) -> RequirementCheck | None:
    if parsed.os is None or parsed.min_windows_version is None:
        return None
    if windows_version is None:
        return RequirementCheck(
            component=RequirementComponent.OS,
            required=parsed.os,
            status=CheckStatus.NAO_DETERMINADO,
            explanation="Não conseguimos identificar a versão do seu Windows.",
            counts_for_verdict=False,
        )
    meets = windows_version_rank(windows_version) >= windows_version_rank(
        parsed.min_windows_version
    )
    return RequirementCheck(
        component=RequirementComponent.OS,
        required=parsed.os,
        yours=f"Windows {windows_version}",
        status=CheckStatus.ATENDE if meets else CheckStatus.NAO_ATENDE,
        explanation=(
            "Versão do Windows compatível."
            if meets
            else f"O jogo pede Windows {parsed.min_windows_version} ou mais novo."
        ),
        counts_for_verdict=False,
    )


def _evaluate_tier(
    tier: RequirementTier,
    parsed: ParsedRequirements,
    user: _UserHardware,
    cpu_pool: list[ReferenceEntry],
    gpu_pool: list[ReferenceEntry],
) -> TierEvaluation:
    checks: list[RequirementCheck] = []
    if parsed.cpu:
        checks.append(
            _hardware_check(RequirementComponent.CPU, "cpu", parsed.cpu, cpu_pool, user.cpu)
        )
    if parsed.gpu:
        checks.append(
            _hardware_check(
                RequirementComponent.GPU,
                "gpu",
                parsed.gpu,
                gpu_pool,
                user.gpu,
                requirement_only_states_vram=(
                    parsed.vram_gb is not None and not _GPU_MODEL_HINT.search(parsed.gpu)
                ),
            )
        )
    optional_checks = [
        _vram_check(parsed, user.gpu),
        _ram_check(parsed, user.ram_gb),
        _storage_check(parsed, user),
        _os_check(parsed, user.windows_version),
    ]
    checks.extend(c for c in optional_checks if c is not None)

    deciding = [c.status for c in checks if c.counts_for_verdict]
    if CheckStatus.NAO_ATENDE in deciding:
        status = CheckStatus.NAO_ATENDE
    elif not deciding or CheckStatus.NAO_DETERMINADO in deciding:
        status = CheckStatus.NAO_DETERMINADO
    else:
        status = CheckStatus.ATENDE
    return TierEvaluation(tier=tier, status=status, checks=checks)


# ---------------------------------------------------------------- veredito


def _join_pt(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " e " + items[-1]


def _components_with(tier: TierEvaluation, status: CheckStatus) -> str:
    return _join_pt(
        [
            _COMPONENT_LABELS[c.component]
            for c in tier.checks
            if c.counts_for_verdict and c.status == status
        ]
    )


def _verdict(
    minimum: TierEvaluation | None, recommended: TierEvaluation | None
) -> tuple[GameVerdict, str]:
    if recommended and recommended.status == CheckStatus.ATENDE:
        return (
            GameVerdict.RODA_NO_RECOMENDADO,
            "Seu PC atende aos requisitos recomendados — o jogo deve rodar bem, com folga "
            "para deixar os gráficos mais caprichados.",
        )

    if minimum and minimum.status == CheckStatus.ATENDE:
        text = (
            "Seu PC atende aos requisitos mínimos, então o jogo deve rodar — mas espere "
            "gráficos no baixo ou no médio."
        )
        if recommended is None:
            text = (
                "Seu PC atende aos requisitos mínimos, então o jogo deve rodar (ele não "
                "publica requisitos recomendados para comparar)."
            )
        elif recommended.status == CheckStatus.NAO_ATENDE:
            text += (
                " Para chegar no recomendado, falta melhorar: "
                f"{_components_with(recommended, CheckStatus.NAO_ATENDE)}."
            )
        else:
            text += (
                " Não deu para comparar com o recomendado: "
                f"{_components_with(recommended, CheckStatus.NAO_DETERMINADO)}."
            )
        return GameVerdict.RODA_NO_MINIMO, text

    if minimum and minimum.status == CheckStatus.NAO_ATENDE:
        return (
            GameVerdict.ABAIXO_DO_MINIMO,
            "Seu PC fica abaixo dos requisitos mínimos em: "
            f"{_components_with(minimum, CheckStatus.NAO_ATENDE)}. Às vezes até abre, mas "
            "espere travamentos e quedas de desempenho — o mínimo é a configuração com que o "
            "próprio desenvolvedor diz que o jogo fica jogável.",
        )

    if minimum is None and recommended and recommended.status == CheckStatus.NAO_ATENDE:
        return (
            GameVerdict.INDETERMINADO,
            "O jogo só publica requisitos recomendados, e seu PC fica abaixo deles em: "
            f"{_components_with(recommended, CheckStatus.NAO_ATENDE)}. Sem o mínimo, não dá "
            "para saber se ele roda no básico.",
        )

    reference_tier = minimum or recommended
    pending = (
        _components_with(reference_tier, CheckStatus.NAO_DETERMINADO) if reference_tier else ""
    )
    detail = (
        f"não conseguimos comparar {pending} com o que o jogo pede."
        if pending
        else "faltou dado para comparar."
    )
    return GameVerdict.INDETERMINADO, f"Não deu para cravar: {detail} Veja os detalhes abaixo."


_ATTENTION_SENTENCES = {
    RequirementComponent.STORAGE: (
        "Atenção ao armazenamento: falta espaço livre ou SSD para o que o jogo pede — veja "
        "os detalhes."
    ),
    RequirementComponent.OS: "Atenção: o jogo pede uma versão mais nova do Windows.",
}


def _attention_note(tiers: list[TierEvaluation]) -> str | None:
    """Avisos que não mudam o veredito (dá para resolver sem trocar peça), mas que a pessoa
    precisa ver antes de comprar o jogo."""
    flagged: list[RequirementComponent] = []
    for tier in tiers:
        for check in tier.checks:
            if (
                not check.counts_for_verdict
                and check.status == CheckStatus.NAO_ATENDE
                and check.component in _ATTENTION_SENTENCES
                and check.component not in flagged
            ):
                flagged.append(check.component)
    return " ".join(_ATTENTION_SENTENCES[c] for c in flagged) or None


def _evaluate_system(
    db: Session,
    system: SystemSnapshot,
    detected: HardwareSnapshotBase | None,
    minimum: ParsedRequirements | None,
    recommended: ParsedRequirements | None,
    cpu_pool: list[ReferenceEntry],
    gpu_pool: list[ReferenceEntry],
) -> SystemEvaluation:
    user = _build_user_hardware(db, system, detected, cpu_pool, gpu_pool)
    minimum_eval = (
        _evaluate_tier(RequirementTier.MINIMUM, minimum, user, cpu_pool, gpu_pool)
        if minimum
        else None
    )
    recommended_eval = (
        _evaluate_tier(RequirementTier.RECOMMENDED, recommended, user, cpu_pool, gpu_pool)
        if recommended
        else None
    )
    verdict, verdict_text = _verdict(minimum_eval, recommended_eval)
    attention = _attention_note([t for t in (minimum_eval, recommended_eval) if t])
    if attention:
        verdict_text = f"{verdict_text} {attention}"
    return SystemEvaluation(
        verdict=verdict,
        verdict_text=verdict_text,
        minimum=minimum_eval,
        recommended=recommended_eval,
    )


def _lines(parsed: ParsedRequirements | None) -> list[RequirementLineRead]:
    if parsed is None:
        return []
    return [RequirementLineRead(label=line.label, value=line.value) for line in parsed.lines]


def check_requirements(
    db: Session, steam: SteamStoreClient, request: GameRequirementsCheckRequest
) -> GameRequirementsCheckResult:
    app = steam.get_app(request.app_id)
    minimum = parse_requirements(app.minimum_html)
    recommended = parse_requirements(app.recommended_html)
    if minimum is None and recommended is None:
        raise InsufficientDataError(
            f"A Steam não lista requisitos de PC para '{app.name}', então não temos com o "
            "que comparar o seu computador."
        )

    cpu_pool = build_pool(db, "cpu")
    gpu_pool = build_pool(db, "gpu")

    current = _evaluate_system(
        db, request.system, request.detected, minimum, recommended, cpu_pool, gpu_pool
    )
    upgraded = (
        _evaluate_system(
            db, request.upgraded_system, request.detected, minimum, recommended, cpu_pool, gpu_pool
        )
        if request.upgraded_system is not None
        else None
    )

    return GameRequirementsCheckResult(
        app_id=app.app_id,
        name=app.name,
        store_url=app.store_url,
        header_image=app.header_image,
        minimum_requirements=_lines(minimum),
        recommended_requirements=_lines(recommended),
        current=current,
        upgraded=upgraded,
        disclaimer=DISCLAIMER,
    )
