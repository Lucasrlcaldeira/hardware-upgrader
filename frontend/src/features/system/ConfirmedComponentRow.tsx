export function ConfirmedComponentRow({
  label,
  value,
  onEdit,
}: {
  label: string
  value: string
  onEdit: () => void
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 dark:border-emerald-900 dark:bg-emerald-950/30">
      <div className="min-w-0">
        <p className="text-xs text-emerald-700 dark:text-emerald-400">{label}</p>
        <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">{value}</p>
      </div>
      <button
        type="button"
        onClick={onEdit}
        className="shrink-0 text-xs font-medium text-emerald-700 underline hover:text-emerald-900 dark:text-emerald-400 dark:hover:text-emerald-200"
      >
        Trocar
      </button>
    </div>
  )
}
