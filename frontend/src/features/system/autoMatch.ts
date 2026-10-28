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

// Ruído removido ANTES de quebrar em tokens: depois disso "(TM)" vira um token "tm" solto,
// "@ 3.20GHz" vira "3" + "20ghz" e "6-Core" vira um "6" — e qualquer token que sobra impede o
// casamento exato. Era por isso que CPUs Intel ("Intel(R) Core(TM) i5-12400 CPU @ 2.50GHz")
// e Ryzens recentes ("AMD Ryzen 5 5600 6-Core Processor") nunca casavam com o catálogo.
const PRE_STRIP_PATTERNS = [
  /\((?:r|tm|c)\)/g,
  /[®™]/g,
  /@?\s*\d+(?:[.,]\d+)?\s*ghz\b/g,
  /\b\d+-core\b/g,
]

function tokenize(value: string): string[] {
  let normalized = value.toLowerCase().normalize('NFD').replace(/\p{Diacritic}/gu, '')
  for (const pattern of PRE_STRIP_PATTERNS) {
    normalized = normalized.replace(pattern, ' ')
  }
  return normalized
    .replace(/[^a-z0-9]+/g, ' ')
    .split(' ')
    .filter(Boolean)
}

function significantTokens(value: string): Set<string> {
  return new Set(tokenize(value).filter((t) => !IGNORABLE_TOKENS.has(t)))
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

  const detectedTokens = significantTokens(detected)
  if (detectedTokens.size === 0) return null

  // Os dois lados passam pelo mesmo filtro: se só a string detectada perdesse os tokens
  // genéricos, um item como "Core i5-12400" (com "core", que é genérico) nunca casaria.
  const matches = options.filter((option) => {
    const optionTokens = significantTokens(option.model_name)
    if (optionTokens.size === 0) return false
    return (
      optionTokens.size === detectedTokens.size &&
      [...optionTokens].every((t) => detectedTokens.has(t))
    )
  })

  return matches.length === 1 ? matches[0] : null
}
