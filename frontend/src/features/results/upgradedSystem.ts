import type { SystemSnapshot } from '../../types/compatibility'
import type { ComponentRecommendation, ComponentSlot } from '../../types/recommendation'

// Só essas peças mudam a comparação com os requisitos da Steam — placa-mãe, fonte etc. não
// aparecem nos requisitos de nenhum jogo.
const UPGRADE_KEYS: Partial<Record<ComponentSlot, keyof SystemSnapshot>> = {
  cpu: 'cpu_model_name',
  gpu: 'gpu_model_name',
  ram: 'ram_model_name',
}

/** O PC do usuário com os upgrades recomendados aplicados, ou null se nenhum faz diferença. */
export function buildUpgradedSystem(
  system: SystemSnapshot,
  recommendations: ComponentRecommendation[],
): { system: SystemSnapshot; names: string[] } | null {
  const upgraded: SystemSnapshot = { ...system }
  const names: string[] = []
  for (const rec of recommendations) {
    const key = UPGRADE_KEYS[rec.slot]
    if (!key) continue
    upgraded[key] = rec.recommended_model_name
    names.push(rec.recommended_model_name)
  }
  return names.length > 0 ? { system: upgraded, names } : null
}
