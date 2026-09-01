import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactElement } from 'react'
import { describe, expect, it, vi } from 'vitest'
import * as detectionApi from '../../api/detection'
import type { DetectionResult } from '../../types/detection'
import { DetectionStep } from './DetectionStep'

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient()
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const baseSnapshot: DetectionResult['snapshot'] = {
  cpu_model_name: 'AMD Ryzen 5 1600',
  gpu_model_name: null,
  motherboard_model_name: 'ASRock A320M-DGS',
  ram_capacity_gb: 32,
  ram_speed_mhz: 2400,
  ram_modules: 2,
  storage_devices: [],
  psu_model_name: null,
  psu_wattage: null,
  os_name: 'Windows',
  os_version: '10',
  monitor_resolution: '2560x1080',
  monitor_refresh_hz: 60,
}

const baseResult: DetectionResult = {
  snapshot: baseSnapshot,
  field_status: {
    cpu_model_name: 'DETECTED',
    gpu_model_name: 'MANUAL_REQUIRED',
    motherboard_model_name: 'DETECTED',
    ram_capacity_gb: 'DETECTED',
    ram_speed_mhz: 'DETECTED',
    ram_modules: 'DETECTED',
    storage_devices: 'MANUAL_REQUIRED',
    psu_model_name: 'MANUAL_REQUIRED',
    psu_wattage: 'MANUAL_REQUIRED',
    os_name: 'DETECTED',
    os_version: 'DETECTED',
    monitor_resolution: 'DETECTED',
    monitor_refresh_hz: 'DETECTED',
  },
}

describe('DetectionStep', () => {
  it('shows detected values and blocks continue until manual fields are filled', async () => {
    vi.spyOn(detectionApi, 'fetchDetectionRun').mockResolvedValue(baseResult)
    const onContinue = vi.fn()
    const user = userEvent.setup()

    renderWithClient(<DetectionStep onContinue={onContinue} />)

    expect(await screen.findByText('AMD Ryzen 5 1600')).toBeInTheDocument()

    const continueButton = screen.getByRole('button', { name: 'Continuar' })
    expect(continueButton).toBeDisabled()

    const manualInputs = screen.getAllByPlaceholderText('Informe manualmente')
    for (const input of manualInputs) {
      await user.type(input, 'valor de teste')
    }
    await user.type(screen.getByPlaceholderText('Ex: SSD 480GB'), 'SSD 480GB')

    await waitFor(() => expect(continueButton).not.toBeDisabled())
    await user.click(continueButton)

    expect(onContinue).toHaveBeenCalledTimes(1)
    const merged = onContinue.mock.calls[0][0]
    expect(merged.gpu_model_name).toBe('valor de teste')
    expect(merged.storage_devices[0].model_name).toBe('SSD 480GB')
  })
})
