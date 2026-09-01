# Hardware Upgrade Advisor

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

> O `docker-compose.yml` também sobe `backend`/`frontend` em containers para fins de
> build/produção, mas **a detecção de hardware só reflete a máquina real quando o
> backend roda nativamente** (fora do container) — dentro do Docker ele só enxerga o
> hardware virtual do container.

## Status do projeto

Em desenvolvimento por etapas. Backend: `catalog`, `compatibility`, `performance`,
`detection`, `recommendation`, `users` (autenticação JWT) e `analysis` (orquestra os
demais módulos e persiste histórico por usuário) implementados e testados. Frontend:
fluxo de detecção de hardware integrado; telas de compatibilidade, gargalo,
recomendação e relatório final ainda não conectadas à API.
