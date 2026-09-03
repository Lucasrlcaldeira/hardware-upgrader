import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import {
  fetchCases,
  fetchCoolers,
  fetchCpus,
  fetchGpus,
  fetchMotherboards,
  fetchPsus,
  fetchRamKits,
  fetchStorage,
} from '../../api/catalog'
import { Card } from '../../components/ui/Card'
import type { CatalogOption } from '../../types/catalog'
import type { SystemSnapshot } from '../../types/compatibility'
import type { HardwareSnapshot } from '../../types/detection'
import type { GraphicsQuality, Resolution, WorkloadType } from '../../types/performance'
import type { UpgradeProfile } from '../../types/recommendation'
import { findCatalogAutoMatch } from './autoMatch'
import { CatalogSelect } from './CatalogSelect'
import { ConfirmedComponentRow } from './ConfirmedComponentRow'
import {
  GRAPHICS_QUALITY_LABELS,
  PROFILE_DESCRIPTIONS,
  PROFILE_LABELS,
  RESOLUTION_LABELS,
  WORKLOAD_TYPE_LABELS,
} from '../results/labels'

export interface AnalysisConfig {
  system: SystemSnapshot
  profile: UpgradeProfile
  resolution: Resolution | null
  graphics_quality: GraphicsQuality | null
  target_fps: number | null
  workload_type: WorkloadType
}

const PROFILES: UpgradeProfile[] = [
  'ECONOMICO',
  'CUSTO_BENEFICIO',
  'ALTO_DESEMPENHO',
  'UPGRADE_COMPLETO',
]
const RESOLUTIONS: Resolution[] = ['1080P', '1440P', '4K']
const QUALITIES: GraphicsQuality[] = ['LOW', 'MEDIUM', 'HIGH', 'ULTRA']
const WORKLOADS: WorkloadType[] = ['GAMING', 'CONTENT_CREATION', 'PRODUCTIVITY', 'GENERAL']

function ramHint(detected: HardwareSnapshot): string | null {
  if (!detected.ram_capacity_gb) return null
  const parts = [`${detected.ram_capacity_gb}GB`]
  if (detected.ram_speed_mhz) parts.push(`@ ${detected.ram_speed_mhz}MHz`)
  if (detected.ram_modules) parts.push(`(${detected.ram_modules} módulos)`)
  return parts.join(' ')
}

/**
 * Tenta casar automaticamente um campo com o catálogo assim que a lista carrega — só uma
 * vez por campo (o ref evita reaplicar depois que o usuário mexe no valor).
 */
function useAutoMatch(
  key: keyof SystemSnapshot,
  detectedValue: string | null | undefined,
  options: CatalogOption[] | undefined,
  setSystem: React.Dispatch<React.SetStateAction<SystemSnapshot>>,
  setAutoMatched: React.Dispatch<React.SetStateAction<Partial<Record<keyof SystemSnapshot, boolean>>>>,
) {
  const attempted = useRef(false)
  useEffect(() => {
    if (attempted.current || !options) return
    attempted.current = true
    const match = findCatalogAutoMatch(detectedValue, options)
    if (match) {
      setSystem((prev) => ({ ...prev, [key]: match.model_name }))
      setAutoMatched((prev) => ({ ...prev, [key]: true }))
    }
  }, [options, detectedValue, key, setSystem, setAutoMatched])
}

interface FieldConfig {
  key: keyof SystemSnapshot
  label: string
  query: UseQueryResult<CatalogOption[]>
  hint: string | null
  autoMatchable: boolean
}

export function SystemSelectionStep({
  detected,
  onAnalyze,
  isSubmitting,
}: {
  detected: HardwareSnapshot
  onAnalyze: (config: AnalysisConfig) => void
  isSubmitting: boolean
}) {
  const [system, setSystem] = useState<SystemSnapshot>({})
  const [autoMatched, setAutoMatched] = useState<Partial<Record<keyof SystemSnapshot, boolean>>>({})
  const [profile, setProfile] = useState<UpgradeProfile>('CUSTO_BENEFICIO')
  const [resolution, setResolution] = useState<Resolution>('1080P')
  const [graphicsQuality, setGraphicsQuality] = useState<GraphicsQuality>('HIGH')
  const [targetFps, setTargetFps] = useState('')
  const [workloadType, setWorkloadType] = useState<WorkloadType>('GAMING')

  const cpuQuery = useQuery({ queryKey: ['catalog-cpus'], queryFn: fetchCpus })
  const gpuQuery = useQuery({ queryKey: ['catalog-gpus'], queryFn: fetchGpus })
  const motherboardQuery = useQuery({ queryKey: ['catalog-motherboards'], queryFn: fetchMotherboards })
  const ramQuery = useQuery({ queryKey: ['catalog-ram'], queryFn: fetchRamKits })
  const storageQuery = useQuery({ queryKey: ['catalog-storage'], queryFn: fetchStorage })
  const psuQuery = useQuery({ queryKey: ['catalog-psus'], queryFn: fetchPsus })
  const caseQuery = useQuery({ queryKey: ['catalog-cases'], queryFn: fetchCases })
  const coolerQuery = useQuery({ queryKey: ['catalog-coolers'], queryFn: fetchCoolers })

  // RAM/gabinete/cooler nunca chegam da detecção como um "modelo" comparável ao catálogo
  // (RAM vem como capacidade/frequência crua; gabinete e cooler não são detectados) — só
  // tentamos auto-match nos campos onde a detecção de fato devolve uma string de modelo.
  useAutoMatch('cpu_model_name', detected.cpu_model_name, cpuQuery.data, setSystem, setAutoMatched)
  useAutoMatch('gpu_model_name', detected.gpu_model_name, gpuQuery.data, setSystem, setAutoMatched)
  useAutoMatch(
    'motherboard_model_name',
    detected.motherboard_model_name,
    motherboardQuery.data,
    setSystem,
    setAutoMatched,
  )
  useAutoMatch(
    'storage_model_name',
    detected.storage_devices[0]?.model_name,
    storageQuery.data,
    setSystem,
    setAutoMatched,
  )
  useAutoMatch('psu_model_name', detected.psu_model_name, psuQuery.data, setSystem, setAutoMatched)

  function updateSystem(key: keyof SystemSnapshot, value: string | null) {
    setSystem((prev) => ({ ...prev, [key]: value }))
    setAutoMatched((prev) => ({ ...prev, [key]: false }))
  }

  function requestEdit(key: keyof SystemSnapshot) {
    setAutoMatched((prev) => ({ ...prev, [key]: false }))
  }

  const fields: FieldConfig[] = [
    {
      key: 'cpu_model_name',
      label: 'Processador (CPU)',
      query: cpuQuery,
      hint: detected.cpu_model_name,
      autoMatchable: true,
    },
    {
      key: 'gpu_model_name',
      label: 'Placa de vídeo (GPU)',
      query: gpuQuery,
      hint: detected.gpu_model_name,
      autoMatchable: true,
    },
    {
      key: 'motherboard_model_name',
      label: 'Placa-mãe',
      query: motherboardQuery,
      hint: detected.motherboard_model_name,
      autoMatchable: true,
    },
    {
      key: 'ram_model_name',
      label: 'Kit de memória RAM',
      query: ramQuery,
      hint: ramHint(detected),
      autoMatchable: false,
    },
    {
      key: 'storage_model_name',
      label: 'Armazenamento',
      query: storageQuery,
      hint: detected.storage_devices[0]?.model_name ?? null,
      autoMatchable: true,
    },
    {
      key: 'psu_model_name',
      label: 'Fonte de alimentação (PSU)',
      query: psuQuery,
      hint: detected.psu_model_name ?? (detected.psu_wattage ? `${detected.psu_wattage}W` : null),
      autoMatchable: true,
    },
    { key: 'case_model_name', label: 'Gabinete', query: caseQuery, hint: null, autoMatchable: false },
    { key: 'cooler_model_name', label: 'Cooler', query: coolerQuery, hint: null, autoMatchable: false },
  ]

  const isConfirmed = (f: FieldConfig) => f.autoMatchable && autoMatched[f.key] && system[f.key]
  const confirmedFields = fields.filter(isConfirmed)
  const pendingFields = fields.filter((f) => !isConfirmed(f))

  const hasAnyComponent = Object.values(system).some((v) => v)

  function handleSubmit() {
    onAnalyze({
      system,
      profile,
      resolution,
      graphics_quality: graphicsQuality,
      target_fps: targetFps.trim() ? Number(targetFps) : null,
      workload_type: workloadType,
    })
  }

  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-3 font-medium text-slate-900 dark:text-slate-100">
          Confirme suas peças
        </h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          O que já conseguimos identificar sozinhos já vem preenchido aí embaixo — você só
          precisa escolher o que sobrou (ou deixar em branco o que não tiver).
        </p>

        {confirmedFields.length > 0 && (
          <div className="mb-4 space-y-2">
            <p className="text-xs font-medium text-emerald-700 dark:text-emerald-400">
              A gente já identificou essas sozinho
            </p>
            {confirmedFields.map((f) => (
              <ConfirmedComponentRow
                key={f.key}
                label={f.label}
                value={system[f.key] as string}
                onEdit={() => requestEdit(f.key)}
              />
            ))}
          </div>
        )}

        {pendingFields.length > 0 && (
          <>
            {confirmedFields.length > 0 && (
              <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                Escolha o resto das peças
              </p>
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              {pendingFields.map((f) => (
                <CatalogSelect
                  key={f.key}
                  label={f.label}
                  options={f.query.data}
                  status={f.query.status}
                  value={(system[f.key] as string | null | undefined) ?? null}
                  onChange={(v) => updateSystem(f.key, v)}
                  hint={f.hint}
                />
              ))}
            </div>
          </>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 font-medium text-slate-900 dark:text-slate-100">Como você usa o PC</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm text-slate-500 dark:text-slate-400">Pra que mais você usa</span>
            <select
              value={workloadType}
              onChange={(e) => setWorkloadType(e.target.value as WorkloadType)}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
            >
              {WORKLOADS.map((w) => (
                <option key={w} value={w}>
                  {WORKLOAD_TYPE_LABELS[w]}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm text-slate-500 dark:text-slate-400">Resolução</span>
            <select
              value={resolution}
              onChange={(e) => setResolution(e.target.value as Resolution)}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
            >
              {RESOLUTIONS.map((r) => (
                <option key={r} value={r}>
                  {RESOLUTION_LABELS[r]}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm text-slate-500 dark:text-slate-400">Qualidade gráfica</span>
            <select
              value={graphicsQuality}
              onChange={(e) => setGraphicsQuality(e.target.value as GraphicsQuality)}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
            >
              {QUALITIES.map((q) => (
                <option key={q} value={q}>
                  {GRAPHICS_QUALITY_LABELS[q]}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-sm text-slate-500 dark:text-slate-400">
              FPS que você quer alcançar (se souber)
            </span>
            <input
              type="number"
              min={1}
              value={targetFps}
              onChange={(e) => setTargetFps(e.target.value)}
              placeholder="Ex: 144"
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
            />
          </label>
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-medium text-slate-900 dark:text-slate-100">Qual seu estilo de upgrade</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {PROFILES.map((p) => (
            <label
              key={p}
              className={`flex cursor-pointer flex-col gap-1 rounded-md border p-3 text-sm ${
                profile === p
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/40'
                  : 'border-slate-200 dark:border-slate-700'
              }`}
            >
              <span className="flex items-center gap-2 font-medium text-slate-900 dark:text-slate-100">
                <input type="radio" name="profile" checked={profile === p} onChange={() => setProfile(p)} />
                {PROFILE_LABELS[p]}
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {PROFILE_DESCRIPTIONS[p]}
              </span>
            </label>
          ))}
        </div>
      </Card>

      <button
        type="button"
        disabled={!hasAnyComponent || isSubmitting}
        onClick={handleSubmit}
        className="w-full rounded-md bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300 dark:disabled:bg-slate-700"
      >
        {isSubmitting ? 'Analisando…' : 'Analisar'}
      </button>
      {!hasAnyComponent && (
        <p className="text-center text-xs text-slate-400 dark:text-slate-500">
          Escolha pelo menos uma peça antes de analisar.
        </p>
      )}
    </div>
  )
}
