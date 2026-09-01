import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { GameFpsExplorer } from './GameFpsExplorer'
import type { CombinedAnalysisResult } from './useRunAnalysis'
import {
  BOTTLENECK_VERDICT_LABELS,
  COMPATIBILITY_RELATION_LABELS,
  COMPATIBILITY_STATUS_LABELS,
  COMPATIBILITY_STATUS_STYLES,
  CONFIDENCE_LABELS,
  PRIORITY_LABELS,
  PRIORITY_STYLES,
  SLOT_LABELS,
  slotLabel,
} from './labels'

export function ResultsView({
  result,
  onReset,
}: {
  result: CombinedAnalysisResult
  onReset: () => void
}) {
  const { system, compatibility, bottleneck, bottleneckNote, recommendation } = result

  return (
    <div className="space-y-4">
      <Card>
        <p className="text-slate-900 dark:text-slate-100">{recommendation.summary}</p>
      </Card>

      {recommendation.bundle && (
        <Card className="border-orange-300 bg-orange-50 dark:border-orange-800 dark:bg-orange-950/30">
          <p className="font-medium text-orange-900 dark:text-orange-200">
            Upgrade de conjunto necessário
          </p>
          <p className="mt-1 text-sm text-orange-800 dark:text-orange-300">
            {recommendation.bundle.reason}
          </p>
          <p className="mt-2 text-sm text-orange-800 dark:text-orange-300">
            Componentes envolvidos:{' '}
            {recommendation.bundle.components.map(slotLabel).join(', ')}
          </p>
        </Card>
      )}

      <section>
        <h2 className="mb-2 font-medium text-slate-900 dark:text-slate-100">
          Compatibilidade do sistema atual
        </h2>
        {compatibility.results.length === 0 ? (
          <Card>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Componentes insuficientes para checar compatibilidade entre pares — selecione mais
              itens na etapa anterior.
            </p>
          </Card>
        ) : (
          <div className="space-y-2">
            {compatibility.results.map((r, i) => (
              <Card key={i} className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {COMPATIBILITY_RELATION_LABELS[r.relation]}
                  </p>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{r.reason}</p>
                </div>
                <Badge
                  text={COMPATIBILITY_STATUS_LABELS[r.status]}
                  className={COMPATIBILITY_STATUS_STYLES[r.status]}
                />
              </Card>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="mb-2 font-medium text-slate-900 dark:text-slate-100">Análise de gargalo</h2>
        <Card>
          {bottleneck ? (
            <>
              <div className="flex items-center justify-between gap-4">
                <p className="font-medium text-slate-900 dark:text-slate-100">
                  {BOTTLENECK_VERDICT_LABELS[bottleneck.verdict]}
                </p>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  {CONFIDENCE_LABELS[bottleneck.confidence]}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                {bottleneck.explanation}
              </p>
              {bottleneck.contributing_factors.length > 0 && (
                <ul className="mt-2 list-inside list-disc text-xs text-slate-500 dark:text-slate-400">
                  {bottleneck.contributing_factors.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {bottleneckNote ?? 'Dado insuficiente para determinar gargalo.'}
            </p>
          )}
        </Card>
      </section>

      <section>
        <h2 className="mb-2 font-medium text-slate-900 dark:text-slate-100">
          Recomendações de upgrade
        </h2>
        {recommendation.recommendations.length === 0 ? (
          <Card>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Nenhum componente foi identificado como limitante para o perfil escolhido.
            </p>
          </Card>
        ) : (
          <div className="space-y-3">
            {recommendation.recommendations.map((rec) => (
              <Card key={rec.slot}>
                <div className="flex items-start justify-between gap-4">
                  <p className="font-medium text-slate-900 dark:text-slate-100">
                    {SLOT_LABELS[rec.slot]}
                  </p>
                  <div className="flex shrink-0 gap-2">
                    <Badge text={PRIORITY_LABELS[rec.priority]} className={PRIORITY_STYLES[rec.priority]} />
                    <Badge
                      text={COMPATIBILITY_STATUS_LABELS[rec.compatibility_status]}
                      className={COMPATIBILITY_STATUS_STYLES[rec.compatibility_status]}
                    />
                  </div>
                </div>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{rec.problem}</p>
                <p className="mt-2 text-sm text-slate-900 dark:text-slate-100">
                  <span className="text-slate-500 dark:text-slate-400">Atual: </span>
                  {rec.current_model_name ?? '—'}
                  <span className="mx-2 text-slate-400">→</span>
                  <span className="font-medium">{rec.recommended_model_name}</span>
                </p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{rec.expected_gain}</p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{rec.cost_benefit}</p>
                {rec.additional_required_components.length > 0 && (
                  <p className="mt-2 text-xs text-orange-700 dark:text-orange-400">
                    Também exige: {rec.additional_required_components.map(slotLabel).join(', ')}
                  </p>
                )}
                {rec.remaining_limitations.length > 0 && (
                  <ul className="mt-2 list-inside list-disc text-xs text-slate-500 dark:text-slate-400">
                    {rec.remaining_limitations.map((l, i) => (
                      <li key={i}>{l}</li>
                    ))}
                  </ul>
                )}
              </Card>
            ))}
          </div>
        )}
      </section>

      <GameFpsExplorer system={system} recommendations={recommendation.recommendations} />

      <button
        type="button"
        onClick={onReset}
        className="w-full rounded-md border border-slate-300 px-4 py-2 font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800"
      >
        Nova análise
      </button>
    </div>
  )
}
