# TRD — Technical Requirements Document

> Documento técnico global do projeto PoSentinel. Criado e mantido via skill `escrever-trd`.
> Carregado automaticamente por `preparar-execucao` e `implementar-task` como contexto global.
> Granularidade baixa: cobre o que é global e estável. Regras finas ficam em ADRs.

---

## Stack

| Dimensão | Valor |
|---|---|
| Linguagem principal | Python 3.12+ |
| Runtime / plataforma | CPython 3.12+ / Linux & Cross-platform |
| Framework principal | Typer (CLI) + Rich (Terminal UI) |
| Parser de PO | polib |
| Banco de dados | Não aplicável (Stateless CLI / linter determinístico) |
| Ferramentas de build | Hatchling (PEP 517/518/621), build, twine |
| Gerenciador de pacotes | pip / uv |

---

## Arquitetura

### Padrão arquitetural

**Clean Core / Hexagonal Leve (Domain-Isolated Rules Engine)**

O núcleo do domínio (`TranslationEntry`, `Issue`, `ScanSummary`) e o motor de validação (`RulesEngine`, `BaseRule`) são estritamente isolados de formatos de arquivos externos e de bibliotecas de parsing (`polib`). Adaptadores específicos lidam com a leitura/conversão de dados e apresentação dos resultados.

### Estrutura de pastas dominante

```
posentinel/
├── pyproject.toml              # Metadados de empacotamento PyPI, dependências e linters
├── docs/                       # Documentação técnica, PRDs, ADRs e planos
│   ├── prds/                   # Product Requirements Documents
│   ├── adrs/                   # Architecture Decision Records
│   └── superpowers/specs/      # Especificações técnicas de design
├── src/posentinel/             # Código-fonte da aplicação (layout src)
│   ├── models/                 # Modelos de domínio imutáveis desacoplados
│   ├── parser/                 # Adaptadores de parsing (PoParser com metadados Odoo)
│   ├── rules/                  # Motor de regras e regras de validação (PO001 a PO005)
│   ├── analyzers/              # Orquestrador de varredura (arquivos e diretórios)
│   ├── reporters/              # Apresentação formatada (Console via Rich e JSON)
│   ├── cli/                    # Interface de linha de comando com Typer
│   └── config/                 # Carregamento de configuração TOML (v0.2+)
└── tests/                      # Suíte de testes automatizados com pytest
    └── fixtures/               # Arquivos .po válidos e inválidos para testes
```

### Módulos / camadas principais

| Módulo | Responsabilidade |
|---|---|
| `posentinel.models` | Entidades imutáveis de domínio (`TranslationEntry`, `OdooMetadata`, `Issue`, `ScanSummary`, `Severity`). |
| `posentinel.parser` | Adaptador para leitura de `.po` usando `polib`, mapeando ocorrências e metadados Odoo (`#. module:`, referências de modelo/campo). |
| `posentinel.rules` | Motor de execução (`RulesEngine`) e implementação individual de regras desacopladas (`BaseRule`). |
| `posentinel.analyzers` | Coordenação do processo de scan em arquivos e diretórios recursivamente. |
| `posentinel.reporters` | Formatação e exportação dos diagnósticos para console (`rich`) e pipelines (`JSON`). |
| `posentinel.cli` | Entrypoint da CLI, definição de argumentos, opções e controle de códigos de saída (`0`, `1`, `2`). |

---

## Requisitos Não-Funcionais

| Dimensão | Requisito |
|---|---|
| Performance | Varredura de arquivos com 10.000+ entradas de tradução em tempo < 1.5s em hardware padrão. |
| Disponibilidade / SLA | Execução local e offline determinística (zero dependência de rede no Core). |
| Escalabilidade | Capacidade de varrer recursivamente árvores completas de módulos Odoo (`addons/`) com centenas de arquivos `.po`. |
| Segurança | Leitura somente-leitura de arquivos `.po` no modo `scan`; nenhuma execução de código dinâmico contido nas strings. |
| Observabilidade / CI | Códigos de saída semânticos e estáveis (`0` = OK, `1` = Issues encontradas, `2` = Erro operacional) e saída JSON estruturada. |

---

## Dependências Externas

| Serviço / Sistema | Tipo | Constraint relevante | Dono |
|---|---|---|---|
| PyPI | Distribuição de pacotes | Publicação padronizada de wheels e sdist (PEP 517/621) | Externo |
| GNU gettext / Odoo PO format | Especificação de formato | Compatibilidade com o formato PO gerado nativamente pelo Odoo (UTF-8, flags, referências de modelo) | Externo (Odoo S.A. / GNU) |

---

## Padrões

### Testes

| Item | Valor |
|---|---|
| Framework | pytest |
| Comando completo | `.venv/bin/pytest -v` |
| Cobertura mínima | 90% no Core |
| Estratégia | Testes unitários para todas as regras isoladas + testes de integração CLI e parser com fixtures reais |

### Estilo de código

- **Linter:** Ruff (`select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "SIM"]`)
- **Formatter:** Ruff (`line-length = 100`)
- **Tipagem:** Mypy estrito (`strict = true`, `python_version = "3.12"`)
- **Convenções de nomenclatura:** PEP 8 (snake_case para funções/variáveis, PascalCase para classes/modelos)

### Error handling

Exceções operacionais (como arquivo não encontrado ou sintaxe inválida de arquivo PO) são capturadas no nível da CLI/Analyzer, emitindo mensagem clara para `stderr` com exit code `2`. Falhas pontuais em uma regra individual durante a checagem não derrubam o processo completo, gerando uma `Issue` de severidade de erro (`SYS001`).

### Logging / Saída

- **Formato:** Saída humana rica via Rich (com suporte a cores e tabelas) ou saída puramente estruturada em JSON (quando solicitado via `--format json`).
- **Nível padrão:** Saída direcionada ao usuário final da CLI.

### Autenticação / autorização

Não aplicável (ferramenta CLI local/offline).

---

## Decisões Globais (ADRs)

| # | Título | Data | Status | Link |
|---|--------|------|--------|------|
| 001 | [Adoção de Clean Core com Modelos Desacoplados e Metadados Odoo](adrs/001-clean-core-odoo-metadata.md) | 2026-09-21 | aceito | [001-clean-core-odoo-metadata.md](adrs/001-clean-core-odoo-metadata.md) |
