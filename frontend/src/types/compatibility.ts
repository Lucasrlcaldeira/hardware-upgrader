export type CompatibilityStatus =
  | 'COMPATIVEL'
  | 'INCOMPATIVEL'
  | 'COMPATIVEL_COM_RESSALVAS'
  | 'REQUER_ATUALIZACAO_BIOS'
  | 'REQUER_TROCA_DE_OUTROS_COMPONENTES'
  | 'INFORMACAO_INSUFICIENTE'

export type CompatibilityRelation =
  | 'cpu_motherboard'
  | 'motherboard_ram'
  | 'gpu_psu'
  | 'cpu_gpu_pcie'
  | 'motherboard_storage'
  | 'case_gpu'
  | 'case_motherboard'
  | 'cooler_cpu'

export interface CompatibilityResult {
  relation: CompatibilityRelation
  status: CompatibilityStatus
  reason: string
  additional_required_components: string[]
}

export interface BundleUpgrade {
  components: string[]
  reason: string
}

export interface SystemSnapshot {
  cpu_model_name?: string | null
  gpu_model_name?: string | null
  motherboard_model_name?: string | null
  ram_model_name?: string | null
  storage_model_name?: string | null
  psu_model_name?: string | null
  case_model_name?: string | null
  cooler_model_name?: string | null
}

export interface CompatibilityCheckResponse {
  results: CompatibilityResult[]
  bundle: BundleUpgrade | null
}
