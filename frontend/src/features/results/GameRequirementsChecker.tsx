import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { ApiError } from '../../api/client'
import { checkGameRequirements, searchSteamGames } from '../../api/games'
import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import type { SystemSnapshot } from '../../types/compatibility'
import type { HardwareSnapshot } from '../../types/detection'
import type {
  RequirementCheck,
  RequirementLine,
  RequirementTier,
  SteamGameSummary,
  SystemEvaluation,
  TierEvaluation,
} from '../../types/games'
import type { ComponentRecommendation } from '../../types/recommendation'
import {
  CHECK_STATUS_LABELS,
  CHECK_STATUS_STYLES,
  GAME_VERDICT_LABELS,
  GAME_VERDICT_STYLES,
  REQUIREMENT_COMPONENT_LABELS,
} from './labels'
import { buildUpgradedSystem } from './upgradedSystem'

const SEARCH_DEBOUNCE_MS = 350
const MIN_SEARCH_LENGTH = 2

const TIER_LABELS: Record<RequirementTier, string> = {
  MINIMUM: 'Requisitos mínimos',
  RECOMMENDED: 'Requisitos recomendados',
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(id)
  }, [value, delayMs])
  return debounced
}

// 4xx são respostas definitivas do backend (jogo sem requisitos, não encontrado) — repetir
// a requisição não muda nada. Só vale tentar de novo quando a Steam não respondeu (502).
function retryOnlyServerErrors(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && error.status < 500) return false
  return failureCount < 1
}

function VerdictBox({ title, evaluation }: { title: string; evaluation: SystemEvaluation }) {
  return (
    <div className={`rounded-md border p-4 ${GAME_VERDICT_STYLES[evaluation.verdict]}`}>
      <p className="text-xs font-medium opacity-80">{title}</p>
      <p className="mt-0.5 text-lg font-semibold">{GAME_VERDICT_LABELS[evaluation.verdict]}</p>
      <p className="mt-1 text-sm">{evaluation.verdict_text}</p>
    </div>
  )
}

function CheckRow({
  check,
  upgradedCheck,
}: {
  check: RequirementCheck
  upgradedCheck?: RequirementCheck
}) {
  // Só mostra a linha "com upgrade" quando algo de fato muda — senão é ruído repetido.
  const upgradeChangesSomething =
    upgradedCheck &&
    (upgradedCheck.yours !== check.yours || upgradedCheck.status !== check.status)

  return (
    <li className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
          {REQUIREMENT_COMPONENT_LABELS[check.component]}
        </p>
        <Badge text={CHECK_STATUS_LABELS[check.status]} className={CHECK_STATUS_STYLES[check.status]} />
      </div>
      <dl className="mt-1 grid gap-x-3 text-sm sm:grid-cols-[auto_1fr]">
        <dt className="text-slate-500 dark:text-slate-400">O jogo pede</dt>
        <dd className="break-words text-slate-900 dark:text-slate-100">{check.required}</dd>
        <dt className="text-slate-500 dark:text-slate-400">Seu PC</dt>
        <dd className="break-words text-slate-900 dark:text-slate-100">{check.yours ?? '—'}</dd>
      </dl>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        {check.explanation}
        {!check.counts_for_verdict && ' (Isso não muda o veredito, mas vale conferir.)'}
      </p>
      {upgradeChangesSomething && upgradedCheck && (
        <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-sky-800 dark:text-sky-300">
          <span>Com o upgrade: {upgradedCheck.yours ?? '—'}</span>
          <Badge
            text={CHECK_STATUS_LABELS[upgradedCheck.status]}
            className={CHECK_STATUS_STYLES[upgradedCheck.status]}
          />
        </p>
      )}
    </li>
  )
}

function RawRequirements({ lines }: { lines: RequirementLine[] }) {
  if (lines.length === 0) return null
  return (
    <details className="mt-3 text-xs text-slate-500 dark:text-slate-400">
      <summary className="cursor-pointer hover:text-slate-700 dark:hover:text-slate-200">
        Ver o texto original da Steam
      </summary>
      <ul className="mt-2 space-y-1">
        {lines.map((line, i) => (
          <li key={i}>
            {line.label && <span className="font-medium">{line.label}: </span>}
            {line.value}
          </li>
        ))}
      </ul>
    </details>
  )
}

function TierDetails({
  tier,
  upgradedTier,
  rawLines,
}: {
  tier: TierEvaluation
  upgradedTier: TierEvaluation | null | undefined
  rawLines: RequirementLine[]
}) {
  return (
    <div>
      <ul className="space-y-2">
        {tier.checks.map((check) => (
          <CheckRow
            key={check.component}
            check={check}
            upgradedCheck={upgradedTier?.checks.find((c) => c.component === check.component)}
          />
        ))}
      </ul>
      <RawRequirements lines={rawLines} />
    </div>
  )
}

function GameResult({
  game,
  system,
  detected,
  upgraded,
}: {
  game: SteamGameSummary
  system: SystemSnapshot
  detected: HardwareSnapshot | null
  upgraded: { system: SystemSnapshot; names: string[] } | null
}) {
  const [activeTier, setActiveTier] = useState<RequirementTier>('MINIMUM')

  const checkQuery = useQuery({
    queryKey: ['game-requirements', game.app_id, system, detected, upgraded?.system ?? null],
    queryFn: () =>
      checkGameRequirements({
        app_id: game.app_id,
        system,
        detected,
        upgraded_system: upgraded?.system ?? null,
      }),
    // Mesmo jogo + mesmo PC = mesmo resultado; não há por que consultar de novo na sessão.
    staleTime: Infinity,
    retry: retryOnlyServerErrors,
  })

  if (checkQuery.isPending) {
    return (
      <p className="text-sm text-slate-500 dark:text-slate-400">
        Abrindo a página de {game.name} na Steam e comparando com o seu PC…
      </p>
    )
  }
  if (checkQuery.isError) {
    return <p className="text-sm text-amber-700 dark:text-amber-400">{checkQuery.error.message}</p>
  }

  const result = checkQuery.data
  const tiers = [result.current.minimum, result.current.recommended].filter(
    (t): t is TierEvaluation => t !== null,
  )
  // Jogos que só publicam um dos dois: a aba ativa cai na que existe.
  const shownTier = tiers.find((t) => t.tier === activeTier) ?? tiers[0]
  const upgradedTier =
    shownTier.tier === 'MINIMUM' ? result.upgraded?.minimum : result.upgraded?.recommended
  const rawLines =
    shownTier.tier === 'MINIMUM' ? result.minimum_requirements : result.recommended_requirements

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        {result.header_image && (
          <img
            src={result.header_image}
            alt=""
            className="h-16 w-auto rounded-md object-cover"
            loading="lazy"
          />
        )}
        <div className="min-w-0">
          <p className="font-medium text-slate-900 dark:text-slate-100">{result.name}</p>
          <a
            href={result.store_url}
            target="_blank"
            rel="noreferrer"
            className="text-sm text-indigo-600 underline hover:text-indigo-500 dark:text-indigo-400"
          >
            Ver a página na Steam ↗
          </a>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <VerdictBox title="Seu PC hoje" evaluation={result.current} />
        {result.upgraded && upgraded && (
          <VerdictBox
            title={`Com os upgrades recomendados (${upgraded.names.join(', ')})`}
            evaluation={result.upgraded}
          />
        )}
      </div>

      <div>
        <div className="mb-3 flex gap-2" role="tablist">
          {tiers.map((t) => (
            <button
              key={t.tier}
              type="button"
              role="tab"
              aria-selected={t.tier === shownTier.tier}
              onClick={() => setActiveTier(t.tier)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                t.tier === shownTier.tier
                  ? 'bg-indigo-600 text-white'
                  : 'border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800'
              }`}
            >
              {TIER_LABELS[t.tier]}
            </button>
          ))}
        </div>
        <TierDetails tier={shownTier} upgradedTier={upgradedTier} rawLines={rawLines} />
      </div>

      <p className="text-xs text-slate-400 dark:text-slate-500">{result.disclaimer}</p>
    </div>
  )
}

export function GameRequirementsChecker({
  system,
  detected,
  recommendations,
}: {
  system: SystemSnapshot
  detected: HardwareSnapshot | null
  recommendations: ComponentRecommendation[]
}) {
  const [term, setTerm] = useState('')
  const [selectedGame, setSelectedGame] = useState<SteamGameSummary | null>(null)
  const debouncedTerm = useDebouncedValue(term.trim(), SEARCH_DEBOUNCE_MS)
  const upgraded = buildUpgradedSystem(system, recommendations)

  const searchQuery = useQuery({
    queryKey: ['steam-search', debouncedTerm],
    queryFn: () => searchSteamGames(debouncedTerm),
    enabled: debouncedTerm.length >= MIN_SEARCH_LENGTH,
    staleTime: 5 * 60 * 1000,
    retry: retryOnlyServerErrors,
  })

  function selectGame(game: SteamGameSummary) {
    setSelectedGame(game)
    setTerm('')
  }

  const showResults = term.trim().length >= MIN_SEARCH_LENGTH

  return (
    <Card>
      <h2 className="mb-1 font-medium text-slate-900 dark:text-slate-100">
        Será que roda? Confira um jogo da Steam
      </h2>
      <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
        Escolha um jogo: a gente abre a página dele na Steam, pega os requisitos mínimos e
        recomendados que o próprio desenvolvedor publicou e compara com as suas peças. Nada de
        "você vai ter 87 FPS": só com a lista de peças, qualquer número desses seria chute.
      </p>

      <label className="block">
        <span className="text-sm text-slate-500 dark:text-slate-400">Buscar jogo na Steam</span>
        <input
          type="search"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="Ex: Cyberpunk 2077 (ou cole o link da loja)"
          className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
        />
      </label>

      {showResults && (
        <div className="mt-2">
          {searchQuery.isFetching && (
            <p className="text-sm text-slate-500 dark:text-slate-400">Buscando na Steam…</p>
          )}
          {searchQuery.isError && (
            <p className="text-sm text-amber-700 dark:text-amber-400">{searchQuery.error.message}</p>
          )}
          {searchQuery.isSuccess && !searchQuery.isFetching && searchQuery.data.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Nenhum jogo encontrado com esse nome na Steam.
            </p>
          )}
          {searchQuery.isSuccess && searchQuery.data.length > 0 && (
            <ul className="max-h-72 divide-y divide-slate-100 overflow-y-auto rounded-md border border-slate-200 dark:divide-slate-800 dark:border-slate-700">
              {searchQuery.data.map((game) => (
                <li key={game.app_id}>
                  <button
                    type="button"
                    onClick={() => selectGame(game)}
                    className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
                  >
                    {game.image_url ? (
                      <img src={game.image_url} alt="" className="h-8 w-20 shrink-0 rounded object-cover" loading="lazy" />
                    ) : (
                      <span className="h-8 w-20 shrink-0 rounded bg-slate-200 dark:bg-slate-700" />
                    )}
                    <span className="text-slate-900 dark:text-slate-100">{game.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {selectedGame && (
        <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-700">
          <GameResult
            key={selectedGame.app_id}
            game={selectedGame}
            system={system}
            detected={detected}
            upgraded={upgraded}
          />
        </div>
      )}
    </Card>
  )
}
