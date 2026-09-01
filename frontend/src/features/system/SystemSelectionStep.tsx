import { useState } from 'react'
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
import type { SystemSnapshot } from '../../types/compatibility'
import type { HardwareSnapshot } from '../../types/detection'
import type { GraphicsQuality, Resolution, WorkloadType } from '../../types/performance'
import type { UpgradeProfile } from '../../types/recommendation'
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
  const [profile, setProfile] = useState<UpgradeProfile>('CUSTO_BENEFICIO')
  const [resolution, setResolution] = useState<Resolution>('1080P')
  const [graphicsQuality, setGraphicsQuality] = useState<GraphicsQuality>('HIGH')
  const [targetFps, setTargetFps] = useState('')
  const [workloadType, setWorkloadType] = useState<WorkloadType>('GAMING')

  function updateSystem(key: keyof SystemSnapshot, value: string | null) {
    setSystem((prev) => ({ ...prev, [key]: value }))
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
          A detecção automática não identifica o modelo exato de RAM, armazenamento, fonte,
          gabinete e cooler — selecione o mais próximo do catálogo para cada componente que
          quiser incluir na análise. Deixe em branco o que não se aplica.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <CatalogSelect
            label="Processador (CPU)"
            queryKey="catalog-cpus"
            fetcher={fetchCpus}
            value={system.cpu_model_name ?? null}
            onChange={(v) => updateSystem('cpu_model_name', v)}
            hint={detected.cpu_model_name}
          />
          <CatalogSelect
            label="Placa de vídeo (GPU)"
            queryKey="catalog-gpus"
            fetcher={fetchGpus}
            value={system.gpu_model_name ?? null}
            onChange={(v) => updateSystem('gpu_model_name', v)}
            hint={detected.gpu_model_name}
          />
          <CatalogSelect
            label="Placa-mãe"
            queryKey="catalog-motherboards"
            fetcher={fetchMotherboards}
            value={system.motherboard_model_name ?? null}
            onChange={(v) => updateSystem('motherboard_model_name', v)}
            hint={detected.motherboard_model_name}
          />
          <CatalogSelect
            label="Kit de memória RAM"
            queryKey="catalog-ram"
            fetcher={fetchRamKits}
            value={system.ram_model_name ?? null}
            onChange={(v) => updateSystem('ram_model_name', v)}
            hint={ramHint(detected)}
          />
          <CatalogSelect
            label="Armazenamento"
            queryKey="catalog-storage"
            fetcher={fetchStorage}
            value={system.storage_model_name ?? null}
            onChange={(v) => updateSystem('storage_model_name', v)}
            hint={detected.storage_devices[0]?.model_name ?? null}
          />
          <CatalogSelect
            label="Fonte de alimentação (PSU)"
            queryKey="catalog-psus"
            fetcher={fetchPsus}
            value={system.psu_model_name ?? null}
            onChange={(v) => updateSystem('psu_model_name', v)}
            hint={
              detected.psu_model_name ??
              (detected.psu_wattage ? `${detected.psu_wattage}W` : null)
            }
          />
          <CatalogSelect
            label="Gabinete"
            queryKey="catalog-cases"
            fetcher={fetchCases}
            value={system.case_model_name ?? null}
            onChange={(v) => updateSystem('case_model_name', v)}
          />
          <CatalogSelect
            label="Cooler"
            queryKey="catalog-coolers"
            fetcher={fetchCoolers}
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
