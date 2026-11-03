"""Interface de linha de comando do PoSentinel, construída com Typer."""

from collections import defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from posentinel import __version__
from posentinel.ai.client import TranslationSuggester
from posentinel.ai.orchestrator import TranslationAssistant
from posentinel.analyzers.analyzer import TranslationAnalyzer
from posentinel.cli.interactive import confirm_translation
from posentinel.config.loader import ConfigLoader
from posentinel.models import ScanSummary
from posentinel.parser.po_parser import PoParser
from posentinel.parser.po_writer import PoWriter
from posentinel.reporters.console import ConsoleReporter
from posentinel.reporters.json import JsonReporter
from posentinel.rules.base import BaseRule
from posentinel.rules.engine import RulesEngine
from posentinel.rules.fuzzy import FuzzyTranslationRule
from posentinel.rules.glossary import GlossaryRule
from posentinel.rules.odoo import OdooFormatRule
from posentinel.rules.placeholders import (
    ExtraPlaceholderRule,
    InvalidPlaceholderRule,
    MissingPlaceholderRule,
)
from posentinel.rules.punctuation import PunctuationSpacingRule
from posentinel.rules.syntax import InvalidMarkupRule
from posentinel.rules.translations import EmptyTranslationRule

app = typer.Typer(
    name="posentinel",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help=(
        "Linter determinístico e Assistente de Tradução (IA) para arquivos .po (foco Odoo/pt_BR).\n"
        "Pode ser usado diretamente pelo Claude Code como linter determinístico sem API key."
    ),
    epilog=(
        "Guia para Claude Code e LLMs (Uso como Subagente):\n"
        "  O Claude Code pode atuar como provedor de IA sem necessidade de login ou chave de API:\n"
        "  1. Inicialize o subagente no workspace: `posentinel --init-claude`\n"
        "  2. Obtenha diagnóstico determinístico em JSON: `posentinel scan <alvo> --format json`\n"
        "  3. Traduza e edite as entradas apontadas (PO001 a PO006) no arquivo .po.\n"
        "  4. Valide a conformidade até zerar erros: `posentinel scan <alvo>` (exit code 0).\n\n"
        "Conectando à IA via API direta (Opcional):\n"
        "  Para sugestões automáticas via SDK Anthropic, exporte ANTHROPIC_API_KEY ou use SSO.\n\n"
        "Exemplos:\n\n"
        "  posentinel --init-claude\n"
        "  posentinel scan pt_BR.po\n"
        "  posentinel scan ./addons/sale/i18n --format json\n"
        "  posentinel scan pt_BR.po --fail-on warning\n"
        "  posentinel rules\n"
        "  posentinel version"
    ),
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"posentinel {__version__}")
        raise typer.Exit()


def init_claude_callback(value: bool) -> None:
    if value:
        agent_file = _generate_claude_agent(Path("."), force=True)
        typer.echo(f"Subagente Claude Code criado com sucesso em: {agent_file}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Exibe a versão instalada do PoSentinel.",
        ),
    ] = None,
    init_claude: Annotated[
        bool | None,
        typer.Option(
            "--init-claude",
            callback=init_claude_callback,
            is_eager=True,
            help="Gera o subagente do Claude Code em .claude/agents/posentinel-translator.md.",
        ),
    ] = None,
) -> None:
    """
    Linter determinístico e Assistente de Tradução (IA) para arquivos .po (foco Odoo/pt_BR).
    """
    pass


class OutputFormat(StrEnum):
    CONSOLE = "console"
    JSON = "json"


class FailOnLevel(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    NONE = "none"


def _default_rules(
    glossary: dict[str, tuple[str, ...]] | None = None,
) -> list[BaseRule]:
    return [
        EmptyTranslationRule(),
        MissingPlaceholderRule(),
        InvalidPlaceholderRule(),
        ExtraPlaceholderRule(),
        InvalidMarkupRule(),
        FuzzyTranslationRule(),
        GlossaryRule(glossary=glossary),
        OdooFormatRule(),
        PunctuationSpacingRule(),
    ]


def _determine_exit_code(summaries: list[ScanSummary], fail_on: FailOnLevel) -> int:
    has_operational_error = any(
        issue.code == "SYS001" for summary in summaries for issue in summary.issues
    )
    if has_operational_error:
        return 2

    if fail_on == FailOnLevel.NONE:
        return 0

    if any(summary.has_errors for summary in summaries):
        return 1

    if fail_on == FailOnLevel.WARNING and any(summary.warnings_count > 0 for summary in summaries):
        return 1

    return 0


@app.command(
    epilog=(
        "Uso por Claude Code e Subagentes (Recomendado - Sem API Key):\n"
        "  1. Use `--format json` para consumir os problemas de forma estruturada:\n"
        "     posentinel scan pt_BR.po --format json\n"
        "  2. Use o Claude Code para traduzir ou corrigir os msgstrs apontados no arquivo .po.\n"
        "  3. Revalide com `posentinel scan pt_BR.po` até obter código 0 (sucesso garantido).\n\n"
        "Conectando à IA via API externa (Anthropic / OpenAI / OpenRouter / Ollama):\n"
        "  O assistente de IA necessita de acesso à API da Anthropic. Exporte a variável\n"
        '  ANTHROPIC_API_KEY="sua-chave" ou use `ant auth login` para autenticar via SSO.\n\n'
        "Exemplos:\n\n"
        "  posentinel scan pt_BR.po\n"
        "      Analisa um único arquivo, saída em console, exit 1 se houver erro.\n\n"
        "  posentinel scan ./addons/sale/i18n\n"
        "      Varre recursivamente todos os .po de um diretório.\n\n"
        "  posentinel scan pt_BR.po --format json\n"
        "      Emite o resultado como JSON, ideal para pipelines de CI/CD e agentes LLM.\n\n"
        "  posentinel scan pt_BR.po --fail-on warning\n"
        "      Bloqueia (exit 1) também quando há apenas avisos, sem erros.\n\n"
        "  posentinel scan pt_BR.po --fail-on none\n"
        "      Nunca bloqueia por violações de qualidade (exit 0), só por erro operacional.\n\n"
        "  posentinel scan pt_BR.po --translation --auto-translate\n"
        "      Verifica arquivos e aplica as sugestões da IA automaticamente, sem perguntar."
    )
)
def scan(
    target: Annotated[
        Path | None, typer.Argument(help="Arquivo .po ou diretório a analisar")
    ] = None,
    output_format: Annotated[
        OutputFormat | None, typer.Option("--format", help="Formato de saída (console ou json)")
    ] = None,
    fail_on: Annotated[
        FailOnLevel | None,
        typer.Option("--fail-on", help="Nível mínimo para falhar (error, warning, none)"),
    ] = None,
    source_lang: Annotated[
        str | None, typer.Option("--source-lang", help="Idioma do msgid (ex: en_US)")
    ] = None,
    target_lang: Annotated[
        str | None, typer.Option("--target-lang", help="Idioma do msgstr (ex: pt_BR)")
    ] = None,
    translation_enabled: Annotated[
        bool | None,
        typer.Option("--translation/--no-translation", help="Ativa/desativa a camada de IA"),
    ] = None,
    auto_translate: Annotated[
        bool | None,
        typer.Option(
            "--auto-translate/--no-auto-translate",
            help="Aplica sem confirmar / força confirmação manual",
        ),
    ] = None,
    ai_model: Annotated[
        str | None,
        typer.Option("--ai-model", help="Modelo LLM (ex: claude-3-5-sonnet-20240620, gpt-4o-mini)"),
    ] = None,
    baseline: Annotated[
        Path | None,
        typer.Option(
            "--baseline",
            help="Arquivo ou diretório .po de referência para reportar apenas problemas novos.",
        ),
    ] = None,
    changed_only: Annotated[
        str | None,
        typer.Option(
            "--changed-only",
            help="Referência Git (ex: origin/main, HEAD~1) para reportar apenas problemas novos.",
        ),
    ] = None,
    ignore: Annotated[
        str | None,
        typer.Option(
            "--ignore",
            help="Códigos de regras a ignorar separados por vírgula (ex: PO005,PO006,PO010).",
        ),
    ] = None,
    config_opt: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Caminho explícito para o arquivo de configuração posentinel.toml.",
        ),
    ] = None,
) -> None:
    """Analisa um arquivo .po ou diretório em busca de problemas de tradução."""
    lookup_path = target if target is not None else Path.cwd()
    config = ConfigLoader().load(lookup_path, config_file=config_opt)

    eff_target = target if target is not None else Path(config.scan.target)
    eff_format = output_format if output_format is not None else OutputFormat(config.scan.format)
    eff_fail_on = fail_on if fail_on is not None else FailOnLevel(config.scan.fail_on)
    eff_source = source_lang if source_lang is not None else config.project.source_language
    eff_target_lang = target_lang if target_lang is not None else config.project.target_language
    eff_ai_enabled = translation_enabled if translation_enabled is not None else config.ai.enabled
    eff_auto = auto_translate if auto_translate is not None else config.ai.auto_translate
    eff_model = ai_model if ai_model is not None else config.ai.model
    eff_provider = config.ai.provider
    eff_base_url = config.ai.base_url

    eff_baseline = (
        baseline
        if baseline is not None
        else (Path(config.scan.baseline) if config.scan.baseline else None)
    )
    eff_changed_only = changed_only if changed_only is not None else config.scan.changed_only

    active_rules = _default_rules(glossary=config.project.glossary)
    known_codes = {r.code.upper() for r in active_rules}

    ignored_codes = set(config.scan.ignore_rules)
    if ignore:
        for c in (item.strip().upper() for item in ignore.split(",") if item.strip()):
            if c not in known_codes:
                typer.echo(
                    f"Aviso: regra '{c}' informada em --ignore não é reconhecida "
                    f"(regras válidas: {', '.join(sorted(known_codes))}).",
                    err=True,
                )
            ignored_codes.add(c)

    rules_engine = RulesEngine(active_rules, ignore_rules=ignored_codes)
    analyzer = TranslationAnalyzer(PoParser(), rules_engine)

    try:
        summaries = analyzer.analyze_path(
            eff_target,
            target_lang=eff_target_lang,
            baseline_path=eff_baseline,
            git_ref=eff_changed_only,
        )
    except FileNotFoundError:
        typer.echo(f"Erro: arquivo ou diretório não encontrado: {eff_target}", err=True)
        raise typer.Exit(code=2) from None

    all_changes = defaultdict(list)

    if eff_ai_enabled:
        console = Console()
        suggester = None
        assistant = None

        for summary in summaries:
            if not summary.issues:
                continue

            if suggester is None:
                try:
                    suggester = TranslationSuggester(
                        model=eff_model, provider=eff_provider, base_url=eff_base_url
                    )
                    assistant = TranslationAssistant(
                        suggester=suggester,
                        auto_translate=eff_auto,
                        confirm=lambda e, i, s: confirm_translation(e, i, s, console),
                    )
                except Exception as e:
                    import anthropic
                    import openai

                    if not isinstance(
                        e, (anthropic.AnthropicError, openai.OpenAIError, TypeError, Exception)
                    ):
                        raise e

                    import os
                    import sys

                    if sys.stdout.isatty():
                        provider_name = (
                            "Anthropic" if eff_provider == "anthropic" else "OpenAI/Agnóstico"
                        )
                        typer.echo(
                            f"IA ativada, sem credencial válida para {provider_name}.",
                            err=True,
                        )

                        if eff_provider == "anthropic":
                            import webbrowser

                            try:
                                webbrowser.open("https://console.anthropic.com/settings/keys")
                                typer.echo(
                                    "Navegador: https://console.anthropic.com/settings/keys ...",
                                    err=True,
                                )
                            except Exception:
                                pass

                        api_key = typer.prompt(
                            "Cole aqui a nova API Key (ou vazio para rodar só o linter)",
                            hide_input=True,
                            default="",
                            show_default=False,
                        )
                        if api_key.strip():
                            try:
                                if eff_provider == "anthropic":
                                    os.environ["ANTHROPIC_API_KEY"] = api_key.strip()
                                else:
                                    os.environ["OPENAI_API_KEY"] = api_key.strip()

                                suggester = TranslationSuggester(
                                    model=eff_model, provider=eff_provider, base_url=eff_base_url
                                )
                                assistant = TranslationAssistant(
                                    suggester=suggester,
                                    auto_translate=eff_auto,
                                    confirm=lambda e, i, s: confirm_translation(e, i, s, console),
                                )
                            except Exception:
                                typer.echo("Erro: A chave fornecida é inválida.", err=True)
                                raise typer.Exit(code=2) from None
                        else:
                            if translation_enabled is True:
                                typer.echo(
                                    "Erro: Operação abortada (IA obrigatória por --translation).",
                                    err=True,
                                )
                                raise typer.Exit(code=2) from None
                            eff_ai_enabled = False
                            break
                    else:
                        if translation_enabled is True:
                            typer.echo(
                                "Erro: Credenciais da IA ausentes.",
                                err=True,
                            )
                            raise typer.Exit(code=2) from None
                        eff_ai_enabled = False
                        break

            try:
                parse_result = PoParser().parse_file(Path(summary.file_path))
                entries_by_msgid = {e.msgid: e for e in parse_result.entries}

                assert assistant is not None
                changes = assistant.process(summary, entries_by_msgid, eff_source, eff_target_lang)
                if changes:
                    all_changes[summary.file_path] = changes
                    PoWriter().apply_changes(Path(summary.file_path), changes)
            except Exception:
                if translation_enabled is True:
                    typer.echo("Erro: Falha de rede ou autenticação durante o uso da IA.", err=True)
                    raise typer.Exit(code=2) from None
                eff_ai_enabled = False
                break

    if eff_format == OutputFormat.JSON:
        typer.echo(JsonReporter().report(summaries, all_changes if all_changes else None))
    else:
        for summary in summaries:
            if summary.total_entries == 0 and not summary.issues:
                typer.echo(f"Aviso: {summary.file_path} está vazio (nenhuma entrada).")
        ConsoleReporter().report(summaries, all_changes if all_changes else None)

    raise typer.Exit(code=_determine_exit_code(summaries, eff_fail_on))


@app.command()
def rules() -> None:
    """Lista as regras de validação ativas."""
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Código")
    table.add_column("Severidade")
    table.add_column("Descrição")

    for rule in _default_rules():
        table.add_row(rule.code, rule.default_severity.value.upper(), rule.description)

    console.print(table)


_CLAUDE_SUBAGENT_MARKDOWN = """---
name: posentinel-translator
description: Subagente especialista em auditoria e tradução de arquivos .po para ecossistemas
  Odoo / pt_BR usando o PoSentinel como linter determinístico e Claude Code como provedor LLM.
tools:
  - Bash
  - FileEdit
  - FileRead
  - GlobTool
  - GrepTool
---

Você é um especialista em localização de software Odoo (pt_BR) e arquivos gettext (.po).
Você atua de modo autônomo e rigoroso garantindo qualidade total de tradução sem quebrar sintaxe.

## Seu Fluxo de Trabalho Determinístico

1. **Diagnóstico Estruturado:**
   Execute a análise determinística usando o PoSentinel sem IA (linter estático):
   ```bash
   posentinel scan <caminho_ou_arquivo.po> --format json
   ```
   Analise a saída JSON para mapear exatamente as issues identificadas.

2. **Categorias de Issues e Ações Necessárias:**
   - **PO001 (EmptyTranslation):** Traduza a string `msgid` para o idioma alvo (ex: pt_BR),
     mantendo o sentido de negócio no contexto do Odoo.
   - **PO002 / PO003 / PO004 (Placeholders):** Corrija discrepâncias em interpolações `%s`,
     `%(nome)s`, `{var}` ou índices. Todos os placeholders presentes no `msgid` DEVEM constar
     identicamente no `msgstr`.
   - **PO005 (InvalidMarkup):** Preserve rigorosamente tags HTML e XML (ex: `<span class="...">`,
     `<b>`, `</b>`, `<t t-out="..."/>`), mantendo-as fechadas e balanceadas.
   - **PO006 (Fuzzy):** Se a tradução estiver correta ou após ajustá-la, remova o comentário
     `#, fuzzy` da respectiva entrada.

3. **Aplicação das Traduções:**
   Edite o arquivo `.po` diretamente com as correções necessárias.

4. **Validação e Loop de Fechamento:**
   Rode novamente o linter:
   ```bash
   posentinel scan <caminho_ou_arquivo.po>
   ```
   - O trabalho SÓ termina quando o comando retornar código 0 (sem erros).
   - Se ainda houver issues, corrija-as imediatamente e revalide.
"""


def _generate_claude_agent(target_dir: Path, force: bool) -> Path:
    claude_dir = target_dir / ".claude" / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)
    agent_file = claude_dir / "posentinel-translator.md"

    if agent_file.exists() and not force:
        typer.echo(
            f"Aviso: Subagente já existe em {agent_file}. Use --force para sobrescrever.",
            err=True,
        )
        raise typer.Exit(code=1)

    agent_file.write_text(_CLAUDE_SUBAGENT_MARKDOWN, encoding="utf-8")
    return agent_file


@app.command(name="init-claude-agent")
def init_claude_agent(
    target_dir: Annotated[
        Path,
        typer.Option(
            "--path",
            "-p",
            help="Diretório raiz onde o .claude/agents será gerado.",
        ),
    ] = Path("."),
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Sobrescreve o arquivo de subagente se já existir.",
        ),
    ] = False,
) -> None:
    """Gera o subagente determinístico do Claude Code em .claude/agents/posentinel-translator.md."""
    agent_file = _generate_claude_agent(target_dir, force)
    typer.echo(f"Subagente Claude Code criado com sucesso em: {agent_file}")


@app.command(name="lookup")
def lookup_cmd(
    po: Annotated[Path, typer.Argument(help="Arquivo .po a consultar")],
    msgid: Annotated[str, typer.Argument(help="Texto de origem exato (msgid)")],
    context: Annotated[
        str | None,
        typer.Option("--context", help="msgctxt ou módulo Odoo para desambiguação"),
    ] = None,
    similar: Annotated[
        int,
        typer.Option("--similar", help="Quantidade de termos similares a retornar (0 desliga)"),
    ] = 5,
    format_opt: Annotated[
        OutputFormat,
        typer.Option("--format", help="Formato de saída (console ou json)"),
    ] = OutputFormat.CONSOLE,
) -> None:
    """Consulta o status de tradução de um msgid em um arquivo .po (somente leitura)."""
    import json

    from posentinel.cli.lookup_set import (
        AmbiguousContextError,
        ScopeError,
        execute_lookup,
    )

    try:
        res = execute_lookup(po, msgid, context=context, similar_n=similar)
    except ScopeError as e:
        typer.echo(f"Erro de escopo: {e}", err=True)
        raise typer.Exit(code=4) from None
    except AmbiguousContextError as e:
        typer.echo(
            f"Erro: msgid ambíguo entre contextos. "
            f"Use --context com um de: {', '.join(e.contexts)}",
            err=True,
        )
        raise typer.Exit(code=3) from None
    except Exception as e:
        typer.echo(f"Erro operacional: {e}", err=True)
        raise typer.Exit(code=2) from None

    if format_opt == OutputFormat.JSON:
        payload = {
            "msgid": res.msgid,
            "status": res.status,
            "entries": res.entries,
            "similar": res.similar,
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"msgid:  {res.msgid}")
        typer.echo(f"status: {res.status}")
        for entry_data in res.entries:
            typer.echo(f"linha:  {entry_data['line']}")
            typer.echo(f"msgstr: {entry_data['msgstr']}")
            issues_list = entry_data.get("issues")
            if isinstance(issues_list, list):
                for iss in issues_list:
                    if isinstance(iss, dict):
                        typer.echo(f"  - [{iss['code']}] {iss['message']}")
        if res.similar:
            typer.echo("\nSimilares:")
            for sim in res.similar:
                typer.echo(f"  - {sim['msgid']} -> {sim['msgstr']} (linha {sim['line']})")

    exit_code = 0 if res.status == "translated" else 1
    raise typer.Exit(code=exit_code)


@app.command(name="set")
def set_cmd(
    po: Annotated[Path, typer.Argument(help="Arquivo .po a atualizar")],
    msgid: Annotated[str, typer.Argument(help="Texto de origem exato (msgid)")],
    msgstr: Annotated[str, typer.Argument(help="Novo texto traduzido (msgstr)")],
    context: Annotated[
        str | None,
        typer.Option("--context", help="msgctxt ou módulo Odoo para desambiguação"),
    ] = None,
    ref: Annotated[
        list[str] | None,
        typer.Option("--ref", help="Referência de código-fonte (#:) repetível para novas entradas"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Sobrescreve msgstr existente preenchido e diferente"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Exibe o diff sem alterar o arquivo .po"),
    ] = False,
    format_opt: Annotated[
        OutputFormat,
        typer.Option("--format", help="Formato de saída (console ou json)"),
    ] = OutputFormat.CONSOLE,
) -> None:
    """Atualiza ou cria deterministicamente a tradução de um msgid em um arquivo .po."""
    import json

    from posentinel.cli.lookup_set import (
        AmbiguousContextError,
        ScopeError,
        execute_set,
    )

    try:
        res = execute_set(
            po,
            msgid,
            msgstr,
            context=context,
            refs=ref,
            force=force,
            dry_run=dry_run,
        )
    except ScopeError as e:
        typer.echo(f"Erro de escopo: {e}", err=True)
        raise typer.Exit(code=4) from None
    except AmbiguousContextError as e:
        typer.echo(
            f"Erro: msgid ambíguo entre contextos. "
            f"Use --context com um de: {', '.join(e.contexts)}",
            err=True,
        )
        raise typer.Exit(code=3) from None
    except Exception as e:
        typer.echo(f"Erro operacional: {e}", err=True)
        raise typer.Exit(code=2) from None

    if format_opt == OutputFormat.JSON:
        payload = {
            "action": res.action,
            "changed": res.changed,
            "line": res.line,
            "previous_msgstr": res.previous_msgstr,
            "msgstr": res.msgstr,
            "warnings": res.warnings,
        }
        if res.reason is not None:
            payload["reason"] = res.reason
        if dry_run and res.diff is not None:
            payload["diff"] = res.diff
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"Ação:            {res.action}")
        typer.echo(f"Modificado:      {res.changed}")
        if res.line:
            typer.echo(f"Linha:           {res.line}")
        if res.previous_msgstr:
            typer.echo(f"msgstr anterior: {res.previous_msgstr}")
        typer.echo(f"msgstr:          {res.msgstr}")
        if res.reason:
            typer.echo(f"Motivo recusa:   {res.reason}")
        if res.warnings:
            for w in res.warnings:
                typer.echo(f"Aviso:           {w}")
        if dry_run and res.diff:
            typer.echo(f"\nDiff (dry-run):\n{res.diff}")

    exit_code = 1 if res.action == "refused" else 0
    raise typer.Exit(code=exit_code)


@app.command()
def version() -> None:
    """Exibe a versão instalada do PoSentinel."""
    typer.echo(f"posentinel {__version__}")
