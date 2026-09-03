import type { CatalogOption } from '../../types/catalog'

export function CatalogSelect({
  label,
  options,
  status,
  value,
  onChange,
  hint,
}: {
  label: string
  options: CatalogOption[] | undefined
  status: 'pending' | 'error' | 'success'
  value: string | null
  onChange: (value: string | null) => void
  hint?: string | null
}) {
  return (
    <label className="block">
      <span className="text-sm text-slate-500 dark:text-slate-400">{label}</span>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={status !== 'success'}
        className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800"
      >
        <option value="">— nenhuma —</option>
        {options?.map((item) => (
          <option key={item.model_name} value={item.model_name}>
            {item.manufacturer ? `${item.manufacturer} ${item.model_name}` : item.model_name}
          </option>
        ))}
      </select>
      {status === 'error' && (
        <p className="mt-1 text-xs text-red-600 dark:text-red-400">
          Não deu pra carregar as opções agora.
        </p>
      )}
      {hint && <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">Achamos: {hint}</p>}
    </label>
  )
}
