# Especificação Técnica de Design: PoSentinel Core (v0.1.0 MVP)

- **Status**: Aprovado e Refinado em Brainstorming
- **Data**: 2026-09-21 (Atualizado)
- **Autor**: Tech Lead
- **Escopo**: Milestone v0.1.0 (Core Engine, Odoo Metadata Parser, Plurais, Regras PO001-PO006, CLI, Reporters)

---

## 1. Visão Geral e Objetivos

O **PoSentinel** é um linter determinístico e analisador de qualidade para arquivos de internacionalização `.po`, focado primordialmente no ecossistema Odoo e localizações `pt_BR`.

O objetivo do Milestone v0.1.0 é entregar uma CLI funcional, estável e testada, capaz de analisar arquivos `.po` de módulos Odoo e detectar falhas críticas de tradução (placeholders corrompidos, strings vazias, tags HTML quebradas, entradas fuzzy e formas plurais) com retorno de exit codes adequados para integração contínua (CI/CD).

---

## 2. Princípios de Arquitetura

1. **Clean Core & Domain Isolation**: O motor de validação e as regras não dependem de bibliotecas externas de parsing (`polib`). Apenas os adaptadores de parser conhecem os formatos de origem.
2. **First-Class Odoo Awareness**: Mesmo no MVP determinístico com regras básicas de PO, o modelo de domínio já extrai e preserva o contexto do Odoo (`#. module:`, referências de modelo/campo `#: model:...,field_description:...`).
3. **Determinismo Estrito**: Sem dependência de IA nesta fase inicial. Execuções repetidas com a mesma entrada produzem resultados idênticos.
4. **Ergonomia CLI & Prontidão para CI**: Uso de `typer` + `rich` para experiência interativa de desenvolvedor e saídas padronizadas em JSON com códigos de saída semânticos (0 = sucesso, 1 = erros detectados, 2 = falha de execução/configuração).

---

## 3. Modelo de Domínio (`posentinel.models`)

### 3.1 Severidades (`Severity`)
```python
from enum import StrEnum


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
```

### 3.2 Metadados de Contexto Odoo (`OdooMetadata`)
```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OdooMetadata:
    module: str | None = None
    model: str | None = None
    field_name: str | None = None
    xml_id: str | None = None
    term_type: str | None = None  # ex: field_description, code, view, selection
```

### 3.3 Entrada de Tradução Normalizada (`TranslationEntry`)
Suporte nativo tanto para mensagens singulares quanto para formas plurais (`msgid_plural` / `msgstr_plural`).

```python
from dataclasses import dataclass, field


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
    def is_python_format(self) -> bool:
        return "python-format" in self.flags

    @property
    def is_header(self) -> bool:
        return self.msgid == ""

    @property
    def all_translations(self) -> list[str]:
        """Retorna todas as traduções associadas (singular ou plurais preenchidos)."""
        if self.msgstr_plural:
            return list(self.msgstr_plural.values())
        return [self.msgstr] if self.msgstr else []
```

### 3.4 Representação de Ocorrência (`Issue`) e Resultado do Scan (`ScanSummary`)

> **Decisão de design**: `Issue` é um **value object leve e serializável**. Não carrega
> referência à `TranslationEntry` de origem para manter o modelo independente de estado e
> compatível com serialização JSON direta. As informações de contexto necessárias para
> o reporter (`line`, `msgid`, `odoo_context`) são copiadas para campos escalares no
> momento da criação da `Issue`.

```python
@dataclass(frozen=True, slots=True)
class Issue:
    code: str            # ex: "PO001", "PO003"
    message: str         # Descrição legível da falha
    severity: Severity   # ERROR, WARNING, INFO
    line: int | None     # Linha no arquivo original
    msgid: str | None    # String original avaliada
    odoo_context: str | None = None   # Nome do módulo Odoo (ex: "sale", "account")
    suggestion: str | None = None     # Sugestão de correção opcional (usada por PO003:
                                      # informa o nome correto do placeholder esperado)
```

**Uso de `suggestion`**: preenchido por `InvalidPlaceholderRule` (PO003) para indicar
qual nome de variável era esperado. Exemplo: `suggestion="%(date)s"` quando a tradução
usou `%(data)s`. Todas as demais regras do v0.1.0 deixam `suggestion=None`.

```python
@dataclass(slots=True)
class ScanSummary:
    file_path: str
    locale: str | None = None
    total_entries: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == Severity.ERROR)

    @property
    def warnings_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == Severity.WARNING)

    @property
    def infos_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == Severity.INFO)

    @property
    def has_errors(self) -> bool:
        return self.errors_count > 0
```


---

## 4. Adaptador de Parser (`posentinel.parser.po_parser`)

O `PoParser` encapsula `polib` e realiza o mapeamento para instâncias imutáveis de `TranslationEntry`.

### Responsabilidades:
1. **Carregamento resiliente com fallback de encoding**: UTF-8 primário, fallback transparente para ISO-8859-1/Latin-1 se UTF-8 estrito falhar.
2. **Extração de metadados Odoo**:
   * Comentários automáticos `#. module: <name>` -> `OdooMetadata.module`.
   * Ocorrências `#: model:<name>,<type>:<field>` -> `OdooMetadata.model`, `term_type` e `field_name`.
3. **Suporte a plurais**: mapear `item.msgid_plural` e `item.msgstr_plural`.
4. **Resiliência a erros de sintaxe**: capturar `polib.POFileSyntaxError` e registrar uma `Issue` sintática sem abortar o processo global.

---

## 5. Motor de Regras (`posentinel.rules`)

### 5.1 Contrato Base (`BaseRule`)
```python
from abc import ABC, abstractmethod


class BaseRule(ABC):
    code: str
    description: str
    default_severity: Severity

    @abstractmethod
    def check(self, entry: TranslationEntry) -> list[Issue]:
        """Avalia a entrada fornecida e retorna problemas encontrados."""
        ...
```

### 5.2 Regras do MVP (v0.1.0)

| Código | Nome | Severidade Padrão | Descrição |
|---|---|---|---|
| **PO001** | `EmptyTranslationRule` | `WARNING` | Detecta entradas onde `msgid` não é vazio, mas `msgstr` (ou formas plurais) estão em branco `""`. |
| **PO002** | `MissingPlaceholderRule` | `ERROR` | Detecta placeholders presentes no original (`%s`, `%d`, `%(var)s`, `{var}`) ausentes em qualquer forma de tradução. |
| **PO003** | `InvalidPlaceholderRule` | `ERROR` | Detecta placeholders nomeados que foram corrompidos ou inadvertidamente traduzidos (ex: `%(partner)s` -> `%(parceiro)s`). |
| **PO004** | `ExtraPlaceholderRule` | `ERROR` | Detecta placeholders existentes na tradução que não foram declarados no `msgid` original. |
| **PO005** | `InvalidMarkupRule` | `WARNING` | Valida tags HTML/XML básicas (ex: `<a>`, `<b>`, `<code>`), garantindo balanceamento e preservação de tags do original. |
| **PO006** | `FuzzyTranslationRule` | `WARNING` | Alerta sobre entradas marcadas com a flag `fuzzy`, indicando tradução pendente de revisão que pode quebrar a experiência do usuário. |

### 5.3 Registry e Engine (`RulesEngine`)
* Mantém a coleção de regras ativas.
* Itera sobre cada entrada isolando exceções com emissão de erro `SYS001`.

---

## 6. Orquestrador (`posentinel.analyzers.analyzer`)

O `TranslationAnalyzer`:
1. Recebe um arquivo ou diretório de arquivos `.po`.
2. Aciona o `PoParser` de forma resiliente.
3. Submete as entradas ao `RulesEngine`.
4. Agrupa os resultados em objetos `ScanSummary`.

---

## 7. Apresentação e Repórteres (`posentinel.reporters`)

### 7.1 `ConsoleReporter` (Rich)
* Cabeçalho estético: arquivo analisado, locale detectado e contagem total de entradas.
* Tabela expansiva com severidade, código da regra, linha, módulo Odoo e mensagem explicativa.
* Resumo final com contadores de erros, avisos e status `PASSED` / `WARNINGS` / `FAILED`.

### 7.2 `JsonReporter`
* Serialização estruturada com contadores consolidados e lista detalhada de issues para consumo por bots de CI, GitHub Annotations e GitLab Code Quality.

---

## 8. CLI (`posentinel.cli.commands`)

Construída sobre `typer`:
* `posentinel scan <target>`:
  * `--format [console|json]`
  * `--fail-on [error|warning|none]`
* `posentinel rules`: Listagem de regras ativas.
* `posentinel version`: Versão da ferramenta.
* Códigos de saída:
  * `0`: Sucesso.
  * `1`: Violações detectadas no nível estipulado de `--fail-on`.
  * `2`: Erro operacional (arquivo inexistente ou sintaxe ilegível).

---

## 9. Plano de Testes Automatizados (`tests/`)

### Fixtures necessárias (`tests/fixtures/`)

| Arquivo | Conteúdo |
|---------|----------|
| `valid.po` | Arquivo PO válido com entradas completas (singulares e plurais), metadados Odoo e sem problemas |
| `invalid.po` | Arquivo com erros deliberados de placeholder, markup quebrado e entradas fuzzy |
| `odoo_pt_br.po` | Arquivo real-like com comentários `#. module:`, referências `#: model:...` e plurais `pt_BR` |

### Arquivos de teste

| Arquivo | O que cobre |
|---------|------------|
| `test_parser.py` | Carregamento de arquivo válido, extração de `OdooMetadata` (`module`, `model`, `field_name`), suporte a `msgid_plural`/`msgstr_plural`, fallback de encoding UTF-8→Latin-1 |
| `test_placeholders.py` | PO002 (`%s`, `%d`, `%(var)s`, `{var}` ausentes), PO003 (variáveis nomeadas traduzidas), PO004 (placeholders extras), cobertura de plurais e `%%` escapado |
| `test_translations.py` | PO001 (vazia, excluindo cabeçalho), PO005 (tags `<a>`, `<b>`, `<br/>` ausentes ou desequilibradas), PO006 (flag `#, fuzzy` detectada) |
| `test_odoo.py` | `OdooMetadata` extraído corretamente de comentários `#. module:` e referências `#: model:ir.model.fields,field_description:`; `odoo_context` presente nas issues geradas |
| `test_cli.py` | End-to-end com `CliRunner`: exit code `0` em arquivo limpo, `1` com erros, `2` em arquivo inexistente; `--format json` com payload válido; `--fail-on warning` bloqueando em warning |

### Meta de cobertura

- **Mínimo aceitável**: 85%
- **Meta**: ≥ 90% no Core (`models`, `parser`, `rules`, `analyzers`)

