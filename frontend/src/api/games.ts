import { apiGet, apiPost } from './client'
import type {
  GameRequirementsCheckRequest,
  GameRequirementsCheckResult,
  SteamGameSummary,
} from '../types/games'

export function searchSteamGames(term: string): Promise<SteamGameSummary[]> {
  return apiGet<SteamGameSummary[]>(`/games/search?q=${encodeURIComponent(term)}`)
}

export function checkGameRequirements(
  payload: GameRequirementsCheckRequest,
): Promise<GameRequirementsCheckResult> {
  return apiPost<GameRequirementsCheckResult>('/games/requirements-check', payload)
}
