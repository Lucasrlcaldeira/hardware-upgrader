import { useMutation } from '@tanstack/react-query'
import { checkCompatibility } from '../../api/compatibility'
import { generateRecommendations } from '../../api/recommendation'
import type { CompatibilityCheckResponse, SystemSnapshot } from '../../types/compatibility'
import type { BottleneckAnalysisResult } from '../../types/performance'
import type { RecommendationResponse } from '../../types/recommendation'
import type { AnalysisConfig } from '../system/SystemSelectionStep'

export interface CombinedAnalysisResult {
  system: SystemSnapshot
  compatibility: CompatibilityCheckResponse
  bottleneck: BottleneckAnalysisResult | null
  bottleneckNote: string | null
  recommendation: RecommendationResponse
}

const MISSING_BOTTLENECK_INPUT_NOTE =
  'Pra ver o que está te segurando, a gente precisa saber sua CPU, GPU, resolução e qualidade gráfica.'

async function runAnalysis(config: AnalysisConfig): Promise<CombinedAnalysisResult> {
  const { system, profile, resolution, graphics_quality, target_fps, workload_type } = config

  // Disparadas juntas para rodar em paralelo. O gargalo não tem chamada própria: o motor de
  // recomendação já roda a mesma análise de gargalo no backend (é ela que decide se a CPU
  // ou a GPU entram na recomendação) e devolve o resultado — inclusive o "dado insuficiente"
  // em bottleneck_note — então pedir de novo em /performance/bottleneck era trabalho dobrado.
  const compatibilityPromise = checkCompatibility(system)
  const recommendationPromise = generateRecommendations({
    system,
    profile,
    resolution,
    graphics_quality,
    target_fps,
    workload_type,
  })

  const compatibility = await compatibilityPromise
  const recommendation = await recommendationPromise

  const bottleneck = recommendation.bottleneck
  const bottleneckNote = bottleneck
    ? null
    : (recommendation.bottleneck_note ?? MISSING_BOTTLENECK_INPUT_NOTE)

  return { system, compatibility, recommendation, bottleneck, bottleneckNote }
}

export function useRunAnalysis() {
  return useMutation({ mutationFn: runAnalysis })
}
