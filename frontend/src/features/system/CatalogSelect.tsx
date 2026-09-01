import { useQuery } from '@tanstack/react-query'
import type { CatalogOption } from '../../types/catalog'

export function CatalogSelect({
  label,
  queryKey,
  fetcher,
  value,
  onChange,
  hint,
}: {
  label: string
  queryKey: string
  fetcher: () => Promise<CatalogOption[]>
  value: string | null
  onChange: (value: string | null) => void
  hint?: string | null
}) {
  const { data, status } = useQuery({ queryKey: [queryKey], queryFn: fetcher })

  return (
    <label className="block">
      <span className="text-sm text-slate-500 dark:text-slate-400">{label}</span>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={status !== 'success'}
        className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm disabled:opacity-60 dark:border-slate-600 dark:bg-slate-800"
      >
        <option value="">— não informado —</option>
        {data?.map((item) => (
          <option key={item.model_name} value={item.model_name}>
            {item.manufacturer ? `${item.manufacturer} ${item.model_name}` : item.model_name}
          </option>
        ))}
      </select>
      {status === 'error' && (
        <p className="mt-1 text-xs text-red-600 dark:text-red-400">Falha ao carregar opções.</p>
      )}
      {hint && <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">Detectado: {hint}</p>}
    </label>
  )
}
