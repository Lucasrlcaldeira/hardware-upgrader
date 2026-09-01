import { useMutation } from '@tanstack/react-query'
import { ApiError } from '../../api/client'
import { checkCompatibility } from '../../api/compatibility'
import { checkBottleneck } from '../../api/performance'
import { generateRecommendations } from '../../api/recommendation'
import type { CompatibilityCheckResponse } from '../../types/compatibility'
import type { BottleneckAnalysisResult } from '../../types/performance'
import type { RecommendationResponse } from '../../types/recommendation'
import type { AnalysisConfig } from '../system/SystemSelectionStep'

export interface CombinedAnalysisResult {
  compatibility: CompatibilityCheckResponse
  bottleneck: BottleneckAnalysisResult | null
  bottleneckNote: string | null
  recommendation: RecommendationResponse
}

async function runAnalysis(config: AnalysisConfig): Promise<CombinedAnalysisResult> {
  const { system, profile, resolution, graphics_quality, target_fps, workload_type } = config
  const canCheckBottleneck = Boolean(
    system.cpu_model_name && system.gpu_model_name && resolution && graphics_quality,
  )

  // Disparadas juntas (não aguardadas ainda) para rodar em paralelo — compatibility e
  // recommendation exercitam o catálogo inteiro do sistema selecionado, enquanto bottleneck
  // depende apenas de CPU/GPU/cenário e é opcional (pode faltar dado suficiente).
  const compatibilityPromise = checkCompatibility(system)
  const recommendationPromise = generateRecommendations({
    system,
    profile,
    resolution,
    graphics_quality,
    target_fps,
    workload_type,
  })
  const bottleneckPromise = canCheckBottleneck
    ? checkBottleneck({
        cpu_model_name: system.cpu_model_name as string,
        gpu_model_name: system.gpu_model_name as string,
        resolution: resolution as NonNullable<typeof resolution>,
        graphics_quality: graphics_quality as NonNullable<typeof graphics_quality>,
        target_fps: target_fps ?? undefined,
        workload_type,
      })
    : null

  const compatibility = await compatibilityPromise
  const recommendation = await recommendationPromise

  let bottleneck: BottleneckAnalysisResult | null = null
  let bottleneckNote: string | null = canCheckBottleneck
    ? null
    : 'Informe CPU, GPU, resolução e qualidade gráfica para calcular o gargalo.'

  if (bottleneckPromise) {
    try {
      bottleneck = await bottleneckPromise
    } catch (err) {
      // 422 = "dado insuficiente para determinar" (ex: catálogo sem performance_tier para o
      // componente) — é uma resposta válida do domínio, não uma falha da análise inteira.
      if (err instanceof ApiError && err.status === 422) {
        bottleneckNote = err.message
      } else {
        throw err
      }
    }
  }

  return { compatibility, recommendation, bottleneck, bottleneckNote }
}

export function useRunAnalysis() {
  return useMutation({ mutationFn: runAnalysis })
}
