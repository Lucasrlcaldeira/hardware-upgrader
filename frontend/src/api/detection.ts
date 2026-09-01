import { apiGet } from './client'
import type { DetectionResult } from '../types/detection'

export function fetchDetectionRun(): Promise<DetectionResult> {
  return apiGet<DetectionResult>('/detection/run')
}
