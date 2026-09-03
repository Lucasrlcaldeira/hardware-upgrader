import type { DetectionSource } from '../../types/detection'

const STYLES: Record<DetectionSource, string> = {
  DETECTED: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  MANUAL_REQUIRED: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  MANUAL_PROVIDED: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300',
}

const LABELS: Record<DetectionSource, string> = {
  DETECTED: 'Achamos sozinho',
  MANUAL_REQUIRED: 'Preencha você',
  MANUAL_PROVIDED: 'Você preencheu',
}

export function StatusPill({ status }: { status: DetectionSource }) {
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  )
}
