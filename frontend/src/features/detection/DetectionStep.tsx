import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { fetchDetectionRun } from '../../api/detection'
import { Card } from '../../components/ui/Card'
import { StatusPill } from '../../components/ui/StatusPill'
import type { HardwareSnapshot } from '../../types/detection'
import { SCALAR_FIELD_LABELS, SCALAR_FIELD_ORDER } from './fieldLabels'

const NUMERIC_FIELDS = new Set<keyof HardwareSnapshot>([
  'ram_capacity_gb',
  'ram_speed_mhz',
  'ram_modules',
  'monitor_refresh_hz',
])

export function DetectionStep({
  onContinue,
}: {
  onContinue: (snapshot: HardwareSnapshot) => void
}) {
  const { data, status, error, refetch } = useQuery({
    queryKey: ['detection-run'],
    queryFn: fetchDetectionRun,
  })

  const [manualValues, setManualValues] = useState<Record<string, string>>({})
  const [manualStorageText, setManualStorageText] = useState('')

  const missingRequired = useMemo(() => {
    if (!data) return []
    return SCALAR_FIELD_ORDER.filter(
      (field) => data.field_status[field] === 'MANUAL_REQUIRED' && !manualValues[field]?.trim(),
    )
  }, [data, manualValues])

  const storageMissing =
    data?.field_status.storage_devices === 'MANUAL_REQUIRED' && !manualStorageText.trim()

  if (status === 'pending') {
    return <Card>Dando uma olhada nas peças do seu PC…</Card>
  }

  if (status === 'error') {
    return (
      <Card>
        <p className="mb-3 text-red-700 dark:text-red-400">
          Não conseguimos ver o hardware do seu PC: {(error as Error).message}
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="rounded-md bg-slate-800 px-4 py-2 text-white hover:bg-slate-700"
        >
          Tentar de novo
        </button>
      </Card>
    )
  }

  const snapshot = data.snapshot
  const fieldStatus = data.field_status

  function handleContinue() {
    const merged: HardwareSnapshot = { ...snapshot }
    for (const field of SCALAR_FIELD_ORDER) {
      if (fieldStatus[field] === 'MANUAL_REQUIRED') {
        const raw = manualValues[field]?.trim()
        if (!raw) continue
        ;(merged as unknown as Record<string, unknown>)[field] = NUMERIC_FIELDS.has(field)
          ? Number(raw)
          : raw
      }
    }
    if (fieldStatus.storage_devices === 'MANUAL_REQUIRED' && manualStorageText.trim()) {
      merged.storage_devices = [
        { storage_type: null, capacity_gb: null, model_name: manualStorageText.trim() },
      ]
    }
    onContinue(merged)
  }

  return (
    <div className="space-y-3">
      {SCALAR_FIELD_ORDER.map((field) => {
        const status = fieldStatus[field]
        const detectedValue = snapshot[field]
        return (
          <Card key={field} className="flex items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {SCALAR_FIELD_LABELS[field]}
              </p>
              {status === 'DETECTED' ? (
                <p className="truncate font-medium text-slate-900 dark:text-slate-100">
                  {String(detectedValue)}
                </p>
              ) : (
                <input
                  type="text"
                  value={manualValues[field] ?? ''}
                  onChange={(e) =>
                    setManualValues((prev) => ({ ...prev, [field]: e.target.value }))
                  }
                  placeholder="Informe manualmente"
                  className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
                />
              )}
            </div>
            <StatusPill status={status} />
          </Card>
        )
      })}

      <Card className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-sm text-slate-500 dark:text-slate-400">Armazenamento</p>
          {fieldStatus.storage_devices === 'DETECTED' ? (
            <ul className="mt-1 space-y-1">
              {snapshot.storage_devices.map((device, i) => (
                <li key={i} className="font-medium text-slate-900 dark:text-slate-100">
                  {device.model_name ?? 'Dispositivo'}
                  {device.capacity_gb ? ` — ${device.capacity_gb} GB` : ''}
                </li>
              ))}
            </ul>
          ) : (
            <input
              type="text"
              value={manualStorageText}
              onChange={(e) => setManualStorageText(e.target.value)}
              placeholder="Ex: SSD 480GB"
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-600 dark:bg-slate-800"
            />
          )}
        </div>
        <StatusPill status={fieldStatus.storage_devices} />
      </Card>

      <button
        type="button"
        disabled={missingRequired.length > 0 || storageMissing}
        onClick={handleContinue}
        className="w-full rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300 dark:disabled:bg-slate-700"
      >
        Continuar
      </button>
    </div>
  )
}
