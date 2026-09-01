import { apiPost } from './client'
import type { RecommendationRequest, RecommendationResponse } from '../types/recommendation'

export function generateRecommendations(
  payload: RecommendationRequest,
): Promise<RecommendationResponse> {
  return apiPost<RecommendationResponse>('/recommendation/generate', payload)
}
