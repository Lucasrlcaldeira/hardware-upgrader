import { apiPost } from './client'
import type { BottleneckAnalysisRequest, BottleneckAnalysisResult } from '../types/performance'

export function checkBottleneck(
  payload: BottleneckAnalysisRequest,
): Promise<BottleneckAnalysisResult> {
  return apiPost<BottleneckAnalysisResult>('/performance/bottleneck', payload)
}
