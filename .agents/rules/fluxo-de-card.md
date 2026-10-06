---
trigger: model_decision
description: "Fluxo de execucao de um card Jira PST no PoSentinel (9 passos: ler card, comentar plano, transicionar, delegar implementacao, testar, revisar, commitar, comentar resultado, transicionar), onde ler cada spec e o ferramental ja decidido. Use ao executar um card PST, planejar implementacao, ou precisar de comando de teste/lint."
---

# Fluxo de card PST, specs e ferramental

## Fluxo de execução de uma task (card Jira)

Ao executar um card do projeto Jira `PST` (`PoSentinel Tarefas`), siga estritamente esta sequência:

1. **Ler o card** — buscar a descrição completa no Jira (`mcp__atlassian-gotryx__getJiraIssue`) e revisá-la contra as specs em `docs/` (TRD, ADRs, PRDs, design spec) e a skill `posentinel-spec`.
2. **Comentar o plano** — publicar um comentário no card (`addCommentToJiraIssue`) descrevendo quais implementações serão executadas, **antes** de escrever qualquer código.
3. **Mover para "Fazendo"** — transicionar o status do card (`transitionJiraIssue`).
4. **Delegar a implementação** — chamar o agente de implementação (ex.: `python-pro`) para executar o trabalho descrito no comentário do passo 2.
5. **Testar** — rodar a suíte (`pytest`) e validar que a implementação cobre os critérios de aceite do card.
6. **Revisar** — fazer code review (ex.: skill `code-review` / `python-backend-reviewer`) antes de consolidar.
7. **Commitar** — criar o commit com a implementação aprovada.
8. **Comentar o resultado** — publicar um novo comentário no card resumindo o que foi implementado.
9. **Mover para "Pronto para testar"** — transicionar o status final do card.

## Onde ler cada spec

| Dúvida | Documento |
|---|---|
| Stack, arquitetura, RNFs, padrões globais | `docs/trd.md` |
| Decisão de Clean Core + modelos desacoplados | `docs/adrs/001-clean-core-odoo-metadata.md` |
| Requisitos de produto, User Stories, critérios de aceite | `docs/prds/001-linter-core-placeholders.md` |
| Modelos de domínio, contratos de regras, reporters, plano de testes | `docs/superpowers/specs/2026-09-21-posentinel-core-design.md` |
| Roadmap completo e visão de longo prazo | `docs/PoSentinel_Project_Plan.md` |

## Ferramental já decidido

A config de tooling (`pyproject.toml`, `ruff.toml`) já existe e está alinhada ao TRD, mesmo sem código para rodar contra ela ainda:

- Python 3.12+, Typer (CLI), Rich (terminal), `polib` (parser PO), Hatchling (build)
- Ruff: `line-length = 100`, `select = ["E","W","F","I","B","C4","UP","ARG","SIM"]` — a config ativa é `ruff.toml` na raiz (tem precedência sobre `[tool.ruff]` em `pyproject.toml`)
- Mypy strict
- pytest, com cobertura mínima de 90% planejada para o Core (`models`, `parser`, `rules`, `analyzers`) quando esse código existir
