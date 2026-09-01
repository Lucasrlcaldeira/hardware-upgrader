import type { CompatibilityStatus, BundleUpgrade, SystemSnapshot } from './compatibility'
import type {
  BottleneckAnalysisResult,
  GraphicsQuality,
  Resolution,
  WorkloadType,
} from './performance'

export type UpgradeProfile = 'ECONOMICO' | 'CUSTO_BENEFICIO' | 'ALTO_DESEMPENHO' | 'UPGRADE_COMPLETO'
export type RecommendationPriority = 'CRITICA' | 'ALTA' | 'MEDIA' | 'BAIXA'
export type ComponentSlot =
  | 'cpu'
  | 'gpu'
  | 'motherboard'
  | 'ram'
  | 'storage'
  | 'psu'
  | 'case'
  | 'cooler'

export interface RecommendationRequest {
  system: SystemSnapshot
  profile: UpgradeProfile
  resolution?: Resolution | null
  graphics_quality?: GraphicsQuality | null
  target_fps?: number | null
  workload_type: WorkloadType
}

export interface ComponentRecommendation {
  slot: ComponentSlot
  current_model_name: string | null
  problem: string
  recommended_model_name: string
  expected_gain: string
  compatibility_status: CompatibilityStatus
  additional_required_components: ComponentSlot[]
  remaining_limitations: string[]
  priority: RecommendationPriority
  cost_benefit: string
}

export interface RecommendationResponse {
  profile: UpgradeProfile
  bottleneck: BottleneckAnalysisResult | null
  bottleneck_note: string | null
  recommendations: ComponentRecommendation[]
  bundle: BundleUpgrade | null
  summary: string
}
