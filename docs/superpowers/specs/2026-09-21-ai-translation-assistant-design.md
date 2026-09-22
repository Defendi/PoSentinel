# Especificação Técnica de Design: Assistente de Tradução por IA (PoSentinel Agent)

- **Status**: Aprovado em Brainstorming
- **Data**: 2026-09-21
- **Autor**: Tech Lead
- **Escopo**: Nova capacidade opcional de geração/correção de traduções via Claude, camada de configuração (`posentinel.toml`), preservando o Core determinístico do MVP v0.1.0 intacto.

---

## 1. Visão Geral e Objetivos

O PoSentinel Core (v0.1.0) detecta problemas em arquivos `.po` de forma 100% determinística (PO001–PO006). Esta especificação adiciona uma **camada opcional** que usa a API do Claude para:

1. **Gerar** a tradução de entradas com `msgstr` vazio (PO001).
2. **Corrigir** entradas com problema já detectado deterministicamente (PO002–PO006).

Essa camada roda **por padrão** a partir desta versão (ativada, não opt-in), com um modo interativo que pergunta antes de aplicar cada sugestão — a menos que `--auto-translate` seja passado (aplica sem perguntar) ou `--no-translation` (desativa a IA inteiramente, voltando ao comportamento 100% determinístico do MVP).

Autenticação usa o mecanismo já existente do SDK/CLI da Anthropic (`ant auth login`) — o PoSentinel **não implementa OAuth próprio**.

### Fora do escopo desta especificação

- Override de severidade de regra via config (`[rules]`) e `[odoo] enabled` — mudam a arquitetura de `BaseRule`, não fazem parte desta capacidade.
- Chamadas de IA em lote (explicitamente rejeitado: cada entrada é uma chamada isolada).
- Outros provedores de IA além de Claude/Anthropic.
- Comando de reversão automatizado (`posentinel restore`) — o backup `.bak` existe, desfazer manualmente por ora.
- Cache ou rate-limiting de chamadas de IA.
- Regras de detecção novas ou alteradas — PO001–PO006 permanecem exatamente como estão.

---

## 2. Princípios de Arquitetura

1. **O Core nunca deixa de ser determinístico**: `PoParser`, `BaseRule`/`RulesEngine` e as 6 regras não mudam uma linha. A camada de IA consome o output já pronto (`ScanSummary`/`Issue`) — ela nunca decide *se* há um problema, só *o que fazer* com um problema já detectado deterministicamente.
2. **Isolamento de terceiros (Clean Core, ADR 001 estendido)**: assim como `polib` fica confinado ao `PoParser`, o SDK `anthropic` fica confinado ao módulo `posentinel.ai`. Nenhuma regra, nenhum modelo de domínio central importa `anthropic`.
3. **Falha de IA nunca aborta o scan**: se não houver credenciais Claude configuradas, o scan continua no modo 100% determinístico, com um aviso único — nunca um exit code de erro por causa da IA.
4. **Precedência de configuração**: flag de linha de comando > `posentinel.toml` > default embutido, em todos os atributos configuráveis.
5. **Reversibilidade**: nenhuma escrita em arquivo do usuário acontece sem backup automático (`<arquivo>.bak`) criado antes da primeira alteração.

---

## 3. Configuração (`posentinel.toml` + CLI)

### 3.1 Arquivo de configuração

Buscado em `Path.cwd() / "posentinel.toml"` (diretório onde `posentinel scan` é executado; sem subir a árvore de diretórios). Se ausente, todos os defaults embutidos se aplicam.

```toml
[scan]
target = "."
format = "console"       # "console" | "json"
fail_on = "error"         # "error" | "warning" | "none"

[project]
source_language = "en"
target_language = "pt_BR"

[ai]
enabled = true
auto_translate = false
model = "claude-opus-5"
```

### 3.2 Tabela de atributos e precedência

| Atributo | Flag CLI | Chave TOML | Default embutido |
|---|---|---|---|
| Alvo do scan | `target` (posicional) | `[scan] target` | `"."` |
| Formato de saída | `--format` | `[scan] format` | `"console"` |
| Nível de bloqueio | `--fail-on` | `[scan] fail_on` | `"error"` |
| Idioma do `msgid` (base) | `--source-lang` | `[project] source_language` | `"en"` |
| Idioma do `msgstr` (tradução) | `--target-lang` | `[project] target_language` | `"pt_BR"` |
| Desativar IA | `--no-translation` | `[ai] enabled` (inverso) | `enabled = true` |
| Aplicar sem perguntar | `--auto-translate` | `[ai] auto_translate` | `false` |
| Modelo Claude usado | `--ai-model` | `[ai] model` | `"claude-opus-5"` |

**Regra de resolução por atributo** (aplicada na CLI, antes de qualquer uso):

- Valores com escolha discreta (`target`, `format`, `fail_on`, `source_language`, `target_language`, `model`): a flag CLI usa `None` como default no Typer; se `None`, usa o valor do config; se o config também não tiver a seção/chave, usa o default embutido. Ordem: `cli_value or config_value or built_in_default`.
- Flags booleanas aditivas (`--no-translation`, `--auto-translate`): a flag CLI **desativa/ativa incondicionalmente** quando passada. `--no-translation` sempre desativa a IA, independente do `[ai] enabled` do config. `--auto-translate` sempre ativa, independente do `[ai] auto_translate`. Quando a flag não é passada, vale o valor do config (default `enabled=true`, `auto_translate=false`).

### 3.3 Modelos de configuração

```python
# src/posentinel/config/models.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScanConfig:
    target: str = "."
    format: str = "console"
    fail_on: str = "error"


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    source_language: str = "en"
    target_language: str = "pt_BR"


@dataclass(frozen=True, slots=True)
class AiConfig:
    enabled: bool = True
    auto_translate: bool = False
    model: str = "claude-opus-5"


@dataclass(frozen=True, slots=True)
class PoSentinelConfig:
    scan: ScanConfig
    project: ProjectConfig
    ai: AiConfig
```

### 3.4 Loader

```python
# src/posentinel/config/loader.py
import tomllib
from pathlib import Path

from posentinel.config.models import AiConfig, PoSentinelConfig, ProjectConfig, ScanConfig


class ConfigLoader:
    """Carrega posentinel.toml do diretório atual; retorna defaults se ausente."""

    def load(self, cwd: Path) -> PoSentinelConfig:
        config_path = cwd / "posentinel.toml"
        if not config_path.is_file():
            return PoSentinelConfig(scan=ScanConfig(), project=ProjectConfig(), ai=AiConfig())

        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        return PoSentinelConfig(
            scan=ScanConfig(**{**_defaults(ScanConfig), **data.get("scan", {})}),
            project=ProjectConfig(**{**_defaults(ProjectConfig), **data.get("project", {})}),
            ai=AiConfig(**{**_defaults(AiConfig), **data.get("ai", {})}),
        )
```

`_defaults(cls)` é um helper que devolve os valores default de uma dataclass como dict (via `dataclasses.fields`), usado para fazer merge parcial — uma seção incompleta no TOML (ex: só `[ai] model = "..."`) preenche o resto com os defaults embutidos, sem exigir que o usuário declare todas as chaves.

Usa `tomllib` (stdlib desde Python 3.11, já coberto pelo `requires-python = ">=3.12"`) — sem dependência nova.

---

## 4. Módulo `posentinel.ai`

Novo pacote, único ponto de contato com o SDK `anthropic`.

### 4.1 Modelo de retorno

```python
# src/posentinel/ai/models.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranslationSuggestion:
    msgstr: str
    reasoning: str | None = None
```

### 4.2 Prompts

```python
# src/posentinel/ai/prompts.py
from posentinel.models import Issue, TranslationEntry


def build_generate_prompt(entry: TranslationEntry, source_language: str, target_language: str) -> str:
    """Prompt para gerar uma tradução do zero — usado quando a Issue é PO001 (msgstr vazio)."""
    context_lines = [f"Idioma original ({source_language}): {entry.msgid}"]
    if entry.odoo_metadata.module:
        context_lines.append(f"Módulo Odoo: {entry.odoo_metadata.module}")
    if entry.odoo_metadata.field_name:
        context_lines.append(f"Campo: {entry.odoo_metadata.field_name}")
    return (
        f"Traduza o texto de {source_language} para {target_language}, mantendo qualquer "
        f"placeholder (%s, %(nome)s, {{var}}) e tag HTML/XML exatamente como no original.\n\n"
        + "\n".join(context_lines)
    )


def build_fix_prompt(
    entry: TranslationEntry, issue: Issue, source_language: str, target_language: str
) -> str:
    """Prompt para corrigir uma tradução existente com problema — usado para PO002-PO006."""
    return (
        f"A tradução abaixo de {source_language} para {target_language} tem um problema "
        f"detectado deterministicamente: [{issue.code}] {issue.message}\n\n"
        f"Original: {entry.msgid}\n"
        f"Tradução atual: {entry.msgstr}\n\n"
        "Corrija a tradução preservando o sentido, os placeholders e as tags do original."
    )
```

### 4.3 Cliente

```python
# src/posentinel/ai/client.py
import anthropic

from posentinel.ai.models import TranslationSuggestion
from posentinel.ai.prompts import build_fix_prompt, build_generate_prompt
from posentinel.models import Issue, TranslationEntry


class TranslationSuggester:
    """Encapsula o SDK anthropic. Único ponto de contato com a API Claude no projeto."""

    def __init__(self, model: str, client: anthropic.Anthropic | None = None) -> None:
        self._model = model
        self._client = client or anthropic.Anthropic()

    def suggest(
        self,
        entry: TranslationEntry,
        issue: Issue,
        source_language: str,
        target_language: str,
    ) -> TranslationSuggestion:
        """Uma chamada à API por entrada problemática — nunca em lote.

        Levanta `anthropic.AuthenticationError` se não houver credenciais configuradas
        (nem ANTHROPIC_API_KEY, nem perfil OAuth de `ant auth login`); o chamador decide
        como degradar (ver seção 6.4).
        """
        prompt = (
            build_generate_prompt(entry, source_language, target_language)
            if issue.code == "PO001"
            else build_fix_prompt(entry, issue, source_language, target_language)
        )
        response = self._client.messages.parse(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            output_format=TranslationSuggestion,
        )
        return response.parsed_output
```

O cliente é injetável (`client: anthropic.Anthropic | None = None`) especificamente para permitir mock em testes — **nenhum teste automatizado faz chamada de rede real à API Claude**. `output_format=TranslationSuggestion` e `response.parsed_output` foram confirmados contra `anthropic==1.7.0` instalado no projeto (`client.messages.parse` usa `pydantic.TypeAdapter` internamente, que funciona nativamente com dataclasses `frozen=True, slots=True` — testado isoladamente antes de travar esta assinatura).

---

## 5. Orquestração — `TranslationAssistant`

Novo componente que consome o resultado já pronto do scan determinístico e decide, por issue, se gera uma sugestão e se a aplica.

`TranslationChange` fica em `posentinel/models/change.py` (par de `entry.py`, `issue.py`, `result.py`), não em `posentinel/ai/` — tanto o orquestrador (`ai/orchestrator.py`) quanto o `PoWriter` (`parser/po_writer.py`, seção 6.2) precisam desse tipo, e nenhum dos dois deve depender do outro. Colocá-lo em `models/` evita que `parser` (mais próximo do Core) dependa de `ai` (camada opcional):

```python
# src/posentinel/models/change.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranslationChange:
    msgid: str
    old_msgstr: str
    new_msgstr: str
    issue_code: str
    applied: bool  # True se foi escrita no arquivo; False se só sugerida e recusada
```

Re-exportado em `posentinel/models/__init__.py` junto aos demais modelos (`Issue`, `OdooMetadata`, `ScanSummary`, `Severity`, `TranslationEntry`).

```python
# src/posentinel/ai/orchestrator.py
from collections.abc import Callable

from posentinel.ai.client import TranslationSuggester
from posentinel.ai.models import TranslationSuggestion
from posentinel.models import Issue, ScanSummary, TranslationChange, TranslationEntry

ConfirmFn = Callable[[TranslationEntry, Issue, TranslationSuggestion], bool]


class TranslationAssistant:
    def __init__(
        self,
        suggester: TranslationSuggester,
        auto_translate: bool,
        confirm: ConfirmFn,
    ) -> None:
        self._suggester = suggester
        self._auto_translate = auto_translate
        self._confirm = confirm

    def process(
        self,
        summary: ScanSummary,
        entries_by_msgid: dict[str, TranslationEntry],
        source_language: str,
        target_language: str,
    ) -> list[TranslationChange]:
        """Para cada Issue elegível do summary, gera sugestão e decide aplicar."""
        changes = []
        for issue in summary.issues:
            if issue.code == "SYS001" or issue.msgid is None:
                continue  # erro operacional ou sem entrada associada — não é candidato a tradução
            entry = entries_by_msgid.get(issue.msgid)
            if entry is None:
                continue

            suggestion = self._suggester.suggest(entry, issue, source_language, target_language)
            applied = self._auto_translate or self._confirm(entry, issue, suggestion)
            changes.append(
                TranslationChange(
                    msgid=entry.msgid,
                    old_msgstr=entry.msgstr,
                    new_msgstr=suggestion.msgstr,
                    issue_code=issue.code,
                    applied=applied,
                )
            )
        return changes
```

`entries_by_msgid` é montado pela CLI a partir de `ParseResult.entries` (chave = `msgid`); assume-se `msgid` único por arquivo dentro do escopo desta feature — colisões de `msgid` com `msgctxt` diferente ficam fora de escopo (mesma limitação já implícita no design atual de `Issue.msgid`).

---

## 6. Interatividade e CLI

### 6.1 Confirmação por entrada

```python
# src/posentinel/cli/interactive.py
import typer
from rich.console import Console

from posentinel.ai.models import TranslationSuggestion
from posentinel.models import Issue, TranslationEntry


def confirm_translation(
    entry: TranslationEntry, issue: Issue, suggestion: TranslationSuggestion, console: Console
) -> bool:
    console.print(f"[bold]{issue.code}[/bold] {issue.message}")
    console.print(f"  Original: {entry.msgid}")
    console.print(f"  Atual:    {entry.msgstr!r}")
    console.print(f"  Sugestão: {suggestion.msgstr!r}")
    return typer.confirm("Aplicar esta tradução?", default=False)
```

### 6.2 Escrita no arquivo (`PoWriter`)

Novo módulo em `posentinel/parser/` — mesmo princípio Clean Core do `PoParser` (único outro lugar que conhece `polib` para I/O de `.po`).

```python
# src/posentinel/parser/po_writer.py
import shutil
from pathlib import Path

import polib

from posentinel.models import TranslationChange


class PoWriter:
    """Aplica TranslationChange (applied=True) de volta no arquivo .po, com backup automático."""

    def apply_changes(self, path: Path, changes: list[TranslationChange]) -> Path | None:
        applied_changes = [change for change in changes if change.applied]
        if not applied_changes:
            return None

        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup_path)

        pofile = polib.pofile(str(path))
        changes_by_msgid = {change.msgid: change for change in applied_changes}
        for entry in pofile:
            change = changes_by_msgid.get(entry.msgid)
            if change is not None:
                entry.msgstr = change.new_msgstr
        pofile.save(str(path))
        return backup_path
```

Retorna `None` quando nada foi aplicado (evita criar um `.bak` desnecessário). Chamado uma vez por arquivo, depois que todas as confirmações daquele arquivo já foram decididas.

### 6.3 Novas opções do comando `scan`

```python
@app.command(...)
def scan(
    target: Annotated[Path | None, typer.Argument(help="Arquivo .po ou diretório a analisar")] = None,
    output_format: Annotated[OutputFormat | None, typer.Option("--format")] = None,
    fail_on: Annotated[FailOnLevel | None, typer.Option("--fail-on")] = None,
    source_lang: Annotated[str | None, typer.Option("--source-lang", help="Idioma do msgid")] = None,
    target_lang: Annotated[str | None, typer.Option("--target-lang", help="Idioma do msgstr")] = None,
    no_translation: Annotated[
        bool, typer.Option("--no-translation", help="Desativa a camada de IA")
    ] = False,
    auto_translate: Annotated[
        bool, typer.Option("--auto-translate", help="Aplica sugestões sem confirmar")
    ] = False,
    ai_model: Annotated[str | None, typer.Option("--ai-model")] = None,
) -> None:
    ...
```

`target` passa a ter default `None` (resolvido para `Path(config.scan.target)`, que por sua vez tem default `"."`) — mudança de assinatura em relação ao MVP v0.1.0, onde `target` era obrigatório. Isso é o único ajuste retroativo necessário nesta spec sobre o comando existente.

### 6.4 Fluxo completo do `scan`

1. `ConfigLoader().load(Path.cwd())` → `PoSentinelConfig`.
2. Resolve todos os atributos (seção 3.2: CLI > config > default).
3. `TranslationAnalyzer` roda exatamente como hoje (parser + engine determinísticos) → `list[ScanSummary]`.
4. Se `ai_enabled` é `False` (via `--no-translation` ou `[ai] enabled = false`): pula direto para o reporter, comportamento idêntico ao MVP v0.1.0.
5. Se `ai_enabled` é `True`: para cada `ScanSummary` com `issues` não vazias:
   a. Reconstrói `entries_by_msgid` a partir do resultado do parser para aquele arquivo.
   b. Instancia `TranslationSuggester(model=resolved_ai_model)`.
   c. Na **primeira** chamada, se `anthropic.AuthenticationError` for levantada: imprime um aviso único (`"Aviso: sem credenciais Claude configuradas — rode 'ant auth login' ou defina ANTHROPIC_API_KEY. Continuando sem sugestões de IA."`), desativa `ai_enabled` para o restante da execução inteira (não só do arquivo atual) e segue sem abortar o scan.
   d. Caso contrário, `TranslationAssistant.process(...)` → `list[TranslationChange]`.
   e. `PoWriter().apply_changes(path, changes)` — só escreve se houver ao menos uma mudança `applied=True`.
6. Reporter (Console ou JSON) exibe os `ScanSummary` **e**, se houver, a lista de `TranslationChange` de cada arquivo (seção 7).
7. Exit code: calculado exatamente como hoje, a partir dos `ScanSummary.issues` (a camada de IA não influencia exit code — uma sugestão aplicada não remove a `Issue` original do relatório determinístico; o usuário roda o scan de novo para confirmar que o problema foi corrigido).

---

## 7. Extensão dos Reporters

Assinatura estendida de forma aditiva (parâmetro opcional, não quebra os usos existentes já testados):

```python
def report(
    self, summaries: list[ScanSummary], changes: dict[str, list[TranslationChange]] | None = None
) -> None: ...
```

`changes` é indexado por `file_path` (mesma chave usada em `ScanSummary.file_path`). Quando `None` ou vazio, o comportamento é idêntico ao atual (nenhuma seção extra impressa).

- **ConsoleReporter**: após a tabela de issues de cada arquivo, se houver mudanças, imprime uma tabela extra "Traduções (IA)" com colunas Código, Original, Antes, Depois, Aplicada (✓/✗).
- **JsonReporter**: cada objeto de resultado por arquivo ganha uma chave opcional `"ai_changes"`, lista de `{code, msgid, old_msgstr, new_msgstr, applied}` — omitida (não incluída) quando vazia, para não quebrar consumidores existentes que fazem parsing estrito do payload atual.

---

## 8. Autenticação

Nenhum código de OAuth é escrito no PoSentinel. O `TranslationSuggester` instancia `anthropic.Anthropic()` sem argumentos — a SDK resolve credenciais na ordem: `ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → perfil OAuth ativo de `ant auth login` → Workload Identity Federation → perfil default em disco.

O PoSentinel documenta (README) que a forma recomendada de autenticar é `ant auth login` (CLI oficial da Anthropic, instala separadamente) — vinculado à assinatura Claude Pro/Max do usuário — ou definir `ANTHROPIC_API_KEY` para uso via billing direto da API. A falha de autenticação é tratada como degradação graciosa (seção 6.4), nunca como erro fatal do scan.

---

## 9. Plano de Testes

Nenhum teste faz chamada de rede real — `TranslationSuggester` é sempre instanciado com um `client` mockado (`unittest.mock.Mock(spec=anthropic.Anthropic)` ou stub equivalente) nos testes.

| Arquivo | Cobertura |
|---|---|
| `tests/test_config.py` | `ConfigLoader`: arquivo ausente → defaults; arquivo com seções parciais → merge com defaults; arquivo com todas as seções preenchidas; erro de parsing TOML inválido. |
| `tests/test_ai_prompts.py` | `build_generate_prompt`/`build_fix_prompt`: presença do idioma origem/destino, contexto Odoo incluído quando presente, ausente quando não. |
| `tests/test_ai_client.py` | `TranslationSuggester.suggest`: chamada única por invocação (não em lote), propagação de `AuthenticationError` sem capturá-la internamente, seleção do prompt certo por `issue.code`. |
| `tests/test_ai_orchestrator.py` | `TranslationAssistant.process`: ignora `SYS001`, ignora issue sem `msgid`/entry correspondente, `auto_translate=True` nunca chama `confirm`, `auto_translate=False` chama `confirm` e respeita seu retorno. |
| `tests/test_po_writer.py` | `PoWriter.apply_changes`: cria backup `.bak` com conteúdo original, aplica só as mudanças `applied=True`, retorna `None` (sem side-effect) quando não há mudanças aplicadas. |
| `tests/test_cli.py` (extensão) | Precedência CLI > config > default para cada atributo da tabela 3.2; `--no-translation` não instancia `TranslationSuggester`; `--auto-translate` aplica sem chamar `confirm`; modo interativo chama `confirm` (mockado) e respeita a resposta; falha de autenticação simulada gera aviso único e não aborta (exit code determinado só pelas issues do Core). |

Meta de cobertura: mantém o padrão do projeto (≥ 90% no Core; a camada de IA, por depender de mocks determinísticos do client, também é alvo de 100% de cobertura de linha, seguindo a prática já estabelecida nos módulos existentes).

---

## 10. Backlog (cards a criar)

Refletindo a decomposição acima, em ordem de dependência:

1. **Config**: `posentinel.config` (models + loader) + testes.
2. **AI Core**: `posentinel.ai` (models, prompts, client) + `TranslationChange` em `posentinel.models` + testes com client mockado.
3. **AI Orchestrator**: `TranslationAssistant` + testes.
4. **PoWriter**: `posentinel.parser.po_writer` + testes (backup, aplicação seletiva).
5. **Reporters**: extensão de `ConsoleReporter`/`JsonReporter` para `changes` opcional + testes.
6. **CLI**: novas flags, resolução de precedência, fluxo interativo, integração fim-a-fim + testes de `CliRunner`.
7. **Documentação**: README (autenticação via `ant auth login`, novas flags, exemplo de `posentinel.toml`) + atualização do `docs/PoSentinel_Project_Plan.md` (esta capacidade avança o que estava em v0.6/v0.7 do roadmap para agora).

Estes 7 itens viram cards no Jira (projeto `PST`) na fase de `writing-plans`, um por task granular dentro de cada item quando fizer sentido dividir mais.
