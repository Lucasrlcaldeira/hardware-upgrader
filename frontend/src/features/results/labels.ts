import type { CompatibilityRelation, CompatibilityStatus } from '../../types/compatibility'
import type { CheckStatus, GameVerdict, RequirementComponent } from '../../types/games'
import type {
  BottleneckVerdict,
  ConfidenceLevel,
  GraphicsQuality,
  Resolution,
  WorkloadType,
} from '../../types/performance'
import type { ComponentSlot, RecommendationPriority, UpgradeProfile } from '../../types/recommendation'

export const RESOLUTION_LABELS: Record<Resolution, string> = {
  '1080P': '1080p (Full HD)',
  '1440P': '1440p (2K)',
  '4K': '4K (2160p)',
}

export const GRAPHICS_QUALITY_LABELS: Record<GraphicsQuality, string> = {
  LOW: 'Baixa',
  MEDIUM: 'Média',
  HIGH: 'Alta',
  ULTRA: 'Ultra',
}

export const WORKLOAD_TYPE_LABELS: Record<WorkloadType, string> = {
  GAMING: 'Jogos',
  CONTENT_CREATION: 'Criação de conteúdo',
  PRODUCTIVITY: 'Produtividade',
  GENERAL: 'Uso geral',
}

export const PROFILE_LABELS: Record<UpgradeProfile, string> = {
  ECONOMICO: 'Econômico',
  CUSTO_BENEFICIO: 'Custo-benefício',
  ALTO_DESEMPENHO: 'Alto desempenho',
  UPGRADE_COMPLETO: 'Upgrade completo',
}

export const PROFILE_DESCRIPTIONS: Record<UpgradeProfile, string> = {
  ECONOMICO: 'Gasta o mínimo possível, aproveitando ao máximo o que você já tem.',
  CUSTO_BENEFICIO: 'O melhor equilíbrio entre preço e ganho de desempenho.',
  ALTO_DESEMPENHO: 'Foco em desempenho, mesmo que precise trocar mais peças.',
  UPGRADE_COMPLETO: 'Mostra tudo que vale a pena modernizar na sua máquina.',
}

export const COMPATIBILITY_STATUS_LABELS: Record<CompatibilityStatus, string> = {
  COMPATIVEL: 'Compatível',
  INCOMPATIVEL: 'Incompatível',
  COMPATIVEL_COM_RESSALVAS: 'Compatível com ressalvas',
  REQUER_ATUALIZACAO_BIOS: 'Requer atualização de BIOS',
  REQUER_TROCA_DE_OUTROS_COMPONENTES: 'Requer troca de outros componentes',
  INFORMACAO_INSUFICIENTE: 'Informação insuficiente',
}

export const COMPATIBILITY_STATUS_STYLES: Record<CompatibilityStatus, string> = {
  COMPATIVEL: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  INCOMPATIVEL: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  COMPATIVEL_COM_RESSALVAS: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  REQUER_ATUALIZACAO_BIOS: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  REQUER_TROCA_DE_OUTROS_COMPONENTES:
    'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  INFORMACAO_INSUFICIENTE: 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
}

export const COMPATIBILITY_RELATION_LABELS: Record<CompatibilityRelation, string> = {
  cpu_motherboard: 'CPU ↔ Placa-mãe',
  motherboard_ram: 'Placa-mãe ↔ RAM',
  gpu_psu: 'GPU ↔ Fonte',
  cpu_gpu_pcie: 'Interface PCIe (Placa-mãe ↔ GPU)',
  motherboard_storage: 'Placa-mãe ↔ Armazenamento',
  case_gpu: 'Gabinete ↔ GPU',
  case_motherboard: 'Gabinete ↔ Placa-mãe',
  cooler_cpu: 'Cooler ↔ CPU',
}

export const BOTTLENECK_VERDICT_LABELS: Record<BottleneckVerdict, string> = {
  CPU_BOUND: 'Limitado pela CPU',
  GPU_BOUND: 'Limitado pela GPU',
  BALANCED: 'Equilibrado',
  INSUFFICIENT_DATA: 'Dado insuficiente',
}

export const CONFIDENCE_LABELS: Record<ConfidenceLevel, string> = {
  BAIXA: 'Confiança baixa',
  MEDIA: 'Confiança média',
  ALTA: 'Confiança alta',
}

export const PRIORITY_LABELS: Record<RecommendationPriority, string> = {
  CRITICA: 'Crítica',
  ALTA: 'Alta',
  MEDIA: 'Média',
  BAIXA: 'Baixa',
}

export const PRIORITY_STYLES: Record<RecommendationPriority, string> = {
  CRITICA: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  ALTA: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  MEDIA: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  BAIXA: 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
}

export const SLOT_LABELS: Record<ComponentSlot, string> = {
  cpu: 'Processador (CPU)',
  gpu: 'Placa de vídeo (GPU)',
  motherboard: 'Placa-mãe',
  ram: 'Memória RAM',
  storage: 'Armazenamento',
  psu: 'Fonte de alimentação',
  case: 'Gabinete',
  cooler: 'Cooler',
}

export function slotLabel(slot: string): string {
  return SLOT_LABELS[slot as ComponentSlot] ?? slot
}

export const GAME_VERDICT_LABELS: Record<GameVerdict, string> = {
  RODA_NO_RECOMENDADO: 'Roda no recomendado',
  RODA_NO_MINIMO: 'Roda no mínimo',
  ABAIXO_DO_MINIMO: 'Abaixo do mínimo',
  INDETERMINADO: 'Não deu pra cravar',
}

export const GAME_VERDICT_STYLES: Record<GameVerdict, string> = {
  RODA_NO_RECOMENDADO:
    'border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200',
  RODA_NO_MINIMO:
    'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200',
  ABAIXO_DO_MINIMO:
    'border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-950/30 dark:text-red-200',
  INDETERMINADO:
    'border-slate-300 bg-slate-50 text-slate-900 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-200',
}

export const CHECK_STATUS_LABELS: Record<CheckStatus, string> = {
  ATENDE: 'Atende',
  NAO_ATENDE: 'Não atende',
  NAO_DETERMINADO: 'Não deu pra comparar',
}

export const CHECK_STATUS_STYLES: Record<CheckStatus, string> = {
  ATENDE: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  NAO_ATENDE: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  NAO_DETERMINADO: 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
}

export const REQUIREMENT_COMPONENT_LABELS: Record<RequirementComponent, string> = {
  cpu: 'Processador',
  gpu: 'Placa de vídeo',
  vram: 'Memória da placa de vídeo',
  ram: 'Memória RAM',
  storage: 'Armazenamento',
  os: 'Sistema operacional',
}
