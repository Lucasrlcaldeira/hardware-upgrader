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
histórico), `users` (autenticação) e `games` (compara o PC com os requisitos mínimos e
recomendados de um jogo da Steam).

### "Será que roda?" — requisitos da Steam

O projeto não estima FPS: só com a lista de peças, qualquer número seria chute. Em vez
disso, o usuário escolhe um jogo, o backend consulta a loja da Steam (os mesmos endpoints
JSON que alimentam a página do jogo, sem chave de API) e compara cada peça com os
requisitos **mínimos** e **recomendados** publicados pelo desenvolvedor. O resultado é um
veredito ("roda no recomendado", "roda no mínimo", "abaixo do mínimo" ou "não deu pra
cravar") para o PC atual e para o PC com os upgrades recomendados.

Para comparar peças que não estão no catálogo (GTX 960, i5-4460, FX-6300...), o módulo usa
uma base de referência em `backend/app/modules/games/reference/*.json`, na mesma escala
ordinal do `performance_tier` do catálogo. Para um modelo que existe no catálogo, vale a
nota do catálogo. Um modelo não reconhecido vira "não deu pra cravar", nunca um chute.
Requer internet no backend; as respostas da Steam ficam em cache na memória por algumas
horas.

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

### Dados do catálogo (seed)

As tabelas de catálogo (CPUs/GPUs/etc.) começam vazias após rodar as migrações — sem isso,
o catálogo aparece sem opções. Depois de `alembic upgrade head`, rode (idempotente, pode
rodar de novo a qualquer momento):

```
backend\.venv\Scripts\python -m app.modules.catalog.seed.load_seed
```

> Quem já tinha o banco das versões anteriores: o `alembic upgrade head` agora também
> remove as antigas tabelas `games`/`game_benchmarks`, que não são mais usadas.

## Status do projeto

Em desenvolvimento por etapas. Backend: `catalog`, `compatibility`, `performance`,
`detection`, `recommendation`, `users` (autenticação JWT), `analysis` (orquestra os
demais módulos e persiste histórico por usuário) e `games` (comparação com os requisitos
da Steam) implementados e testados. Frontend: fluxo completo conectado à API, da detecção
de hardware ao relatório final (compatibilidade, gargalo, recomendações e "será que roda?"
para qualquer jogo da Steam).
