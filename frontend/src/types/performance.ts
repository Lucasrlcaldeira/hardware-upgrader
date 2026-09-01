export type Resolution = '1080P' | '1440P' | '4K'
export type GraphicsQuality = 'LOW' | 'MEDIUM' | 'HIGH' | 'ULTRA'
export type WorkloadType = 'GAMING' | 'CONTENT_CREATION' | 'PRODUCTIVITY' | 'GENERAL'
export type BottleneckVerdict = 'CPU_BOUND' | 'GPU_BOUND' | 'BALANCED' | 'INSUFFICIENT_DATA'
export type ConfidenceLevel = 'BAIXA' | 'MEDIA' | 'ALTA'

export interface BottleneckAnalysisRequest {
  cpu_model_name: string
  gpu_model_name: string
  resolution: Resolution
  graphics_quality: GraphicsQuality
  target_fps?: number | null
  workload_type: WorkloadType
}

export interface BottleneckAnalysisResult {
  verdict: BottleneckVerdict
  limiting_component: string | null
  explanation: string
  contributing_factors: string[]
  confidence: ConfidenceLevel
}
