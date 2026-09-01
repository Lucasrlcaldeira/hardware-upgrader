import { apiGet, apiPost } from './client'
import type { GameFpsRequest, GameFpsResult } from '../types/games'

export function fetchGameTitles(): Promise<string[]> {
  return apiGet<string[]>('/games/')
}

export function fetchFpsEstimate(payload: GameFpsRequest): Promise<GameFpsResult> {
  return apiPost<GameFpsResult>('/games/fps-estimate', payload)
}
