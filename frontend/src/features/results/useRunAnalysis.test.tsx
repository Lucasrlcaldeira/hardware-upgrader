import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as compatibilityApi from '../../api/compatibility'
import * as recommendationApi from '../../api/recommendation'
import type { RecommendationResponse } from '../../types/recommendation'
import type { AnalysisConfig } from '../system/SystemSelectionStep'
import { useRunAnalysis } from './useRunAnalysis'

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient()
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

const baseConfig: AnalysisConfig = {
  system: { cpu_model_name: 'CPU Fraca', gpu_model_name: 'GPU Forte' },
  profile: 'ECONOMICO',
  resolution: '1080P',
  graphics_quality: 'LOW',
  target_fps: null,
  workload_type: 'GAMING',
}

function recommendationResponse(overrides: Partial<RecommendationResponse>): RecommendationResponse {
  return {
    profile: 'ECONOMICO',
    bottleneck: null,
    bottleneck_note: null,
    recommendations: [],
    bundle: null,
    summary: 'ok',
    ...overrides,
  }
}

describe('useRunAnalysis', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('combines compatibility with the bottleneck already computed by the recommendation', async () => {
    vi.spyOn(compatibilityApi, 'checkCompatibility').mockResolvedValue({ results: [], bundle: null })
    vi.spyOn(recommendationApi, 'generateRecommendations').mockResolvedValue(
      recommendationResponse({
        bottleneck: {
          verdict: 'CPU_BOUND',
          limiting_component: 'cpu',
          explanation: 'explicação',
          contributing_factors: [],
          confidence: 'MEDIA',
        },
      }),
    )

    const { result } = renderHook(() => useRunAnalysis(), { wrapper })
    result.current.mutate(baseConfig)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.bottleneck?.verdict).toBe('CPU_BOUND')
    expect(result.current.data?.bottleneckNote).toBeNull()
  })

  it('surfaces the "insufficient data" note from the recommendation instead of failing', async () => {
    vi.spyOn(compatibilityApi, 'checkCompatibility').mockResolvedValue({ results: [], bundle: null })
    vi.spyOn(recommendationApi, 'generateRecommendations').mockResolvedValue(
      recommendationResponse({ bottleneck_note: 'Dado insuficiente para determinar gargalo.' }),
    )

    const { result } = renderHook(() => useRunAnalysis(), { wrapper })
    result.current.mutate(baseConfig)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.bottleneck).toBeNull()
    expect(result.current.data?.bottleneckNote).toBe('Dado insuficiente para determinar gargalo.')
  })

  it('explains what is missing when the backend could not run the bottleneck check', async () => {
    vi.spyOn(compatibilityApi, 'checkCompatibility').mockResolvedValue({ results: [], bundle: null })
    vi.spyOn(recommendationApi, 'generateRecommendations').mockResolvedValue(
      recommendationResponse({}),
    )

    const { result } = renderHook(() => useRunAnalysis(), { wrapper })
    result.current.mutate({ ...baseConfig, system: { cpu_model_name: 'CPU Fraca' } })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.bottleneckNote).toContain('resolução')
  })
})
