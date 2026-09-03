import { Link } from 'react-router-dom'

export function LandingPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center gap-6 px-4 py-24 text-center">
      <h1 className="text-4xl font-semibold text-slate-900 dark:text-slate-100">
        Hardware Upgrader
      </h1>
      <p className="text-slate-600 dark:text-slate-400">
        Diagnóstico técnico do seu PC e recomendações de upgrade com justificativa — não uma
        lista genérica de peças.
      </p>
      <Link
        to="/analyze"
        className="rounded-md bg-indigo-600 px-6 py-3 font-medium text-white hover:bg-indigo-500"
      >
        Analisar meu PC
      </Link>
    </div>
  )
}
