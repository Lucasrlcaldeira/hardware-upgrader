import { useMutation, useQuery, type UseMutationResult } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { ApiError } from '../../api/client'
import { fetchFpsEstimate, fetchGameTitles } from '../../api/games'
import { Card } from '../../components/ui/Card'
import type { SystemSnapshot } from '../../types/compatibility'
import type { GameFpsResult } from '../../types/games'
import type { Resolution } from '../../types/performance'
import type { ComponentRecommendation, ComponentSlot } from '../../types/recommendation'
import { RESOLUTION_LABELS } from './labels'

const RESOLUTIONS: Resolution[] = ['1080P', '1440P', '4K']

const UPGRADE_TOGGLES: { slot: ComponentSlot; label: string }[] = [
  { slot: 'cpu', label: 'Processador (CPU)' },
  { slot: 'ram', label: 'Memória RAM' },
  { slot: 'gpu', label: 'Placa de vídeo (GPU)' },
]

function UpgradeToggle({
  label,
  rec,
  checked,
  onChange,
}: {
  label: string
  rec: ComponentRecommendation | undefined
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <label
      className={`flex items-start gap-2 rounded-md border px-3 py-2 text-sm ${
        rec
          ? 'cursor-pointer border-slate-200 dark:border-slate-700'
          : 'cursor-not-allowed border-slate-100 opacity-60 dark:border-slate-800'
      }`}
    >
      <input
        type="checkbox"
        checked={rec ? checked : false}
        disabled={!rec}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5"
      />
      <span>
        <span className="block font-medium text-slate-900 dark:text-slate-100">{label}</span>
        <span className="block text-xs text-slate-500 dark:text-slate-400">
          {rec ? `${rec.current_model_name ?? '—'} → ${rec.recommended_model_name}` : 'Sem upgrade recomendado'}
        </span>
      </span>
    </label>
  )
}

function FpsColumn({
  title,
  gpuModelName,
  mutation,
}: {
  title: string
  gpuModelName: string | null | undefined
  mutation: UseMutationResult<GameFpsResult, ApiError, void>
}) {
  return (
    <div>
      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{title}</p>
      <p className="mb-2 truncate text-sm text-slate-600 dark:text-slate-300">
        {gpuModelName ?? 'GPU não informada'}
      </p>

      {!gpuModelName && (
        <p className="text-sm text-slate-400 dark:text-slate-500">
          Sem GPU informada para calcular.
        </p>
      )}
      {gpuModelName && mutation.isPending && (
        <p className="text-sm text-slate-500 dark:text-slate-400">Buscando…</p>
      )}
      {gpuModelName && mutation.isError && (
        <p className="text-sm text-amber-700 dark:text-amber-400">{mutation.error.message}</p>
      )}
      {gpuModelName && mutation.isSuccess && (
        <div>
          <p
            className={`text-3xl font-semibold ${
              mutation.data.cpu_bottleneck_caveat
                ? 'text-amber-700 dark:text-amber-400'
                : 'text-slate-900 dark:text-slate-100'
            }`}
          >
            {mutation.data.cpu_bottleneck_caveat && (
              <span className="text-lg font-normal">até </span>
            )}
            {mutation.data.avg_fps} <span className="text-base font-normal">FPS</span>
          </p>
          {mutation.data.cpu_bottleneck_caveat && (
            <p className="mt-1 text-xs font-medium text-amber-700 dark:text-amber-400">
              {mutation.data.cpu_bottleneck_caveat} O número acima é o teto da GPU, não uma
              previsão para o seu processador atual.
            </p>
          )}
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Medido com {mutation.data.test_cpu_model} — fonte:{' '}
            <a
              href={mutation.data.source_url}
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-slate-700 dark:hover:text-slate-200"
            >
              {mutation.data.source_name}
            </a>
          </p>
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">
            {mutation.data.quality_preset_note}
          </p>
          {mutation.data.approximation_note && (
            <p className="mt-2 text-xs text-sky-700 dark:text-sky-400">
              {mutation.data.approximation_note}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export function GameFpsExplorer({
  system,
  recommendations,
}: {
  system: SystemSnapshot
  recommendations: ComponentRecommendation[]
}) {
  const cpuRec = recommendations.find((r) => r.slot === 'cpu')
  const ramRec = recommendations.find((r) => r.slot === 'ram')
  const gpuRec = recommendations.find((r) => r.slot === 'gpu')

  // Por padrão, "PC futuro" aplica todo upgrade recomendado disponível — o usuário desmarca
  // o que não quiser incluir na comparação (ex: só trocar a GPU, mantendo CPU e RAM atuais).
  const [applyCpu, setApplyCpu] = useState(true)
  const [applyRam, setApplyRam] = useState(true)
  const [applyGpu, setApplyGpu] = useState(true)

  const [gameTitle, setGameTitle] = useState('')
  const [resolution, setResolution] = useState<Resolution>('1080P')
  const [noGpuWarning, setNoGpuWarning] = useState(false)

  const gamesQuery = useQuery({ queryKey: ['games-list'], queryFn: fetchGameTitles })

  const currentGpu = system.gpu_model_name
  const currentCpu = system.cpu_model_name
  const futureGpu = applyGpu && gpuRec ? gpuRec.recommended_model_name : currentGpu
  const futureCpu = applyCpu && cpuRec ? cpuRec.recommended_model_name : currentCpu
  const futureRamApplied = applyRam && Boolean(ramRec)

  const currentMutation = useMutation<GameFpsResult, ApiError, void>({
    mutationFn: () =>
      fetchFpsEstimate({
        game_title: gameTitle,
        gpu_model_name: currentGpu as string,
        cpu_model_name: currentCpu,
        resolution,
      }),
  })
  const futureMutation = useMutation<GameFpsResult, ApiError, void>({
    mutationFn: () =>
      fetchFpsEstimate({
        game_title: gameTitle,
        gpu_model_name: futureGpu as string,
        cpu_model_name: futureCpu,
        resolution,
      }),
  })

  // Se o usuário mexer nos toggles depois de já ver um resultado, o FPS "futuro" mostrado
  // ficaria descasado do que os toggles agora descrevem — limpa o resultado anterior para
  // forçar uma nova consulta em vez de mostrar um número que não corresponde mais à seleção.
  // `futureMutation` de propósito fora das deps: sua identidade muda a cada render do
  // react-query, então incluí-la faria isto rodar em todo render em vez de só quando o
  // sistema "futuro" realmente muda.
  useEffect(() => {
    futureMutation.reset()
  }, [futureGpu, futureCpu])

  function handleSubmit() {
    if (!gameTitle.trim()) return
    if (!currentGpu) {
      // Sem GPU selecionada na etapa anterior não há nada pra consultar — sem este aviso,
      // o clique não dispara nenhuma mutation e a tela simplesmente não muda, sem explicar o motivo.
      setNoGpuWarning(true)
      return
    }
    setNoGpuWarning(false)
    currentMutation.mutate()
    if (futureGpu) futureMutation.mutate()
  }

  return (
    <Card>
      <h2 className="mb-1 font-medium text-slate-900 dark:text-slate-100">FPS por jogo</h2>
      <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
        Baseado em benchmarks reais publicados — só para os jogos e GPUs com dado cadastrado.
        Sem dado real para a combinação digitada, avisamos em vez de estimar um número.
      </p>

      <p className="mb-2 text-xs font-medium text-slate-500 dark:text-slate-400">
        O que muda no "PC futuro"?
      </p>
      <div className="mb-4 grid gap-2 sm:grid-cols-3">
        {UPGRADE_TOGGLES.map(({ slot, label }) => {
          const rec = slot === 'cpu' ? cpuRec : slot === 'ram' ? ramRec : gpuRec
          const checked = slot === 'cpu' ? applyCpu : slot === 'ram' ? applyRam : applyGpu
          const setChecked = slot === 'cpu' ? setApplyCpu : slot === 'ram' ? setApplyRam : setApplyGpu
          return (
            <UpgradeToggle key={slot} label={label} rec={rec} checked={checked} onChange={setChecked} />
          )
        })}
      </div>
      <p className="mb-4 text-xs text-slate-400 dark:text-slate-500">
        O número de FPS abaixo vem de um benchmark real medido por GPU — só a troca de GPU no
        "PC futuro" muda esse valor. Não existe dado real cruzando FPS com CPU ou RAM
        específicas neste projeto, então trocar só o processador{futureRamApplied ? ' ou a RAM' : ''}
        {' '}não altera o número mostrado; a troca de CPU pode, no máximo, acionar o aviso de
        possível gargalo logo abaixo dele.
      </p>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <label className="min-w-48 flex-1">
          <span className="text-sm text-slate-500 dark:text-slate-400">Jogo</span>
          <input
            list="game-fps-titles"
            type="text"
            value={gameTitle}
            onChange={(e) => setGameTitle(e.target.value)}
            placeholder="Ex: Red Dead Redemption 2"
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
          />
          <datalist id="game-fps-titles">
            {gamesQuery.data?.map((title) => <option key={title} value={title} />)}
          </datalist>
        </label>

        <label className="w-32">
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

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!gameTitle.trim()}
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300 dark:disabled:bg-slate-700"
        >
          Ver FPS
        </button>
      </div>

      {gamesQuery.data && gamesQuery.data.length > 0 && (
        <p className="mb-4 text-xs text-slate-400 dark:text-slate-500">
          Jogos com dado cadastrado: {gamesQuery.data.join(', ')}.
        </p>
      )}

      {noGpuWarning && (
        <p className="mb-4 text-sm text-amber-700 dark:text-amber-400">
          Não é possível calcular o FPS: nenhuma GPU foi selecionada no catálogo na etapa
          anterior. Volte e escolha uma GPU (mesmo que seja a mais parecida com a sua) para
          habilitar essa comparação.
        </p>
      )}

      {(currentMutation.isSuccess ||
        currentMutation.isPending ||
        currentMutation.isError ||
        futureMutation.isSuccess ||
        futureMutation.isPending ||
        futureMutation.isError) && (
        <div className="grid gap-4 border-t border-slate-200 pt-4 sm:grid-cols-2 dark:border-slate-700">
          <FpsColumn title="PC atual" gpuModelName={currentGpu} mutation={currentMutation} />
          <FpsColumn title="PC futuro" gpuModelName={futureGpu} mutation={futureMutation} />
        </div>
      )}
    </Card>
  )
}
