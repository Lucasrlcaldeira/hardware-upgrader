export type DetectionSource = 'DETECTED' | 'MANUAL_REQUIRED' | 'MANUAL_PROVIDED'

export interface StorageDeviceInfo {
  storage_type: string | null
  capacity_gb: number | null
  model_name: string | null
}

export interface HardwareSnapshot {
  cpu_model_name: string | null
  gpu_model_name: string | null
  motherboard_model_name: string | null
  ram_capacity_gb: number | null
  ram_speed_mhz: number | null
  ram_modules: number | null
  storage_devices: StorageDeviceInfo[]
  psu_model_name: string | null
  psu_wattage: number | null
  os_name: string | null
  os_version: string | null
  monitor_resolution: string | null
  monitor_refresh_hz: number | null
}

export interface DetectionResult {
  snapshot: HardwareSnapshot
  field_status: Record<keyof HardwareSnapshot, DetectionSource>
}
