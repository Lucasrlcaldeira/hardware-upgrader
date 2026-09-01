import { apiPost } from './client'
import type { CompatibilityCheckResponse, SystemSnapshot } from '../types/compatibility'

export function checkCompatibility(system: SystemSnapshot): Promise<CompatibilityCheckResponse> {
  return apiPost<CompatibilityCheckResponse>('/compatibility/check', system)
}
