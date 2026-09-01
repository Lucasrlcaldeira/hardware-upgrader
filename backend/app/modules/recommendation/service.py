from sqlalchemy.orm import Session

from app.core.exceptions import InsufficientDataError, NotFoundError
from app.modules.catalog import service as catalog_service
from app.modules.catalog.enums import StorageType
from app.modules.compatibility import service as compatibility_service
from app.modules.compatibility.enums import CompatibilityRelation, CompatibilityStatus
from app.modules.compatibility.schemas import CompatibilityResult
from app.modules.performance import service as performance_service
from app.modules.performance.enums import BottleneckVerdict
from app.modules.performance.schemas import BottleneckAnalysisRequest, BottleneckAnalysisResult
from app.modules.recommendation.enums import ComponentSlot, RecommendationPriority, UpgradeProfile
from app.modules.recommendation.schemas import (
    ComponentRecommendation,
    RecommendationRequest,
    RecommendationResponse,
)

# Diferença mínima de performance_tier para considerar um candidato um "upgrade real" —
# evita recomendar troca por ganho marginal que não justificaria o custo/trabalho.
_MIN_TIER_GAIN = 8
_MIN_RAM_CAPACITY_GB = 16

# Texto do resumo (etapa 3) precisa ser lido por alguém sem vocabulário técnico de hardware
# — por isso os valores dos enums (que são slugs em inglês/maiúsculo, ex. "GPU_BOUND",
# "CUSTO_BENEFICIO") nunca aparecem direto no resumo, só através destes mapas.
_PROFILE_SUMMARY_LABELS = {
    UpgradeProfile.ECONOMICO: "economia máxima",
    UpgradeProfile.CUSTO_BENEFICIO: "melhor custo-benefício",
    UpgradeProfile.ALTO_DESEMPENHO: "alto desempenho",
    UpgradeProfile.UPGRADE_COMPLETO: "upgrade completo",
}

_BOTTLENECK_SUMMARY_LABELS = {
    BottleneckVerdict.CPU_BOUND: "o processador é o que mais está segurando seu desempenho hoje",
    BottleneckVerdict.GPU_BOUND: "a placa de vídeo é o que mais está segurando seu desempenho hoje",
    BottleneckVerdict.BALANCED: "processador e placa de vídeo estão equilibrados entre si, sem um vilão claro",
}

_SLOT_SUMMARY_LABELS = {
    "cpu": "o processador",
    "gpu": "a placa de vídeo",
    "motherboard": "a placa-mãe",
    "ram": "a memória RAM",
    "storage": "o armazenamento",
    "psu": "a fonte de alimentação",
    "case": "o gabinete",
    "cooler": "o cooler",
}

# Ordem de severidade (mais grave primeiro) usada para resumir vários CompatibilityResult
# em um único status representativo de uma recomendação.
_STATUS_SEVERITY = [
    CompatibilityStatus.INCOMPATIVEL,
    CompatibilityStatus.REQUER_TROCA_DE_OUTROS_COMPONENTES,
    CompatibilityStatus.REQUER_ATUALIZACAO_BIOS,
    CompatibilityStatus.COMPATIVEL_COM_RESSALVAS,
    CompatibilityStatus.INFORMACAO_INSUFICIENTE,
    CompatibilityStatus.COMPATIVEL,
]


def _resolve(db: Session, model_name: str | None, getter, label: str):
    if not model_name:
        return None
    obj = getter(db, model_name)
    if obj is None:
        raise NotFoundError(f"{label} '{model_name}' não encontrado no catálogo.")
    return obj


def _worst_status(results: list[CompatibilityResult]) -> CompatibilityStatus:
    if not results:
        return CompatibilityStatus.INFORMACAO_INSUFICIENTE
    return min(results, key=lambda r: _STATUS_SEVERITY.index(r.status)).status


def _priority(
    *, is_target: bool, profile: UpgradeProfile, hard_problem: bool
) -> RecommendationPriority:
    if is_target or hard_problem:
        return (
            RecommendationPriority.CRITICA
            if profile == UpgradeProfile.UPGRADE_COMPLETO
            else RecommendationPriority.ALTA
        )
    if profile in (UpgradeProfile.ALTO_DESEMPENHO, UpgradeProfile.UPGRADE_COMPLETO):
        return RecommendationPriority.MEDIA
    return RecommendationPriority.BAIXA


def _tier_gain_text(current_tier: int | None, candidate_tier: int | None) -> str:
    if current_tier is None or candidate_tier is None:
        return "Dado insuficiente para quantificar o ganho de desempenho relativo."
    gain = candidate_tier - current_tier
    return (
        f"Ganho relativo de desempenho estimado em +{gain} pontos na escala ordinal do "
        "catálogo (não é um benchmark absoluto nem um percentual)."
    )


def _cost_benefit_note(
    price_min: int | None, price_max: int | None, tier_gain: int | None = None
) -> str:
    if price_min is None and price_max is None:
        return (
            "Dado insuficiente para determinar custo-benefício — catálogo sem faixa de "
            "preço para este item."
        )
    if price_min is not None and price_max is not None:
        price_txt = f"R$ {price_min}–{price_max}"
    elif price_min is not None:
        price_txt = f"a partir de R$ {price_min}"
    else:
        price_txt = f"até R$ {price_max}"
    if tier_gain is not None:
        return f"Ganho relativo de +{tier_gain} pontos por faixa de preço estimada de {price_txt}."
    return f"Faixa de preço estimada: {price_txt}."


def _best_cost_benefit_ratio(pool: list, current_tier: int | None):
    priced = [c for c in pool if c.price_range_brl_min]
    if not priced:
        # Sem dado de preço: escolhe o meio da distribuição de tiers do pool, evitando tanto
        # o ganho marginal quanto o overkill mais caro do topo.
        ordered = sorted(pool, key=lambda c: c.performance_tier)
        return ordered[len(ordered) // 2]
    base_tier = current_tier or 0
    return max(priced, key=lambda c: (c.performance_tier - base_tier) / c.price_range_brl_min)


def _run_bottleneck(
    request: RecommendationRequest, cpu, gpu
) -> tuple[BottleneckAnalysisResult | None, str | None]:
    if cpu is None or gpu is None or request.resolution is None or request.graphics_quality is None:
        return None, None
    bottleneck_request = BottleneckAnalysisRequest(
        cpu_model_name=cpu.model_name,
        gpu_model_name=gpu.model_name,
        resolution=request.resolution,
        graphics_quality=request.graphics_quality,
        target_fps=request.target_fps,
        workload_type=request.workload_type,
    )
    try:
        return performance_service.analyze_bottleneck(cpu, gpu, bottleneck_request), None
    except InsufficientDataError as exc:
        return None, exc.message


def _pick_cpu_candidate(db: Session, current_cpu, motherboard, profile: UpgradeProfile):
    candidates = [
        c
        for c in catalog_service.list_cpus(db)
        if c.performance_tier is not None and c.model_name != current_cpu.model_name
    ]
    if current_cpu.performance_tier is not None:
        candidates = [
            c
            for c in candidates
            if c.performance_tier - current_cpu.performance_tier >= _MIN_TIER_GAIN
        ]
    if not candidates:
        return None

    # Para os perfis mais conservadores, priorizamos manter o socket atual (evita forçar
    # troca de placa-mãe); perfis agressivos podem cruzar plataforma em busca do topo.
    # O socket da CPU atual é conhecido mesmo sem o modelo exato da placa-mãe — ela só
    # funciona no socket da placa em que está instalada — então usamos isso como o socket
    # "atual" em vez de tratar placa-mãe desconhecida como "qualquer socket serve".
    current_socket = motherboard.socket if motherboard is not None else current_cpu.socket
    same_socket = [c for c in candidates if c.socket == current_socket]

    if profile == UpgradeProfile.ECONOMICO:
        pool = same_socket or candidates
        return min(pool, key=lambda c: c.performance_tier)
    if profile == UpgradeProfile.CUSTO_BENEFICIO:
        pool = same_socket or candidates
        return _best_cost_benefit_ratio(pool, current_cpu.performance_tier)
    return max(candidates, key=lambda c: c.performance_tier)


def _pick_gpu_candidate(db: Session, current_gpu, profile: UpgradeProfile):
    candidates = [
        g
        for g in catalog_service.list_gpus(db)
        if g.performance_tier is not None and g.model_name != current_gpu.model_name
    ]
    if current_gpu.performance_tier is not None:
        candidates = [
            g
            for g in candidates
            if g.performance_tier - current_gpu.performance_tier >= _MIN_TIER_GAIN
        ]
    if not candidates:
        return None
    if profile == UpgradeProfile.ECONOMICO:
        return min(candidates, key=lambda g: g.performance_tier)
    if profile == UpgradeProfile.CUSTO_BENEFICIO:
        return _best_cost_benefit_ratio(candidates, current_gpu.performance_tier)
    return max(candidates, key=lambda g: g.performance_tier)


def _recommend_cpu(
    db: Session, cpu, motherboard, profile: UpgradeProfile, *, is_target: bool, bottleneck
):
    candidate = _pick_cpu_candidate(db, cpu, motherboard, profile)
    if candidate is None:
        return None, []

    results: list[CompatibilityResult] = []
    if motherboard is not None:
        results.append(compatibility_service.check_cpu_motherboard(candidate, motherboard))
    elif candidate.socket != cpu.socket:
        # Placa-mãe não informada, mas o socket da CPU recomendada difere do socket da CPU
        # atual — isso exige troca de placa-mãe em qualquer plataforma, independentemente do
        # modelo exato dela (que não temos). Nunca fica silencioso só por falta desse dado.
        results.append(
            CompatibilityResult(
                relation=CompatibilityRelation.CPU_MOTHERBOARD,
                status=CompatibilityStatus.INCOMPATIVEL,
                reason=(
                    f"Este processador usa o socket {candidate.socket}, diferente do socket "
                    f"{cpu.socket} da sua CPU atual — isso exige trocar também a placa-mãe "
                    "(modelo exato não informado, mas a troca de socket é obrigatória em "
                    "qualquer placa)."
                ),
                additional_required_components=["motherboard"],
            )
        )

    additional = sorted({c for r in results for c in r.additional_required_components})
    limitations = [r.reason for r in results if r.status != CompatibilityStatus.COMPATIVEL]

    if is_target and bottleneck is not None:
        problem = bottleneck.explanation
    else:
        problem = (
            "Sua CPU atual possui desempenho relativo bem abaixo de opções disponíveis no "
            "catálogo para o perfil de upgrade escolhido."
        )

    tier_gain = (
        candidate.performance_tier - cpu.performance_tier
        if cpu.performance_tier is not None and candidate.performance_tier is not None
        else None
    )

    rec = ComponentRecommendation(
        slot=ComponentSlot.CPU,
        current_model_name=cpu.model_name,
        problem=problem,
        recommended_model_name=candidate.model_name,
        expected_gain=_tier_gain_text(cpu.performance_tier, candidate.performance_tier),
        compatibility_status=_worst_status(results),
        additional_required_components=[ComponentSlot(c) for c in additional],
        remaining_limitations=limitations,
        priority=_priority(is_target=is_target, profile=profile, hard_problem=False),
        cost_benefit=_cost_benefit_note(
            candidate.price_range_brl_min, candidate.price_range_brl_max, tier_gain
        ),
    )
    return rec, results


def _recommend_gpu(
    db: Session, gpu, psu, case, motherboard, profile: UpgradeProfile, *, is_target: bool
):
    candidate = _pick_gpu_candidate(db, gpu, profile)
    if candidate is None:
        return None, []

    results: list[CompatibilityResult] = []
    if psu is not None:
        results.append(compatibility_service.check_gpu_psu(candidate, psu))
    if motherboard is not None:
        results.append(compatibility_service.check_pcie_interface(motherboard, candidate))
    if case is not None:
        results.append(compatibility_service.check_case_gpu(case, candidate))

    additional = sorted({c for r in results for c in r.additional_required_components})
    limitations = [r.reason for r in results if r.status != CompatibilityStatus.COMPATIVEL]

    problem = (
        "Sua GPU tem folga de desempenho relativo em relação à CPU/cenário informado, o que "
        "pode limitar a taxa de quadros antes da GPU atingir seu potencial."
        if is_target
        else (
            "GPU atual possui desempenho relativo bem abaixo de opções disponíveis no "
            "catálogo para o perfil de upgrade escolhido."
        )
    )

    tier_gain = (
        candidate.performance_tier - gpu.performance_tier
        if gpu.performance_tier is not None and candidate.performance_tier is not None
        else None
    )

    rec = ComponentRecommendation(
        slot=ComponentSlot.GPU,
        current_model_name=gpu.model_name,
        problem=problem,
        recommended_model_name=candidate.model_name,
        expected_gain=_tier_gain_text(gpu.performance_tier, candidate.performance_tier),
        compatibility_status=_worst_status(results),
        additional_required_components=[ComponentSlot(c) for c in additional],
        remaining_limitations=limitations,
        priority=_priority(is_target=is_target, profile=profile, hard_problem=False),
        cost_benefit=_cost_benefit_note(
            candidate.price_range_brl_min, candidate.price_range_brl_max, tier_gain
        ),
    )
    return rec, results


def _recommend_ram(db: Session, ram, motherboard, profile: UpgradeProfile):
    target_gb = (
        32
        if profile in (UpgradeProfile.ALTO_DESEMPENHO, UpgradeProfile.UPGRADE_COMPLETO)
        else _MIN_RAM_CAPACITY_GB
    )

    # Sem a placa-mãe, o tipo de memória do kit atual (DDR4/DDR5...) é o melhor proxy do que
    # a placa suporta — o kit só funciona no tipo que a placa aceita. Nunca recomendamos um
    # tipo diferente sem confirmar a placa, mesmo em perfis mais agressivos.
    current_memory_type = (
        motherboard.memory_type.value if motherboard is not None else ram.memory_type.value
    )
    pool = catalog_service.list_ram_kits(db, memory_type=current_memory_type)
    pool = [
        k
        for k in pool
        if k.capacity_gb_per_module * k.modules_in_kit >= target_gb
        and k.model_name != ram.model_name
    ]
    if not pool:
        return None, []
    candidate = min(pool, key=lambda k: k.capacity_gb_per_module * k.modules_in_kit)

    results: list[CompatibilityResult] = []
    if motherboard is not None:
        results.append(compatibility_service.check_motherboard_ram(motherboard, candidate))

    additional = sorted({c for r in results for c in r.additional_required_components})
    limitations = [r.reason for r in results if r.status != CompatibilityStatus.COMPATIVEL]

    current_gb = ram.capacity_gb_per_module * ram.modules_in_kit
    candidate_gb = candidate.capacity_gb_per_module * candidate.modules_in_kit

    rec = ComponentRecommendation(
        slot=ComponentSlot.RAM,
        current_model_name=ram.model_name,
        problem=(
            f"Capacidade total de {current_gb}GB é baixa para uso moderno — pode causar uso "
            "de memória virtual (swap) e engasgos em jogos ou aplicações mais pesadas."
        ),
        recommended_model_name=candidate.model_name,
        expected_gain=f"Aumento de capacidade de {current_gb}GB para {candidate_gb}GB.",
        compatibility_status=_worst_status(results),
        additional_required_components=[ComponentSlot(c) for c in additional],
        remaining_limitations=limitations,
        priority=_priority(is_target=False, profile=profile, hard_problem=True),
        cost_benefit=_cost_benefit_note(
            candidate.price_range_brl_min, candidate.price_range_brl_max
        ),
    )
    return rec, results


def _recommend_storage(db: Session, storage, motherboard, profile: UpgradeProfile):
    prefer_nvme = motherboard is not None and (motherboard.m2_slots or 0) > 0
    storage_type = StorageType.NVME_SSD if prefer_nvme else StorageType.SATA_SSD

    pool = [
        s
        for s in catalog_service.list_storage(db, storage_type=storage_type.value)
        if s.model_name != storage.model_name
    ]
    if not pool:
        return None, []

    target_capacity = storage.capacity_gb or 0
    same_or_larger = [s for s in pool if (s.capacity_gb or 0) >= target_capacity] or pool

    if profile == UpgradeProfile.ECONOMICO:
        candidate = min(same_or_larger, key=lambda s: s.capacity_gb or 0)
    elif profile in (UpgradeProfile.ALTO_DESEMPENHO, UpgradeProfile.UPGRADE_COMPLETO):
        candidate = max(same_or_larger, key=lambda s: s.capacity_gb or 0)
    else:
        ordered = sorted(same_or_larger, key=lambda s: s.capacity_gb or 0)
        candidate = ordered[len(ordered) // 2]

    results: list[CompatibilityResult] = []
    if motherboard is not None:
        results.append(compatibility_service.check_motherboard_storage(motherboard, candidate))

    additional = sorted({c for r in results for c in r.additional_required_components})
    limitations = [r.reason for r in results if r.status != CompatibilityStatus.COMPATIVEL]

    rec = ComponentRecommendation(
        slot=ComponentSlot.STORAGE,
        current_model_name=storage.model_name,
        problem=(
            "Armazenamento atual é um HDD — tempos de boot, carregamento e resposta geral do "
            "sistema tendem a ser sensivelmente mais lentos que em um SSD."
        ),
        recommended_model_name=candidate.model_name,
        expected_gain=(
            "Redução expressiva em tempos de boot e carregamento (SSD vs. HDD é uma troca de "
            "tecnologia, não apenas de tier de desempenho — ganho qualitativo consistente)."
        ),
        compatibility_status=_worst_status(results),
        additional_required_components=[ComponentSlot(c) for c in additional],
        remaining_limitations=limitations,
        priority=_priority(is_target=False, profile=profile, hard_problem=True),
        cost_benefit=_cost_benefit_note(
            candidate.price_range_brl_min, candidate.price_range_brl_max
        ),
    )
    return rec, results


def _join_pt(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " e " + items[-1]


def _build_summary(recommendations, bottleneck, bundle, profile: UpgradeProfile) -> str:
    profile_label = _PROFILE_SUMMARY_LABELS[profile]

    if not recommendations:
        return (
            f"Boa notícia: para o perfil de {profile_label}, seu computador atual já dá "
            "conta do recado — não encontramos nenhuma peça que precise ser trocada agora."
        )

    count = len(recommendations)
    piece_word = "peça" if count == 1 else "peças"
    parts = [
        f"Encontramos {count} {piece_word} que vale a pena trocar, pensando em {profile_label}."
    ]

    bottleneck_label = (
        _BOTTLENECK_SUMMARY_LABELS.get(bottleneck.verdict) if bottleneck is not None else None
    )
    if bottleneck_label is not None:
        parts.append(f"Hoje, {bottleneck_label}.")

    if bundle is not None:
        bundle_labels = [_SLOT_SUMMARY_LABELS.get(c, c) for c in bundle.components]
        parts.append(
            "Atenção: essas trocas só funcionam juntas — não dá para trocar uma peça sem "
            "trocar também " + _join_pt(bundle_labels) + "."
        )

    return " ".join(parts)


def generate_recommendations(db: Session, request: RecommendationRequest) -> RecommendationResponse:
    system = request.system
    cpu = _resolve(db, system.cpu_model_name, catalog_service.get_cpu_by_model_name, "CPU")
    gpu = _resolve(db, system.gpu_model_name, catalog_service.get_gpu_by_model_name, "GPU")
    motherboard = _resolve(
        db,
        system.motherboard_model_name,
        catalog_service.get_motherboard_by_model_name,
        "Placa-mãe",
    )
    ram = _resolve(
        db, system.ram_model_name, catalog_service.get_ram_kit_by_model_name, "Kit de RAM"
    )
    storage = _resolve(
        db, system.storage_model_name, catalog_service.get_storage_by_model_name, "Armazenamento"
    )
    psu = _resolve(db, system.psu_model_name, catalog_service.get_psu_by_model_name, "Fonte")
    case = _resolve(db, system.case_model_name, catalog_service.get_case_by_model_name, "Gabinete")

    bottleneck, bottleneck_note = _run_bottleneck(request, cpu, gpu)
    flagged_cpu = bottleneck is not None and bottleneck.limiting_component == "cpu"
    flagged_gpu = bottleneck is not None and bottleneck.limiting_component == "gpu"
    aggressive = request.profile in (
        UpgradeProfile.ALTO_DESEMPENHO,
        UpgradeProfile.UPGRADE_COMPLETO,
    )

    recommendations: list[ComponentRecommendation] = []
    compat_results: list[CompatibilityResult] = []

    if cpu is not None and (flagged_cpu or aggressive):
        rec, results = _recommend_cpu(
            db, cpu, motherboard, request.profile, is_target=flagged_cpu, bottleneck=bottleneck
        )
        if rec is not None:
            recommendations.append(rec)
            compat_results.extend(results)

    if gpu is not None and (flagged_gpu or aggressive):
        rec, results = _recommend_gpu(
            db, gpu, psu, case, motherboard, request.profile, is_target=flagged_gpu
        )
        if rec is not None:
            recommendations.append(rec)
            compat_results.extend(results)

    if ram is not None and (ram.capacity_gb_per_module * ram.modules_in_kit) < _MIN_RAM_CAPACITY_GB:
        rec, results = _recommend_ram(db, ram, motherboard, request.profile)
        if rec is not None:
            recommendations.append(rec)
            compat_results.extend(results)

    if storage is not None and storage.storage_type == StorageType.HDD:
        rec, results = _recommend_storage(db, storage, motherboard, request.profile)
        if rec is not None:
            recommendations.append(rec)
            compat_results.extend(results)

    bundle = compatibility_service.build_bundle(compat_results)

    return RecommendationResponse(
        profile=request.profile,
        bottleneck=bottleneck,
        bottleneck_note=bottleneck_note,
        recommendations=recommendations,
        bundle=bundle,
        summary=_build_summary(recommendations, bottleneck, bundle, request.profile),
    )
