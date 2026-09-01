import { apiGet } from './client'
import type { CatalogOption } from '../types/catalog'

export function fetchCpus(): Promise<CatalogOption[]> {
  return apiGet<CatalogOption[]>('/catalog/cpus')
}

export function fetchGpus(): Promise<CatalogOption[]> {
  return apiGet<CatalogOption[]>('/catalog/gpus')
}

export function fetchMotherboards(): Promise<CatalogOption[]> {
  return apiGet<CatalogOption[]>('/catalog/motherboards')
}

export function fetchRamKits(): Promise<CatalogOption[]> {
  return apiGet<CatalogOption[]>('/catalog/ram')
}

export function fetchStorage(): Promise<CatalogOption[]> {
  return apiGet<CatalogOption[]>('/catalog/storage')
}

export function fetchPsus(): Promise<CatalogOption[]> {
  return apiGet<CatalogOption[]>('/catalog/psus')
}

export function fetchCases(): Promise<CatalogOption[]> {
  return apiGet<CatalogOption[]>('/catalog/cases')
}

export function fetchCoolers(): Promise<CatalogOption[]> {
  return apiGet<CatalogOption[]>('/catalog/coolers')
}
