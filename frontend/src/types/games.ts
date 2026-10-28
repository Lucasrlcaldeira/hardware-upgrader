import type { SystemSnapshot } from './compatibility'
import type { HardwareSnapshot } from './detection'

export type RequirementTier = 'MINIMUM' | 'RECOMMENDED'
export type RequirementComponent = 'cpu' | 'gpu' | 'vram' | 'ram' | 'storage' | 'os'
export type CheckStatus = 'ATENDE' | 'NAO_ATENDE' | 'NAO_DETERMINADO'
export type GameVerdict =
  | 'RODA_NO_RECOMENDADO'
  | 'RODA_NO_MINIMO'
  | 'ABAIXO_DO_MINIMO'
  | 'INDETERMINADO'

export interface SteamGameSummary {
  app_id: number
  name: string
  image_url: string | null
}

export interface GameRequirementsCheckRequest {
  app_id: number
  system: SystemSnapshot
  detected?: HardwareSnapshot | null
  upgraded_system?: SystemSnapshot | null
}

export interface RequirementLine {
  label: string
  value: string
}

export interface RequirementCheck {
  component: RequirementComponent
  required: string
  yours: string | null
  status: CheckStatus
  explanation: string
  counts_for_verdict: boolean
}

export interface TierEvaluation {
  tier: RequirementTier
  status: CheckStatus
  checks: RequirementCheck[]
}

export interface SystemEvaluation {
  verdict: GameVerdict
  verdict_text: string
  minimum: TierEvaluation | null
  recommended: TierEvaluation | null
}

export interface GameRequirementsCheckResult {
  app_id: number
  name: string
  store_url: string
  header_image: string | null
  minimum_requirements: RequirementLine[]
  recommended_requirements: RequirementLine[]
  current: SystemEvaluation
  upgraded: SystemEvaluation | null
  disclaimer: string
}
