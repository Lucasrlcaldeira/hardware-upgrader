import type { CatalogOption } from '../../types/catalog'

// Tokens genéricos que a detecção costuma acrescentar ao redor do nome real do modelo
// (fabricante, descritores de núcleo/tipo de componente) — removidos antes de comparar com
// o catálogo. Deliberadamente conservador: nunca inclui um token que possa distinguir
// produtos diferentes (ex: "xt", "ti", "super" nunca entram aqui).
const IGNORABLE_TOKENS = new Set([
  'amd',
  'nvidia',
  'intel',
  'asus',
  'asrock',
  'msi',
  'gigabyte',
  'evga',
  'zotac',
  'sapphire',
  'processor',
  'processador',
  'cpu',
  'gpu',
  'graphics',
  'card',
  'placa',
  'de',
  'video',
  'six',
  'quad',
  'eight',
  'dual',
  'ten',
  'twelve',
  'sixteen',
  'core',
  'cores',
  'com',
])

function tokenize(value: string): string[] {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .split(' ')
    .filter(Boolean)
}

function isClockSpeedToken(token: string): boolean {
  return /^\d+(\.\d+)?g?hz$/.test(token)
}

/**
 * Só casa um item do catálogo se, depois de remover tokens genéricos (fabricante,
 * "processor", contagem de núcleos, velocidade de clock), o que sobrar da string detectada
 * for EXATAMENTE o conjunto de tokens do model_name do catálogo — nem a mais, nem a menos.
 * Prefere não casar (deixando para seleção manual) a arriscar confundir produtos parecidos
 * mas diferentes (ex: "Radeon RX 6600" vs "Radeon RX 6600 XT" não devem ser tratados como
 * o mesmo item).
 */
export function findCatalogAutoMatch(
  detected: string | null | undefined,
  options: CatalogOption[] | undefined,
): CatalogOption | null {
  if (!detected || !options?.length) return null

  const detectedTokens = new Set(
    tokenize(detected).filter((t) => !IGNORABLE_TOKENS.has(t) && !isClockSpeedToken(t)),
  )
  if (detectedTokens.size === 0) return null

  const matches = options.filter((option) => {
    const optionTokens = tokenize(option.model_name)
    if (optionTokens.length === 0) return false
    return (
      optionTokens.length === detectedTokens.size &&
      optionTokens.every((t) => detectedTokens.has(t))
    )
  })

  return matches.length === 1 ? matches[0] : null
}
