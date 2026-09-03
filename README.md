# Hardware Upgrader

Sistema de diagnóstico de hardware de PC e recomendação de upgrades compatíveis, com
justificativa técnica para cada recomendação — não uma lista genérica de peças.

## Como funciona (visão geral)

O backend roda **na própria máquina que será analisada** (é assim que a detecção
automática de CPU/GPU/RAM/etc. é possível de verdade — um navegador sozinho não
consegue ler isso). O frontend React abre no navegador e conversa com esse backend
local. Pense nele como um Speccy/HWiNFO com interface web e motor de recomendação.

Módulos principais do backend: `detection` (coleta de hardware), `catalog` (base de
componentes com specs reais, atualizável sem alterar código), `compatibility` (motor de
regras de compatibilidade), `performance` (análise de gargalo CPU/GPU), `recommendation`
(motor de recomendação + perfis de upgrade), `analysis` (orquestra tudo e guarda
histórico) e `users` (autenticação).

## Rodando localmente (desenvolvimento)

### Backend

```
cd backend
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example ..\.env   # ajuste se necessário
uvicorn app.main:app --reload
```

Docs interativas em `http://localhost:8000/docs`.

### Frontend

```
cd frontend
npm install
npm run dev
```

Abre em `http://localhost:5173`.

### Banco de dados (PostgreSQL)

Requer Docker Desktop instalado e rodando:

```
docker compose up -d postgres
```

> **a detecção de hardware só reflete a máquina real quando o backend roda nativamente**
> (fora do container) — o `docker-compose.yml` deste projeto só sobe o Postgres; não há
> serviço de `backend`/`frontend` em container.

### Dados do catálogo e de benchmarks (seed)

As tabelas de catálogo (CPUs/GPUs/etc.) e de jogos/benchmarks começam vazias após rodar
as migrações — sem isso, o catálogo aparece sem opções e "FPS por jogo" nunca encontra
dado. Depois de `alembic upgrade head`, rode (idempotente, pode rodar de novo a qualquer
momento):

```
backend\.venv\Scripts\python -m app.modules.catalog.seed.load_seed
backend\.venv\Scripts\python -m app.modules.games.seed.load_seed
```

## Status do projeto

Em desenvolvimento por etapas. Backend: `catalog`, `compatibility`, `performance`,
`detection`, `recommendation`, `users` (autenticação JWT), `analysis` (orquestra os
demais módulos e persiste histórico por usuário) e `games` (FPS por jogo, com benchmarks
reais cadastrados e aproximação transparente por GPU de desempenho próximo quando a GPU
exata não tem dado) implementados e testados. Frontend: fluxo completo conectado à API,
da detecção de hardware ao relatório final (compatibilidade, gargalo, recomendações e
comparação de FPS).
