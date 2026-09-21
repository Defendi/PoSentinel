# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é o PoSentinel

Linter determinístico de linha de comando planejado para arquivos `.po` de internacionalização,
com foco no ecossistema Odoo e localizações `pt_BR`. Vai detectar placeholders corrompidos (`%s`,
`%(name)s`, `{var}`), tags HTML/XML desbalanceadas, traduções vazias e entradas `fuzzy`. Projeto
**independente**, sem relação com o ecossistema Gotryx — não aplicar convenções/skills/MCPs de
outros projetos aqui.

## Estado atual: fase de spec, sem código implementado

Este repositório está deliberadamente **só na fase de especificação** — não há `src/` nem `tests/`.
Uma implementação inicial chegou a ser escrita e foi removida por estar fora do escopo desta fase;
o histórico de commits mantém esse código caso sirva de referência ao retomar a implementação.

**Não inicie implementação de código sem alinhamento explícito do usuário.** O trabalho nesta fase
é sobre os documentos em `docs/` (TRD, ADRs, PRDs, design specs) e sobre as skills em
`.agents/skills/` / `.claude/skills/`.

## Skill obrigatória

Antes de qualquer tarefa — mesmo de planejamento ou revisão de spec — carregue a skill
`posentinel-spec` (`.claude/skills/posentinel-spec/SKILL.md`, espelhada em `.agents/skills/`). Ela
é a fonte de verdade do contexto técnico do projeto: stack alvo, arquitetura Clean Core planejada,
modelo de domínio, regras do MVP (PO001–PO006) e convenções de código a seguir quando a
implementação for retomada.

## Onde ler cada spec

| Dúvida | Documento |
|---|---|
| Stack, arquitetura, RNFs, padrões globais | `docs/trd.md` |
| Decisão de Clean Core + modelos desacoplados | `docs/adrs/001-clean-core-odoo-metadata.md` |
| Requisitos de produto, User Stories, critérios de aceite | `docs/prds/001-linter-core-placeholders.md` |
| Modelos de domínio, contratos de regras, reporters, plano de testes | `docs/superpowers/specs/2026-09-21-posentinel-core-design.md` |
| Roadmap completo e visão de longo prazo | `docs/PoSentinel_Project_Plan.md` |

## Gestão de tarefas no Jira

As tarefas do projeto são gerenciadas no Jira, projeto **"PoSentinel Tarefas"** (key `PST`), no site
`mygotryx.atlassian.net`. Use o MCP `atlassian-gotryx` para consultar, criar ou atualizar issues
desse projeto (épicos, histórias, bugs, tarefas e subtarefas) — não use o MCP `atlassian` genérico
nem assuma outro projeto Jira para o PoSentinel.

## Fluxo de execução de uma task (card Jira)

Ao executar um card do projeto Jira `PST` (`PoSentinel Tarefas`), siga estritamente esta sequência:

1. **Ler o card**: buscar a descrição completa no Jira (`mcp__atlassian-gotryx__getJiraIssue`) e
   revisá-la contra as specs em `docs/` (TRD, ADRs, PRDs, design spec) e a skill `posentinel-spec`.
2. **Comentar o plano**: publicar um comentário no card (`addCommentToJiraIssue`) descrevendo quais
   implementações serão executadas, antes de escrever qualquer código.
3. **Mover para "Fazendo"**: transicionar o status do card (`transitionJiraIssue`) para refletir
   que o trabalho começou.
4. **Delegar a implementação**: chamar o agente de implementação (ex: `python-pro`) para executar
   o trabalho descrito no comentário do passo 2.
5. **Testar**: rodar a suíte de testes (`pytest`) e validar que a implementação cobre os critérios
   de aceite do card.
6. **Revisar**: fazer code review da implementação (ex: skill `code-review` /
   `python-backend-reviewer`) antes de consolidar.
7. **Commitar**: criar o commit com a implementação aprovada.
8. **Comentar o resultado**: publicar um novo comentário no card resumindo o que foi implementado.
9. **Mover para "Pronto para testar"**: transicionar o status final do card.

## Ferramental já decidido (para quando a implementação começar)

Config de tooling (`pyproject.toml`, `ruff.toml`) já existe e está alinhada ao TRD, mesmo sem
código para rodar contra ela ainda:

- Python 3.12+, Typer (CLI), Rich (terminal), `polib` (parser PO), Hatchling (build)
- Ruff: `line-length = 100`, `select = ["E","W","F","I","B","C4","UP","ARG","SIM"]` — config ativa
  é `ruff.toml` na raiz (tem precedência sobre `[tool.ruff]` em `pyproject.toml`)
- Mypy strict
- pytest, com cobertura mínima de 90% planejada para o Core (`models`, `parser`, `rules`,
  `analyzers`) quando esse código existir

## Comunicação

Sempre em português do Brasil (`pt-BR`).
