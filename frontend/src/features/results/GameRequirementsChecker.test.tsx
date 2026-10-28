import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as gamesApi from '../../api/games'
import type { GameRequirementsCheckResult } from '../../types/games'
import type { ComponentRecommendation } from '../../types/recommendation'
import { GameRequirementsChecker } from './GameRequirementsChecker'
import { buildUpgradedSystem } from './upgradedSystem'

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const gpuRecommendation: ComponentRecommendation = {
  slot: 'gpu',
  current_model_name: 'GeForce GTX 1650',
  problem: 'GPU fraca',
  recommended_model_name: 'GeForce RTX 4060',
  expected_gain: '+40',
  compatibility_status: 'COMPATIVEL',
  additional_required_components: [],
  remaining_limitations: [],
  priority: 'ALTA',
  cost_benefit: 'ok',
}

const checkResult: GameRequirementsCheckResult = {
  app_id: 1091500,
  name: 'Cyberpunk 2077',
  store_url: 'https://store.steampowered.com/app/1091500',
  header_image: null,
  minimum_requirements: [{ label: 'Memory', value: '12 GB RAM' }],
  recommended_requirements: [{ label: 'Memory', value: '16 GB RAM' }],
  current: {
    verdict: 'RODA_NO_MINIMO',
    verdict_text: 'Seu PC atende aos requisitos mínimos.',
    minimum: {
      tier: 'MINIMUM',
      status: 'ATENDE',
      checks: [
        {
          component: 'gpu',
          required: 'GeForce GTX 1060 6GB',
          yours: 'GeForce GTX 1650',
          status: 'ATENDE',
          explanation: 'Tem desempenho igual ou melhor.',
          counts_for_verdict: true,
        },
      ],
    },
    recommended: {
      tier: 'RECOMMENDED',
      status: 'NAO_ATENDE',
      checks: [
        {
          component: 'gpu',
          required: 'GeForce RTX 2060 SUPER',
          yours: 'GeForce GTX 1650',
          status: 'NAO_ATENDE',
          explanation: 'Fica abaixo.',
          counts_for_verdict: true,
        },
      ],
    },
  },
  upgraded: {
    verdict: 'RODA_NO_RECOMENDADO',
    verdict_text: 'Com o upgrade, roda no recomendado.',
    minimum: null,
    recommended: {
      tier: 'RECOMMENDED',
      status: 'ATENDE',
      checks: [
        {
          component: 'gpu',
          required: 'GeForce RTX 2060 SUPER',
          yours: 'GeForce RTX 4060',
          status: 'ATENDE',
          explanation: 'Tem desempenho igual ou melhor.',
          counts_for_verdict: true,
        },
      ],
    },
  },
  disclaimer: 'É uma referência, não uma garantia.',
}

describe('GameRequirementsChecker', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('searches Steam, checks the chosen game and compares with the upgraded PC', async () => {
    vi.spyOn(gamesApi, 'searchSteamGames').mockResolvedValue([
      { app_id: 1091500, name: 'Cyberpunk 2077', image_url: null },
    ])
    const checkSpy = vi.spyOn(gamesApi, 'checkGameRequirements').mockResolvedValue(checkResult)
    const user = userEvent.setup()

    renderWithClient(
      <GameRequirementsChecker
        system={{ gpu_model_name: 'GeForce GTX 1650' }}
        detected={null}
        recommendations={[gpuRecommendation]}
      />,
    )

    await user.type(screen.getByRole('searchbox'), 'cyberpunk')
    await user.click(await screen.findByRole('button', { name: 'Cyberpunk 2077' }))

    expect(await screen.findByText('Roda no mínimo')).toBeInTheDocument()
    expect(screen.getByText('Roda no recomendado')).toBeInTheDocument()
    expect(checkSpy).toHaveBeenCalledWith({
      app_id: 1091500,
      system: { gpu_model_name: 'GeForce GTX 1650' },
      detected: null,
      upgraded_system: { gpu_model_name: 'GeForce RTX 4060' },
    })

    await user.click(screen.getByRole('tab', { name: 'Requisitos recomendados' }))
    expect(screen.getByText('GeForce RTX 2060 SUPER')).toBeInTheDocument()
    expect(screen.getByText('Com o upgrade: GeForce RTX 4060')).toBeInTheDocument()
  })

  it('shows the backend message when the game has no PC requirements', async () => {
    vi.spyOn(gamesApi, 'searchSteamGames').mockResolvedValue([
      { app_id: 7, name: 'Jogo Sem Requisitos', image_url: null },
    ])
    vi.spyOn(gamesApi, 'checkGameRequirements').mockRejectedValue(
      new Error('A Steam não lista requisitos de PC para este jogo.'),
    )
    const user = userEvent.setup()

    renderWithClient(<GameRequirementsChecker system={{}} detected={null} recommendations={[]} />)

    await user.type(screen.getByRole('searchbox'), 'jogo')
    await user.click(await screen.findByRole('button', { name: 'Jogo Sem Requisitos' }))

    expect(
      await screen.findByText('A Steam não lista requisitos de PC para este jogo.'),
    ).toBeInTheDocument()
  })
})

describe('buildUpgradedSystem', () => {
  it('only swaps parts that appear in game requirements', () => {
    const upgraded = buildUpgradedSystem({ cpu_model_name: 'CPU', psu_model_name: 'Fonte' }, [
      gpuRecommendation,
      { ...gpuRecommendation, slot: 'psu', recommended_model_name: 'Fonte Nova' },
    ])

    expect(upgraded?.system).toEqual({
      cpu_model_name: 'CPU',
      psu_model_name: 'Fonte',
      gpu_model_name: 'GeForce RTX 4060',
    })
    expect(upgraded?.names).toEqual(['GeForce RTX 4060'])
  })

  it('returns null when no relevant upgrade was recommended', () => {
    expect(buildUpgradedSystem({}, [])).toBeNull()
  })
})
