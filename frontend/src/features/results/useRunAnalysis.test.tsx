import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as compatibilityApi from '../../api/compatibility'
import { ApiError } from '../../api/client'
import * as performanceApi from '../../api/performance'
import * as recommendationApi from '../../api/recommendation'
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

describe('useRunAnalysis', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('combines compatibility, bottleneck and recommendation results', async () => {
    vi.spyOn(compatibilityApi, 'checkCompatibility').mockResolvedValue({
      results: [],
      bundle: null,
    })
    vi.spyOn(recommendationApi, 'generateRecommendations').mockResolvedValue({
      profile: 'ECONOMICO',
      bottleneck: null,
      bottleneck_note: null,
      recommendations: [],
      bundle: null,
      summary: 'ok',
    })
    vi.spyOn(performanceApi, 'checkBottleneck').mockResolvedValue({
      verdict: 'CPU_BOUND',
      limiting_component: 'cpu',
      explanation: 'explicação',
      contributing_factors: [],
      confidence: 'MEDIA',
    })

    const { result } = renderHook(() => useRunAnalysis(), { wrapper })
    result.current.mutate(baseConfig)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.bottleneck?.verdict).toBe('CPU_BOUND')
    expect(result.current.data?.bottleneckNote).toBeNull()
  })

  it('turns a 422 from the bottleneck check into a note instead of failing the whole analysis', async () => {
    vi.spyOn(compatibilityApi, 'checkCompatibility').mockResolvedValue({
      results: [],
      bundle: null,
    })
    vi.spyOn(recommendationApi, 'generateRecommendations').mockResolvedValue({
      profile: 'ECONOMICO',
      bottleneck: null,
      bottleneck_note: 'Dado insuficiente para determinar gargalo.',
      recommendations: [],
      bundle: null,
      summary: 'ok',
    })
    vi.spyOn(performanceApi, 'checkBottleneck').mockRejectedValue(
      new ApiError(422, 'Dado insuficiente para determinar gargalo.'),
    )

    const { result } = renderHook(() => useRunAnalysis(), { wrapper })
    result.current.mutate(baseConfig)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.bottleneck).toBeNull()
    expect(result.current.data?.bottleneckNote).toBe('Dado insuficiente para determinar gargalo.')
  })

  it('skips the bottleneck call entirely when resolution/quality are not provided', async () => {
    vi.spyOn(compatibilityApi, 'checkCompatibility').mockResolvedValue({
      results: [],
      bundle: null,
    })
    vi.spyOn(recommendationApi, 'generateRecommendations').mockResolvedValue({
      profile: 'ECONOMICO',
      bottleneck: null,
      bottleneck_note: null,
      recommendations: [],
      bundle: null,
      summary: 'ok',
    })
    const bottleneckSpy = vi.spyOn(performanceApi, 'checkBottleneck')

    const { result } = renderHook(() => useRunAnalysis(), { wrapper })
    result.current.mutate({ ...baseConfig, resolution: null, graphics_quality: null })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(bottleneckSpy).not.toHaveBeenCalled()
    expect(result.current.data?.bottleneckNote).toContain('resolução')
  })
})
