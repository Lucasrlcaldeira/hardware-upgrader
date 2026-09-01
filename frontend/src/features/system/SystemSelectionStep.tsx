import { useQuery } from '@tanstack/react-query'
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
 * vez por campo (o ref evita reaplicar o auto-match depois que o usuário mexe no valor), e
 * só se o usuário ainda não tiver tocado nesse campo.
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
          Confirme os componentes no catálogo
        </h2>
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          Quando a detecção bate com um item do catálogo, já selecionamos automaticamente. Nos
          demais casos (nenhum modelo exato encontrado, ou componentes que a detecção não
          identifica, como RAM/armazenamento/fonte/gabinete/cooler), escolha o mais próximo —
          ou deixe em branco o que não se aplica.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <CatalogSelect
            label="Processador (CPU)"
            options={cpuQuery.data}
            status={cpuQuery.status}
            value={system.cpu_model_name ?? null}
            onChange={(v) => updateSystem('cpu_model_name', v)}
            hint={detected.cpu_model_name}
            autoMatched={autoMatched.cpu_model_name}
          />
          <CatalogSelect
            label="Placa de vídeo (GPU)"
            options={gpuQuery.data}
            status={gpuQuery.status}
            value={system.gpu_model_name ?? null}
            onChange={(v) => updateSystem('gpu_model_name', v)}
            hint={detected.gpu_model_name}
            autoMatched={autoMatched.gpu_model_name}
          />
          <CatalogSelect
            label="Placa-mãe"
            options={motherboardQuery.data}
            status={motherboardQuery.status}
            value={system.motherboard_model_name ?? null}
            onChange={(v) => updateSystem('motherboard_model_name', v)}
            hint={detected.motherboard_model_name}
            autoMatched={autoMatched.motherboard_model_name}
          />
          <CatalogSelect
            label="Kit de memória RAM"
            options={ramQuery.data}
            status={ramQuery.status}
            value={system.ram_model_name ?? null}
            onChange={(v) => updateSystem('ram_model_name', v)}
            hint={ramHint(detected)}
          />
          <CatalogSelect
            label="Armazenamento"
            options={storageQuery.data}
            status={storageQuery.status}
            value={system.storage_model_name ?? null}
            onChange={(v) => updateSystem('storage_model_name', v)}
            hint={detected.storage_devices[0]?.model_name ?? null}
            autoMatched={autoMatched.storage_model_name}
          />
          <CatalogSelect
            label="Fonte de alimentação (PSU)"
            options={psuQuery.data}
            status={psuQuery.status}
            value={system.psu_model_name ?? null}
            onChange={(v) => updateSystem('psu_model_name', v)}
            hint={
              detected.psu_model_name ??
              (detected.psu_wattage ? `${detected.psu_wattage}W` : null)
            }
            autoMatched={autoMatched.psu_model_name}
          />
          <CatalogSelect
            label="Gabinete"
            options={caseQuery.data}
            status={caseQuery.status}
            value={system.case_model_name ?? null}
            onChange={(v) => updateSystem('case_model_name', v)}
          />
          <CatalogSelect
            label="Cooler"
            options={coolerQuery.data}
            status={coolerQuery.status}
            value={system.cooler_model_name ?? null}
            onChange={(v) => updateSystem('cooler_model_name', v)}
          />
        </div>
      </Card>

      <Card>
        <h2 className="mb-3 font-medium text-slate-900 dark:text-slate-100">Cenário de uso</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="text-sm text-slate-500 dark:text-slate-400">Tipo de carga</span>
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
            <span className="text-sm text-slate-500 dark:text-slate-400">FPS alvo (opcional)</span>
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
        <h2 className="mb-3 font-medium text-slate-900 dark:text-slate-100">Perfil de upgrade</h2>
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
          Selecione ao menos um componente para analisar.
        </p>
      )}
    </div>
  )
}
