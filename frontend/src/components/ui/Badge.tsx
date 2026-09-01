export function Badge({ text, className }: { text: string; className: string }) {
  return (
    <span
      className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${className}`}
    >
      {text}
    </span>
  )
}
