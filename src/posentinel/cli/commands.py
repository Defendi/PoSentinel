"""Interface de linha de comando do PoSentinel, construída com Typer."""

from collections import defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import anthropic
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
from posentinel.rules.placeholders import (
    ExtraPlaceholderRule,
    InvalidPlaceholderRule,
    MissingPlaceholderRule,
)
from posentinel.rules.syntax import InvalidMarkupRule
from posentinel.rules.translations import EmptyTranslationRule

app = typer.Typer(
    name="posentinel",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Linter determinístico e Assistente de Tradução (IA) para arquivos .po (foco Odoo/pt_BR).",
    epilog=(
        "Para ativar as sugestões de tradução automáticas, você precisa configurar\n"
        "uma chave de API da Anthropic. Isso pode ser feito definindo a variável\n"
        "de ambiente ANTHROPIC_API_KEY ou autenticando via SSO (ant auth login).\n"
        "Se nenhuma chave for detectada, o comando continuará apenas como linter local.\n\n"
        "Exemplos:\n\n"
        "  posentinel scan pt_BR.po\n"
        "  posentinel scan ./addons/sale/i18n\n"
        "  posentinel scan pt_BR.po --format json\n"
        "  posentinel scan pt_BR.po --fail-on warning\n"
        "  posentinel scan pt_BR.po --translation --ai-model claude-3-5-sonnet-20240620\n"
        "  posentinel rules\n"
        "  posentinel version"
    ),
)


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"posentinel {__version__}")
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


def _default_rules() -> list[BaseRule]:
    return [
        EmptyTranslationRule(),
        MissingPlaceholderRule(),
        InvalidPlaceholderRule(),
        ExtraPlaceholderRule(),
        InvalidMarkupRule(),
        FuzzyTranslationRule(),
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
        "Conectando à IA (Anthropic / Claude):\n"
        "  O assistente de IA necessita de acesso à API da Anthropic. Exporte a variável\n"
        '  ANTHROPIC_API_KEY="sua-chave" ou use `ant auth login` para autenticar via SSO.\n\n'
        "Exemplos:\n\n"
        "  posentinel scan pt_BR.po\n"
        "      Analisa um único arquivo, saída em console, exit 1 se houver erro.\n\n"
        "  posentinel scan ./addons/sale/i18n\n"
        "      Varre recursivamente todos os .po de um diretório.\n\n"
        "  posentinel scan pt_BR.po --format json\n"
        "      Emite o resultado como JSON, ideal para pipelines de CI/CD.\n\n"
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
        typer.Option("--ai-model", help="Modelo LLM do Claude (ex: claude-3-5-sonnet-20240620)"),
    ] = None,
) -> None:
    """Analisa um arquivo .po ou diretório em busca de problemas de tradução."""
    config = ConfigLoader().load(Path.cwd())

    eff_target = target if target is not None else Path(config.scan.target)
    eff_format = output_format if output_format is not None else OutputFormat(config.scan.format)
    eff_fail_on = fail_on if fail_on is not None else FailOnLevel(config.scan.fail_on)
    eff_source = source_lang if source_lang is not None else config.project.source_language
    eff_target_lang = target_lang if target_lang is not None else config.project.target_language
    eff_ai_enabled = translation_enabled if translation_enabled is not None else config.ai.enabled
    eff_auto = auto_translate if auto_translate is not None else config.ai.auto_translate
    eff_model = ai_model if ai_model is not None else config.ai.model

    analyzer = TranslationAnalyzer(PoParser(), RulesEngine(_default_rules()))

    try:
        summaries = analyzer.analyze_path(eff_target, target_lang=eff_target_lang)
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
                    suggester = TranslationSuggester(model=eff_model)
                    assistant = TranslationAssistant(
                        suggester=suggester,
                        auto_translate=eff_auto,
                        confirm=lambda e, i, s: confirm_translation(e, i, s, console),
                    )
                except (anthropic.AuthenticationError, TypeError):
                    if translation_enabled is True:
                        typer.echo(
                            "Erro: Credenciais Claude ausentes (exporte ANTHROPIC_API_KEY).",
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
            except (anthropic.AuthenticationError, TypeError):
                if translation_enabled is True:
                    typer.echo(
                        "Erro: Credenciais Claude ausentes (exporte ANTHROPIC_API_KEY).", err=True
                    )
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


@app.command()
def version() -> None:
    """Exibe a versão instalada do PoSentinel."""
    typer.echo(f"posentinel {__version__}")
