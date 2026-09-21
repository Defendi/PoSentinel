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
