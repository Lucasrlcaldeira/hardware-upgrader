import { describe, expect, it } from 'vitest'
import { findCatalogAutoMatch } from './autoMatch'

const cpus = [
  { model_name: 'Ryzen 5 1600', manufacturer: 'AMD' },
  { model_name: 'Ryzen 5 5600', manufacturer: 'AMD' },
]

const gpus = [
  { model_name: 'Radeon RX 6600', manufacturer: 'AMD' },
  { model_name: 'Radeon RX 7600', manufacturer: 'AMD' },
]

const motherboards = [{ model_name: 'AM4 B450 (referência de chipset)', manufacturer: 'Genérico' }]

describe('findCatalogAutoMatch', () => {
  it('matches a CPU string with vendor/core-count noise stripped around the real model', () => {
    const match = findCatalogAutoMatch('AMD Ryzen 5 1600 Six-Core Processor', cpus)
    expect(match?.model_name).toBe('Ryzen 5 1600')
  })

  it('does NOT match a GPU variant (XT) to the base model — different products', () => {
    const match = findCatalogAutoMatch('AMD Radeon RX 6600 XT', gpus)
    expect(match).toBeNull()
  })

  it('matches an exact GPU string once noise is stripped', () => {
    const match = findCatalogAutoMatch('AMD Radeon RX 6600', gpus)
    expect(match?.model_name).toBe('Radeon RX 6600')
  })

  it('returns null when nothing in the catalog is close', () => {
    const match = findCatalogAutoMatch('ASRock A320M-DGS', motherboards)
    expect(match).toBeNull()
  })

  it('returns null for missing/empty input', () => {
    expect(findCatalogAutoMatch(null, cpus)).toBeNull()
    expect(findCatalogAutoMatch(undefined, cpus)).toBeNull()
    expect(findCatalogAutoMatch('Ryzen 5 1600', undefined)).toBeNull()
  })
})
