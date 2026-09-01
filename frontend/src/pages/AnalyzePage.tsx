import { useState } from 'react'
import { Card } from '../components/ui/Card'
import { DetectionStep } from '../features/detection/DetectionStep'
import { ResultsView } from '../features/results/ResultsView'
import { useRunAnalysis } from '../features/results/useRunAnalysis'
import { SystemSelectionStep } from '../features/system/SystemSelectionStep'
import type { HardwareSnapshot } from '../types/detection'

type Step = 'detect' | 'select' | 'results'

const STEP_LABELS: Record<Step, string> = {
  detect: 'Etapa 1 de 3 — Detecção de hardware',
  select: 'Etapa 2 de 3 — Componentes e cenário de uso',
  results: 'Etapa 3 de 3 — Relatório de diagnóstico',
}

export function AnalyzePage() {
  const [confirmedSnapshot, setConfirmedSnapshot] = useState<HardwareSnapshot | null>(null)
  const analysis = useRunAnalysis()

  const step: Step = !confirmedSnapshot ? 'detect' : analysis.data ? 'results' : 'select'

  function handleReset() {
    setConfirmedSnapshot(null)
    analysis.reset()
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="mb-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">
        Analisar meu PC
      </h1>
      <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">{STEP_LABELS[step]}</p>

      {step === 'detect' && <DetectionStep onContinue={setConfirmedSnapshot} />}

      {step === 'select' && confirmedSnapshot && (
        <>
          <SystemSelectionStep
            detected={confirmedSnapshot}
            onAnalyze={(config) => analysis.mutate(config)}
            isSubmitting={analysis.isPending}
          />
          {analysis.isError && (
            <Card className="mt-4 border-red-300 dark:border-red-800">
              <p className="text-sm text-red-700 dark:text-red-400">
                Não foi possível concluir a análise: {(analysis.error as Error).message}
              </p>
            </Card>
          )}
        </>
      )}

      {step === 'results' && analysis.data && (
        <ResultsView result={analysis.data} onReset={handleReset} />
      )}
    </div>
  )
}
