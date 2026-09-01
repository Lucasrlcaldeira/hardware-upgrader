import type { Resolution } from './performance'

export interface GameFpsRequest {
  game_title: string
  gpu_model_name: string
  cpu_model_name?: string | null
  resolution: Resolution
}

export interface GameFpsResult {
  game_title: string
  gpu_model_name: string
  resolution: Resolution
  avg_fps: number
  test_cpu_model: string
  source_name: string
  source_url: string
  quality_preset_note: string
  cpu_bottleneck_caveat: string | null
}
