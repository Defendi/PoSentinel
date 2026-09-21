---
name: posentinel-spec
description: >
  Contexto completo do projeto PoSentinel para qualquer tarefa de desenvolvimento.
  Cobre stack, arquitetura, modelo de domínio, regras do MVP (PO001–PO006), convenções
  de código, estrutura de arquivos e onde encontrar cada artefato de spec.
  Use antes de iniciar qualquer task de desenvolvimento, implementação ou revisão
  de código no repositório PoSentinel.
---

# PoSentinel — Spec do Projeto

## O que é

**PoSentinel** é um **linter determinístico de linha de comando** para arquivos `.po`
de internacionalização, focado no ecossistema Odoo e localizações `pt_BR`.

```bash
posentinel scan pt_BR.po                   # analisa um arquivo
posentinel scan ./i18n/                    # varre recursivamente um diretório
posentinel scan pt_BR.po --format json    # saída JSON para CI/CD
posentinel rules                           # lista regras ativas
posentinel version                         # versão da ferramenta
```

---

## Artefatos de spec — onde ler cada coisa

| Dúvida | Documento |
|--------|-----------|
| Stack, arquitetura, RNFs, padrões globais | `docs/trd.md` |
| Decisão de Clean Core + modelos desacoplados | `docs/adrs/001-clean-core-odoo-metadata.md` |
| Requisitos de produto, User Stories, critérios de aceite | `docs/prds/001-linter-core-placeholders.md` |
| Modelos de domínio, contratos de regras, reporters, plano de testes | `docs/superpowers/specs/2026-09-21-posentinel-core-design.md` |
| Roadmap completo e visão de longo prazo | `docs/PoSentinel_Project_Plan.md` |

---

## Stack

| Dimensão | Valor |
|----------|-------|
| Linguagem | Python 3.12+ |
| CLI | Typer |
| Terminal UI | Rich |
| Parser PO | polib (detalhe interno — nunca exposto às regras) |
| Build | Hatchling (PEP 517/621) |
| Testes | pytest |
| Linter | Ruff |
| Tipos | Mypy strict |

---

## Arquitetura — Clean Core

```
.po file
   │
   ▼
PoParser          ← único módulo que conhece polib
   │  converte para →
   ▼
TranslationEntry  ← entidade de domínio imutável (frozen dataclass)
   │
   ▼
RulesEngine       ← itera regras, isola exceções
   │  produz →
   ▼
Issue[]           ← value object leve e serializável
   │
   ├──► ConsoleReporter  (Rich — tabelas, cores, resumo)
   └──► JsonReporter     (payload estruturado para CI/CD)
```

**Princípio central**: As regras nunca importam `polib`. Apenas o `PoParser` conhece
o formato de origem. As regras recebem `TranslationEntry` e devolvem `list[Issue]`.

---

## Estrutura de arquivos

```
src/posentinel/
├── __init__.py
├── __main__.py
├── models/
│   ├── entry.py        # TranslationEntry, OdooMetadata, Severity
│   ├── issue.py        # Issue
│   └── result.py       # ScanSummary
├── parser/
│   └── po_parser.py    # PoParser — encapsula polib
├── rules/
│   ├── base.py         # BaseRule (ABC)
│   ├── engine.py       # RulesEngine
│   ├── translations.py # PO001 (EmptyTranslationRule)
│   ├── placeholders.py # PO002, PO003, PO004
│   ├── syntax.py       # PO005 (InvalidMarkupRule)
│   └── fuzzy.py        # PO006 (FuzzyTranslationRule) — PST-10
├── analyzers/
│   └── analyzer.py     # TranslationAnalyzer — orquestra parser + engine
├── reporters/
│   ├── console.py      # ConsoleReporter (Rich)
│   └── json.py         # JsonReporter
├── cli/
│   └── commands.py     # app Typer: scan, rules, version
└── config/             # loader.py → planejado para v0.2 (NÃO implementar no MVP)

tests/
├── fixtures/           # valid.po, invalid.po, odoo_pt_br.po  ← PST-11
├── test_parser.py
├── test_placeholders.py
├── test_translations.py
├── test_odoo.py
└── test_cli.py
```

---

## Modelos de domínio

### `TranslationEntry` — entrada normalizada

```python
@dataclass(frozen=True, slots=True)
class TranslationEntry:
    msgid: str
    msgstr: str = ""
    msgid_plural: str | None = None
    msgstr_plural: dict[int, str] = field(default_factory=dict)
    msgctxt: str | None = None
    comments: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    line: int | None = None
    is_fuzzy: bool = False
    odoo_metadata: OdooMetadata = field(default_factory=OdooMetadata)

    @property
    def is_header(self) -> bool:
        return self.msgid == ""

    @property
    def all_translations(self) -> list[str]:
        """Retorna singular ou todas as formas plurais preenchidas."""
        if self.msgstr_plural:
            return list(self.msgstr_plural.values())
        return [self.msgstr] if self.msgstr else []
```

### `OdooMetadata` — contexto extraído dos comentários PO

```python
@dataclass(frozen=True, slots=True)
class OdooMetadata:
    module: str | None = None       # de: #. module: sale
    model: str | None = None        # de: #: model:sale.order,...
    field_name: str | None = None   # de: ,field_description:sale.field_x
    xml_id: str | None = None
    term_type: str | None = None    # field_description | code | view | selection
```

### `Issue` — value object de diagnóstico

```python
@dataclass(frozen=True, slots=True)
class Issue:
    code: str               # "PO001" … "PO006"
    message: str
    severity: Severity      # ERROR | WARNING | INFO
    line: int | None
    msgid: str | None
    odoo_context: str | None = None   # módulo Odoo afetado (ex: "sale")
    suggestion: str | None = None     # apenas PO003: placeholder correto esperado
```

> **Não adicionar** campo `entry: TranslationEntry` ao `Issue`.
> Decisão de design: `Issue` é serializável e leve por definição.
> O contexto necessário para o reporter é copiado para campos escalares na criação.

---

## Regras do MVP (PO001–PO006)

| Código | Classe | Severidade | Detecta |
|--------|--------|-----------|---------|
| PO001 | `EmptyTranslationRule` | WARNING | `msgid` preenchido com `msgstr` vazio (exceto cabeçalho) |
| PO002 | `MissingPlaceholderRule` | ERROR | Placeholder do original ausente na tradução (`%s`, `%d`, `%(var)s`, `{var}`) |
| PO003 | `InvalidPlaceholderRule` | ERROR | Variável nomeada traduzida por engano — preencher `suggestion` com o nome correto |
| PO004 | `ExtraPlaceholderRule` | ERROR | Tradução contém mais placeholders do que o original |
| PO005 | `InvalidMarkupRule` | WARNING | Tags HTML/XML do original omitidas ou desequilibradas na tradução |
| PO006 | `FuzzyTranslationRule` | WARNING | Entrada com flag `#, fuzzy` — ignorada pelo Odoo em produção |

### Contrato de implementação de regra

```python
class MinhaRegra(BaseRule):
    code = "PO00X"
    description = "Descrição curta"
    default_severity = Severity.ERROR  # ou WARNING

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []
        # lógica aqui
        # iterar entry.all_translations para cobrir plurais
        return []  # lista vazia = sem problemas
```

### Placeholders suportados (PO002/PO003/PO004)

| Tipo | Exemplos |
|------|---------|
| Printf posicional | `%s`, `%d`, `%f`, `%r` |
| Printf nomeado | `%(partner_name)s`, `%(count)d` |
| Python str.format | `{var}`, `{0}`, `{name!r}` |
| Escapado (ignorar) | `%%` → **não** é placeholder |

---

## CLI — contratos públicos

```bash
posentinel scan <target> [--format console|json] [--fail-on error|warning|none]
posentinel rules
posentinel version
```

**Exit codes** (estáveis desde v0.1.0):

| Código | Significado |
|--------|------------|
| `0` | Nenhum problema no nível configurado |
| `1` | Violações encontradas |
| `2` | Erro operacional (arquivo não encontrado, sintaxe ilegível) |

---

## Convenções de código

- **Python 3.12+** — `X | Y` em vez de `Optional[X]`, `type` keyword quando adequado
- **Mypy strict** — sem `Any` implícito, toda função anotada
- **Frozen dataclasses** — `frozen=True, slots=True` em todos os modelos de domínio
- **Ruff** — `line-length = 100`, selects `E W F I B C4 UP ARG SIM`
- **Testes unitários** — instâncias puras de `TranslationEntry` sem arquivos `.po` em disco
- **Fixtures** — arquivos `.po` em `tests/fixtures/` usados apenas em testes de integração

---

## Cobertura mínima de testes

| Arquivo | Responsabilidade |
|---------|-----------------|
| `test_parser.py` | `PoParser`: arquivo válido, plurais, metadados Odoo, fallback encoding |
| `test_placeholders.py` | PO002, PO003 (+ `suggestion`), PO004; cobertura de plurais e `%%` escapado |
| `test_translations.py` | PO001 (excluir cabeçalho), PO005 (tags desequilibradas), PO006 (flag fuzzy) |
| `test_odoo.py` | Extração correta de `OdooMetadata`; `odoo_context` presente nas issues |
| `test_cli.py` | Exit codes 0/1/2; `--format json` válido; `--fail-on warning` |

**Meta**: ≥ 90% no Core (`models`, `parser`, `rules`, `analyzers`). Mínimo aceitável: 85%.

---

## Backlog do MVP — cards Jira (PST)

| Card | Título | Status |
|------|--------|--------|
| PST-2 | Setup PyPI, Tooling e Qualidade | A fazer |
| PST-3 | Modelos de Domínio | A fazer |
| PST-4 | PoParser Resiliente | A fazer |
| PST-5 | RulesEngine + PO001–PO004 | A fazer |
| PST-6 | PO005 InvalidMarkupRule | A fazer |
| PST-7 | TranslationAnalyzer | A fazer |
| PST-8 | ConsoleReporter + JsonReporter | A fazer |
| PST-9 | CLI Typer + Exit Codes | A fazer |
| PST-10 | PO006 FuzzyTranslationRule | A fazer |
| PST-11 | Fixtures de Teste | A fazer |

---

## Fora do escopo do MVP (v0.1.0)

| Feature | Versão |
|---------|--------|
| `config/loader.py` — suporte a `posentinel.toml` | v0.2 |
| Regra de inconsistência terminológica (PO007) | v0.5 |
| Análise semântica por IA | v0.6 |
| Auto-fix (`posentinel fix`) | v0.7 |
| Outros formatos (XLIFF, JSON, YAML) | futuro |
