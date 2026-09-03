import type { HardwareSnapshot } from '../../types/detection'

export const SCALAR_FIELD_LABELS: Partial<Record<keyof HardwareSnapshot, string>> = {
  cpu_model_name: 'Processador (CPU)',
  gpu_model_name: 'Placa de vídeo (GPU)',
  motherboard_model_name: 'Placa-mãe',
  ram_capacity_gb: 'RAM total (GB)',
  ram_speed_mhz: 'Velocidade da RAM (MHz)',
  ram_modules: 'Número de módulos de RAM',
  os_name: 'Sistema operacional',
  os_version: 'Versão do SO',
  monitor_resolution: 'Resolução do monitor',
  monitor_refresh_hz: 'Taxa de atualização do monitor (Hz)',
}

export const SCALAR_FIELD_ORDER = Object.keys(SCALAR_FIELD_LABELS) as (keyof HardwareSnapshot)[]
